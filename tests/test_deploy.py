"""The parts of tools/deploy.py that do not talk to Railway."""

import importlib.util
import subprocess
import sys

import pytest

from app.config import BASE_DIR

spec = importlib.util.spec_from_file_location("deploy", BASE_DIR / "tools" / "deploy.py")
deploy = importlib.util.module_from_spec(spec)
sys.modules["deploy"] = deploy
spec.loader.exec_module(deploy)

PASSWORD = "client-pass-2026"  # gitleaks:allow (test-only password)


@pytest.fixture
def env_file(tmp_path):
    """A client file made from .env.example, the way docs/deploy.md says."""
    path = tmp_path / "acme.env"
    text = (BASE_DIR / ".env.example").read_text()
    text = text.replace("PUBLIC_URL=http://localhost:8000", "PUBLIC_URL=")
    text = text.replace("BRAND_NAME=Car Buyout", "BRAND_NAME='Acme Auto Buyers'")
    text = text.replace("OPERATOR_NAME=\n", "OPERATOR_NAME=Acme Auto LLC\n")
    text = text.replace("OPERATOR_EMAIL=\n", "OPERATOR_EMAIL=privacy@example.com\n")
    text = text.replace("OWNER_PASSWORD=\n", f"OWNER_PASSWORD={PASSWORD}\n")
    path.write_text(text)
    return path


def test_the_example_file_reads_cleanly(env_file):
    env = deploy.read_env(env_file)
    assert env["BRAND_NAME"] == "Acme Auto Buyers"
    assert env["SOURCE_LABELS"] == "parking:Parking lot,flyer:Flyers"
    assert env["SECRET_KEY"] == "" and env["RAILWAY_PROJECT_ID"] == ""


def test_missing_keys_are_generated_once_and_saved(env_file):
    env = deploy.read_env(env_file)
    added = deploy.fill_secrets(env_file, env)
    assert added == ["SECRET_KEY", "VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY", "VAPID_SUBJECT"]
    saved = deploy.read_env(env_file)
    assert len(saved["SECRET_KEY"]) >= 32 and saved["VAPID_PRIVATE_KEY"]
    # The example push contact is replaced by the business's own address.
    assert saved["VAPID_SUBJECT"] == "mailto:privacy@example.com"
    # Filled in place, not appended a second time.
    assert env_file.read_text().count("SECRET_KEY=") == 1
    assert deploy.fill_secrets(env_file, saved) == []


def test_project_id_is_appended_with_a_comment(tmp_path):
    path = tmp_path / "old.env"
    path.write_text("BRAND_NAME=Acme\n")
    deploy.write_env_value(path, "RAILWAY_PROJECT_ID", "abc", "Railway project.")
    assert path.read_text() == "BRAND_NAME=Acme\n\n# Railway project.\nRAILWAY_PROJECT_ID=abc\n"


def test_a_ready_file_passes_production_checks(env_file):
    env = deploy.read_env(env_file)
    deploy.fill_secrets(env_file, env)
    deploy.validate(env)


def test_production_problems_are_reported_before_anything_is_created(env_file):
    env = deploy.read_env(env_file)
    deploy.fill_secrets(env_file, env)
    env["OWNER_PASSWORD"] = ""
    env["OPERATOR_EMAIL"] = ""
    with pytest.raises(deploy.DeployError) as caught:
        deploy.validate(env)
    assert "OWNER_PASSWORD is required" in str(caught.value)
    assert "OPERATOR_EMAIL is required" in str(caught.value)


def test_a_local_public_url_is_refused(env_file):
    env = deploy.read_env(env_file)
    env["PUBLIC_URL"] = "http://localhost:8000"
    with pytest.raises(deploy.DeployError, match="Leave it empty"):
        deploy.validate(env)


def test_a_missing_preset_is_caught(env_file):
    env = deploy.read_env(env_file)
    deploy.fill_secrets(env_file, env)
    env["PRESET"] = "no-such-preset"
    with pytest.raises(deploy.DeployError, match="form would not load"):
        deploy.validate(env)


def test_typos_in_setting_names_stop_the_deploy():
    with pytest.raises(deploy.DeployError, match="OPERATOR_NAM"):
        deploy.app_values({"OPERATOR_NAM": "Acme"})


def test_variables_use_railway_references_not_copies(env_file):
    env = deploy.read_env(env_file)
    env["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/carbuyout"
    variables = deploy.railway_variables(env, "abc123")
    assert variables["DATABASE_URL"] == "${{Postgres.DATABASE_URL}}"
    assert variables["S3_SECRET_ACCESS_KEY"] == "${{photos.SECRET_ACCESS_KEY}}"
    assert (variables["APP_ENV"], variables["STORAGE_BACKEND"]) == ("production", "s3")
    assert variables["CLIENT_IP_HEADER"] == "X-Real-IP"
    assert variables["GIT_SHA"] == "abc123"
    # Deploy-only and local-only keys never reach the app; empty ones are left out.
    for key in ("RAILWAY_PROJECT_ID", "RAILWAY_BUCKET_REGION", "LOCAL_STORAGE_DIR", "PUBLIC_URL"):
        assert key not in variables


def brand_files(tmp_path):
    """A client's light logo and a landscape photo, as the installer saves them."""
    from PIL import Image, ImageDraw

    logo = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
    ImageDraw.Draw(logo).ellipse((50, 50, 650, 650), fill=(255, 255, 255, 255))
    logo.save(tmp_path / "Logo.PNG")
    Image.new("RGB", (1800, 1100), (90, 120, 160)).save(tmp_path / "lot.jpg")
    return {"BRAND_LOGO": str(tmp_path / "Logo.PNG"), "BRAND_PHOTO": str(tmp_path / "lot.jpg")}


def test_brand_files_go_to_the_app_as_paths_inside_the_upload(env_file, tmp_path):
    env = {**deploy.read_env(env_file), **brand_files(tmp_path)}
    variables = deploy.railway_variables(env, "abc123")
    assert variables["BRAND_LOGO"] == "brand/logo.png"
    assert variables["BRAND_PHOTO"] == "brand/photo.jpg"
    assert "BRAND_ICON" not in variables


def test_brand_files_are_checked_before_anything_is_created(env_file, tmp_path):
    env = {**deploy.read_env(env_file), **brand_files(tmp_path)}
    deploy.fill_secrets(env_file, env)
    deploy.validate(env)
    (tmp_path / "lot.jpg").write_text("not a photo")
    with pytest.raises(deploy.DeployError, match="A brand file would not work: BRAND_PHOTO"):
        deploy.validate(env)


def test_the_upload_is_the_commit_plus_the_brand_files(tmp_path):
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=BASE_DIR
    ).stdout.strip()
    files = brand_files(tmp_path)
    upload = tmp_path / "upload"
    upload.mkdir()
    deploy.stage(files, sha, upload)
    assert (upload / "Dockerfile").is_file()
    assert (upload / "brand" / "README.md").is_file()
    assert (upload / "brand" / "logo.png").read_bytes() == (tmp_path / "Logo.PNG").read_bytes()
    assert (upload / "brand" / "photo.jpg").is_file()
    # Only committed files: no git folder, no settings, no local environment.
    for name in (".git", ".venv", "clients", ".env"):
        assert not (upload / name).exists()


@pytest.mark.parametrize(
    ("env", "name"),
    [
        ({"BRAND_NAME": "Acme Auto Buyers"}, "acme-auto-buyers"),
        ({"RAILWAY_PROJECT_NAME": "Acme (TX)", "BRAND_NAME": "x"}, "acme-tx"),
        ({}, "car-buyout"),
    ],
)
def test_project_name(env, name):
    assert deploy.project_name(env) == name


def test_health_wait_needs_the_new_commit(monkeypatch):
    answers = iter(
        [
            None,
            {"status": "ok", "version": "old", "revision": "r1"},
            {"status": "error", "reason": "migrations", "version": "new"},
            {"status": "ok", "version": "new", "revision": "r2"},
        ]
    )
    monkeypatch.setattr(deploy, "health", lambda url: next(answers))
    monkeypatch.setattr(deploy.time, "sleep", lambda seconds: None)
    assert deploy.wait_until_live("x.up.railway.app", "new")["revision"] == "r2"


def test_health_wait_gives_up(monkeypatch):
    monkeypatch.setattr(deploy, "health", lambda url: {"status": "ok", "version": "old"})
    monkeypatch.setattr(deploy.time, "sleep", lambda seconds: None)
    with pytest.raises(deploy.DeployError, match="railway logs"):
        deploy.wait_until_live("x.up.railway.app", "new", timeout=0.01)


# What `railway postgres pitr status --json` answers (seen on a live project).
BACKUPS_ON = {
    "enabled": True,
    "bucketWired": True,
    "live": {"available": True, "archiverHealthy": True},
}
BACKUPS_OFF = {"enabled": False, "bucketWired": False, "live": {"available": False}}
LIVE = {"version": "abc123def4567890", "revision": "r2"}


class FakeRailway:
    """The backup commands, answered in turn: a status, or an error to raise."""

    def __init__(self, monkeypatch, *statuses, enable_error=None):
        self.statuses = iter(statuses)
        self.enable_error = enable_error
        self.calls = []
        monkeypatch.setattr(deploy, "railway_json", self.json)
        monkeypatch.setattr(deploy, "railway", self.run)
        monkeypatch.setattr(deploy.time, "sleep", lambda seconds: None)

    def json(self, *args):
        self.calls.append(args)
        answer = next(self.statuses)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def run(self, *args, **kwargs):
        self.calls.append(args)
        if self.enable_error:
            raise self.enable_error
        return "{}"

    @property
    def enabled(self):
        return any("enable" in call for call in self.calls)


def test_backups_that_are_on_are_left_alone(monkeypatch):
    railway = FakeRailway(monkeypatch, BACKUPS_ON)
    assert deploy.ensure_backups() == "on (point-in-time recovery, archive healthy)"
    assert not railway.enabled


def test_the_summary_says_whether_backups_are_on(capsys):
    on = "on (point-in-time recovery, archive healthy)"
    deploy.done({"PUBLIC_URL": "https://buy.example.com"}, "x.up.railway.app", LIVE, on)
    out = capsys.readouterr().out
    assert f"backups:         {on}" in out
    assert "Backups are OFF" not in out


def test_the_summary_cannot_be_missed_when_backups_are_off(capsys):
    deploy.done({"PUBLIC_URL": "https://buy.example.com"}, "x.up.railway.app", LIVE, None)
    out = capsys.readouterr().out
    assert "backups:         OFF" in out
    assert "#" * 60 in out and "Backups are OFF" in out


def test_backups_that_are_off_are_turned_on_and_checked(monkeypatch):
    # Railway takes a moment to report the change; only its own answer counts.
    railway = FakeRailway(monkeypatch, BACKUPS_OFF, BACKUPS_OFF, {**BACKUPS_ON, "live": {}})
    summary = deploy.ensure_backups()
    assert railway.enabled
    assert summary.startswith("on (point-in-time recovery; the archive has not reported yet")


def test_a_deploy_stops_when_backups_cannot_be_turned_on(monkeypatch):
    failed = deploy.DeployError("`railway postgres pitr enable` failed: not allowed")
    FakeRailway(monkeypatch, BACKUPS_OFF, enable_error=failed)
    with pytest.raises(deploy.DeployError) as caught:
        deploy.ensure_backups()
    message = str(caught.value)
    assert "backups are not on" in message and "not allowed" in message
    # It says what to do: update the CLI, turn them on by hand, or the flag.
    assert "railway upgrade" in message and "Enable PITR" in message
    assert "--no-backups" in message


@pytest.mark.parametrize(
    "answer",
    [
        deploy.DeployError("`railway postgres pitr status` failed: unrecognized subcommand"),
        ValueError("Expecting value"),
        {"message": "no state here"},
    ],
)
def test_a_deploy_stops_when_the_backup_state_cannot_be_read(monkeypatch, answer):
    railway = FakeRailway(monkeypatch, answer)
    with pytest.raises(deploy.DeployError, match="status could not be read"):
        deploy.ensure_backups()
    assert not railway.enabled


def test_a_deploy_stops_when_railway_still_reports_backups_off(monkeypatch):
    FakeRailway(monkeypatch, *[BACKUPS_OFF] * (1 + deploy.BACKUP_CHECKS))
    with pytest.raises(deploy.DeployError, match="still reports them off"):
        deploy.ensure_backups()


def test_no_backups_goes_on_without_them_only_when_asked(monkeypatch):
    failed = deploy.DeployError("`railway postgres pitr enable` failed: not allowed")
    FakeRailway(monkeypatch, BACKUPS_OFF, enable_error=failed)
    assert deploy.ensure_backups(required=False) is None
    # The flag never turns backups off: where they come on, the summary says so.
    FakeRailway(monkeypatch, BACKUPS_ON)
    assert deploy.ensure_backups(required=False).startswith("on")
