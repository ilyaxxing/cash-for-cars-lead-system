"""Deploy one client's instance to Railway: an env file in, a working URL out.

    .venv/bin/python tools/deploy.py clients/acme.env

The env file holds the client's settings (start from .env.example) and is the
only input. It lives outside git: `clients/` is ignored. The first run creates
the Railway project and writes its id back into the file; later runs update
the same project. Every run:

1. Checks the tools and the code: the Railway CLI is signed in and the git
   tree is clean, because what gets uploaded must be exactly the commit that
   /healthz will report.
2. Fills in what the file lacks and must never change afterwards: SECRET_KEY
   and the VAPID key pair, written back into the file. New keys would sign
   the owner out and switch notifications off on every device.
3. Validates the settings, the preset and the texts as production would,
   before anything is created on Railway.
4. Creates or links the project, its Postgres, the photo bucket and the app
   service, and turns on point-in-time recovery for the database.
5. Sets the app's variables. Database and bucket credentials are Railway
   references, so their values never pass through this machine.
6. Configures the health check, adds a domain, uploads and builds the code:
   exactly the commit (git archive), plus the client's brand files named in
   the env file (logo, icon, photo), which live outside git in clients/.
7. Waits until https://<domain>/healthz reports this commit and the latest
   migration. The deploy is done when the new code answers, not when the
   build ends: the Telegram bot this grew out of once "deployed" and then
   stayed down for an hour because nobody looked.

Secrets reach Railway on stdin, never on a command line, and are never printed.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_SERVICE = "app"
DB_SERVICE = "Postgres"
BUCKET = "photos"
# The bucket's region cannot change after creation. Railway puts new
# services in US West by default, so the bucket goes next to them.
DEFAULT_BUCKET_REGION = "sjc"
HEALTH_PATH = "/healthz"
HEALTH_TIMEOUT = 15 * 60

# Read by this script, never sent to the app.
DEPLOY_KEYS = {
    "RAILWAY_PROJECT_NAME",
    "RAILWAY_PROJECT_ID",
    "RAILWAY_WORKSPACE",
    "RAILWAY_BUCKET_REGION",
    # tools/deploy_vps.py, for a server of the client's own.
    "VPS_HOST",
    "DOCKER_MIRROR",
    "POSTGRES_PASSWORD",
    "BACKUP_DAYS",
}


def ref(resource: str, variable: str) -> str:
    """A Railway variable reference, resolved by Railway at deploy time."""
    return "${{" + f"{resource}.{variable}" + "}}"


# Set by this script from Railway itself; a value in the file (copied from
# .env.example for local development) is ignored.
MANAGED = {
    "APP_ENV": "production",
    "STORAGE_BACKEND": "s3",
    # Railway's edge puts the visitor's address here (docs: Public Networking,
    # Specs & Limits) and replaces any value the client sends (checked live on
    # 2026-10-20). X-Forwarded-For is not used: Railway does not document it.
    "CLIENT_IP_HEADER": "X-Real-IP",
    "DATABASE_URL": ref(DB_SERVICE, "DATABASE_URL"),
    "S3_ENDPOINT_URL": ref(BUCKET, "ENDPOINT"),
    "S3_REGION": ref(BUCKET, "REGION"),
    "S3_BUCKET": ref(BUCKET, "BUCKET"),
    "S3_ACCESS_KEY_ID": ref(BUCKET, "ACCESS_KEY_ID"),
    "S3_SECRET_ACCESS_KEY": ref(BUCKET, "SECRET_ACCESS_KEY"),
}
# Settings the server never gets: paths on this computer (the card is made
# here, with CARD_FONT) and the commit, which the deploy sets itself.
IGNORED = {"LOCAL_STORAGE_DIR", "GIT_SHA", "CARD_FONT"}
# Settings fields that are not configuration (paths for tests, values
# Railway provides on its own).
INTERNAL = {
    "PRESETS_DIR",
    "LOCALES_DIR",
    "FRONTEND_DIST",
    "RAILWAY_PUBLIC_DOMAIN",
    "RAILWAY_GIT_COMMIT_SHA",
}
SECRET_KEYS = {"SECRET_KEY", "OWNER_PASSWORD", "VAPID_PRIVATE_KEY"}
# The client's own files, named in the env file by a path on this machine:
# images, and the form, texts and policy for another market. They are
# uploaded into brand/ next to the code, and the app is told that path.
CLIENT_FILES = {
    "BRAND_LOGO": "logo",
    "BRAND_ICON": "icon",
    "BRAND_PHOTO": "photo",
    "PRESET_FILE": "preset",
    "LOCALE_FILE": "locale",
    "PRIVACY_POLICY_FILE": "privacy-policy",
}
BRAND_DIR = "brand"
# VAPID_SUBJECT as shipped in .env.example.
EXAMPLE_PUSH_CONTACT = "mailto:owner@example.com"

LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


class DeployError(Exception):
    pass


def step(text: str) -> None:
    print(f"\n==> {text}", flush=True)


def note(text: str) -> None:
    print(f"    {text}", flush=True)


# --- the env file ------------------------------------------------------------------


def read_env(path: Path) -> dict[str, str]:
    """KEY=VALUE lines; comments, blank lines and optional quotes as in .env."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = LINE_RE.match(line)
        if not match:
            raise DeployError(f"{path}: cannot read line {line.split('=')[0]!r}")
        key, value = match.groups()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def write_env_value(path: Path, key: str, value: str, comment: str) -> None:
    """Fill an empty KEY= line in place, or append the key with a comment."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = LINE_RE.match(line)
        if match and match.group(1) == key:
            lines[index] = f"{key}={value}"
            break
    else:
        lines += ["", f"# {comment}", f"{key}={value}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def known_keys() -> set[str]:
    from app.config import Settings

    return {name.upper() for name in Settings.model_fields} - INTERNAL


def app_values(env: Mapping[str, str]) -> dict[str, str]:
    """What the app gets from the file: known settings that are not managed here."""
    unknown = sorted(set(env) - known_keys() - DEPLOY_KEYS - IGNORED)
    if unknown:
        raise DeployError("Unknown settings in the env file (a typo?): " + ", ".join(unknown))
    return {
        key: value
        for key, value in env.items()
        if key not in DEPLOY_KEYS and key not in MANAGED and key not in IGNORED
    }


def local_file(value: str) -> Path:
    """A path from the env file: relative to the repository, as the app reads it."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def uploaded_name(key: str, value: str) -> str:
    """Where a brand file lands in the upload, e.g. brand/logo.png."""
    return f"{BRAND_DIR}/{CLIENT_FILES[key]}{local_file(value).suffix.lower()}"


def railway_variables(env: Mapping[str, str], sha: str) -> dict[str, str]:
    """Every variable the app service gets; empty values are left out."""
    values = {key: value for key, value in app_values(env).items() if value}
    for key in CLIENT_FILES.keys() & values.keys():
        values[key] = uploaded_name(key, values[key])
    return {**values, **MANAGED, "GIT_SHA": sha}


def fill_secrets(path: Path, env: dict[str, str]) -> list[str]:
    """Fill in what the file lacks: SECRET_KEY, VAPID keys, the push contact.

    Returns the names added.
    """
    from app.cli import new_vapid_keys

    added = []
    today = date.today().isoformat()
    if not env.get("SECRET_KEY"):
        env["SECRET_KEY"] = secrets.token_urlsafe(48)
        write_env_value(
            path,
            "SECRET_KEY",
            env["SECRET_KEY"],
            f"Generated by tools/deploy.py on {today}. Keep it: a new one signs the owner out.",
        )
        added.append("SECRET_KEY")
    if "push" in env.get("NOTIFY_CHANNELS", "push") and not (
        env.get("VAPID_PUBLIC_KEY") and env.get("VAPID_PRIVATE_KEY")
    ):
        for key, value in new_vapid_keys().items():
            env[key] = value
            write_env_value(
                path,
                key,
                value,
                f"Generated by tools/deploy.py on {today}. Keep it: new keys switch "
                "notifications off on every device.",
            )
            added.append(key)
    # Push services write to this address about delivery problems. The
    # example value from .env.example would send that to nobody.
    if env.get("OPERATOR_EMAIL") and env.get("VAPID_SUBJECT", "") in ("", EXAMPLE_PUSH_CONTACT):
        env["VAPID_SUBJECT"] = f"mailto:{env['OPERATOR_EMAIL']}"
        write_env_value(path, "VAPID_SUBJECT", env["VAPID_SUBJECT"], "Contact for push services.")
        added.append("VAPID_SUBJECT")
    return added


def validate(env: Mapping[str, str]) -> None:
    """Load the settings, preset and texts the way production will."""
    from pydantic import ValidationError

    from app.config import Settings
    from app.i18n import load_messages
    from app.preset.loader import check_texts, load_preset
    from app.web.privacy import check_policy

    public_url = env.get("PUBLIC_URL", "")
    if public_url and not public_url.startswith("https://"):
        raise DeployError(
            f"PUBLIC_URL is {public_url!r}. Leave it empty to use the Railway address, "
            "or set the client's own https:// domain."
        )
    # Empty values are left out, as on Railway: the app uses its defaults.
    values: dict[str, Any] = {key.lower(): value for key, value in app_values(env).items() if value}
    # Stand-ins for what Railway provides, so the production checks can run.
    values.update(
        app_env="production",
        storage_backend="s3",
        database_url="postgresql://check@localhost/check",
        s3_bucket="check",
        s3_access_key_id="check",
        s3_secret_access_key="check",
        railway_public_domain="check.up.railway.app",
    )
    try:
        settings = Settings(_env_file=None, **values)
    except ValidationError as exc:
        problems = "\n".join(
            f"  - {error['msg'].removeprefix('Value error, ')}" for error in exc.errors()
        )
        raise DeployError(f"The settings would not start in production:\n{problems}") from None
    try:
        preset = load_preset(settings.presets_dir, settings.preset, settings.preset_file)
        messages = load_messages(settings.locales_dir, settings.locale, settings.locale_file)
        check_texts(preset, messages)
        check_policy(settings)
    except Exception as exc:
        raise DeployError(f"The form would not load: {exc}") from None
    # The same checks the app runs at startup, on the files on this machine.
    from app.branding import Brand, BrandError

    try:
        Brand.load(settings).icons  # noqa: B018 (drawn to be sure they can be)
    except BrandError as exc:
        raise DeployError(f"A brand file would not work: {exc}") from None


# --- Railway -------------------------------------------------------------------------


def railway_cli() -> str:
    # The full path: on Windows the CLI installed by npm is railway.cmd, which
    # subprocess finds only by its full name.
    return shutil.which("railway") or "railway"


def railway(*args: str, stdin: str | None = None, check: bool = True) -> str:
    result = subprocess.run(
        [railway_cli(), *args], input=stdin, capture_output=True, text=True, cwd=ROOT
    )
    if check and result.returncode != 0:
        # The arguments never carry secrets; stdin may, so it is not echoed.
        output = (result.stderr or result.stdout).strip()
        raise DeployError(f"`railway {' '.join(args)}` failed:\n{output}")
    return result.stdout


def railway_json(*args: str) -> Any:
    output = railway(*args, "--json")
    # Some commands print prompts' answers before the JSON.
    start = min((i for i in (output.find("{"), output.find("[")) if i >= 0), default=-1)
    if start < 0:
        raise DeployError(f"`railway {' '.join(args)}` returned no JSON")
    return json.loads(output[start:])


def names(edges: Mapping[str, Any]) -> set[str]:
    return {edge["node"]["name"] for edge in edges.get("edges", [])}


def git_sha() -> str:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True, cwd=ROOT
        ).stdout.strip()

    if git("status", "--porcelain"):
        raise DeployError(
            "The git tree has uncommitted or untracked files. Commit or stash them: "
            "the upload must be exactly the commit /healthz will report."
        )
    return git("rev-parse", "HEAD")


def project_name(env: Mapping[str, str]) -> str:
    raw = env.get("RAILWAY_PROJECT_NAME") or env.get("BRAND_NAME") or "car-buyout"
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-") or "car-buyout"


def ensure_project(path: Path, env: dict[str, str]) -> None:
    if env.get("RAILWAY_PROJECT_ID"):
        railway("link", "--project", env["RAILWAY_PROJECT_ID"], "--environment", "production")
        note(f"linked project {env['RAILWAY_PROJECT_ID']}")
        return
    name = project_name(env)
    args = ["init", "--name", name]
    if env.get("RAILWAY_WORKSPACE"):
        args += ["--workspace", env["RAILWAY_WORKSPACE"]]
    created = railway_json(*args)
    env["RAILWAY_PROJECT_ID"] = created["id"]
    write_env_value(
        path,
        "RAILWAY_PROJECT_ID",
        created["id"],
        "Railway project of this client, written by tools/deploy.py.",
    )
    note(f"created project {name} ({created['id']})")


def ensure_resources(env: Mapping[str, str]) -> None:
    status = railway_json("status")
    services, buckets = names(status["services"]), names(status["buckets"])
    if DB_SERVICE not in services:
        railway_json("add", "--database", "postgres")
        note("added Postgres")
    if BUCKET not in buckets:
        region = env.get("RAILWAY_BUCKET_REGION") or DEFAULT_BUCKET_REGION
        railway_json("bucket", "create", BUCKET, "--region", region)
        note(f"added bucket {BUCKET} in {region}")
    if APP_SERVICE not in services:
        railway_json("add", "--service", APP_SERVICE)
        note(f"added service {APP_SERVICE}")


def ensure_backups() -> None:
    """Point-in-time recovery: the database can be restored to any minute."""
    try:
        state = railway_json("postgres", "pitr", "status", "--service", DB_SERVICE)
    except DeployError as exc:
        note(f"WARNING: could not read backup status, check it by hand: {exc}")
        return
    if state.get("enabled") is True:
        live = state.get("live") or {}
        healthy = "healthy" if live.get("archiverHealthy") else "archiver not reporting yet"
        note(f"point-in-time recovery is on ({healthy})")
        return
    try:
        railway("postgres", "pitr", "enable", "--service", DB_SERVICE, "--json")
        note("turned on point-in-time recovery")
    except DeployError as exc:
        note(f"WARNING: point-in-time recovery is off and could not be turned on: {exc}")


def set_variables(variables: Mapping[str, str], env: Mapping[str, str]) -> None:
    current = railway_json("variable", "list", "--service", APP_SERVICE)
    plain = {k: v for k, v in variables.items() if k not in SECRET_KEYS}
    railway(
        "variable", "set", "--service", APP_SERVICE, "--skip-deploys",
        *(f"{key}={value}" for key, value in plain.items()),
    )  # fmt: skip
    for key in SECRET_KEYS & variables.keys():
        if current.get(key) != variables[key]:
            railway(
                "variable", "set", key, "--stdin", "--service", APP_SERVICE, "--skip-deploys",
                stdin=variables[key],
            )  # fmt: skip
    # A setting emptied in the file is removed, so the app falls back to its default.
    for key in sorted(k for k, v in env.items() if not v and k in current and k not in MANAGED):
        railway("variable", "delete", key, "--service", APP_SERVICE)
        note(f"removed {key}")
    note(f"{len(variables)} variables set")


def configure_service() -> None:
    railway(
        "environment", "edit",
        "--service-config", APP_SERVICE, "build.builder", "DOCKERFILE",
        "--service-config", APP_SERVICE, "deploy.healthcheckPath", HEALTH_PATH,
        "--service-config", APP_SERVICE, "deploy.healthcheckTimeout", "300",
        "--message", "Health check and Dockerfile build (tools/deploy.py)",
    )  # fmt: skip
    note(f"health check {HEALTH_PATH}, Dockerfile build")


def ensure_domains(env: Mapping[str, str]) -> str:
    """The Railway address the deploy waits on; adds the client's domain if set."""
    domains = railway_json("domain", "list", "--service", APP_SERVICE)["domains"]
    service_domain = next((d["domain"] for d in domains if d["type"] == "service"), None)
    if not service_domain:
        service_domain = railway_json("domain", "--service", APP_SERVICE)["domain"]
        service_domain = service_domain.removeprefix("https://")
        note(f"added {service_domain}")
    custom = env.get("PUBLIC_URL", "").removeprefix("https://").rstrip("/")
    if custom and custom != service_domain and all(d["domain"] != custom for d in domains):
        print(railway("domain", custom, "--service", APP_SERVICE))
        note(f"added {custom}: create the DNS records above at the domain's registrar")
    return service_domain


def stage(env: Mapping[str, str], sha: str, into: Path) -> None:
    """What gets uploaded: the commit itself, plus the client's own files."""
    archive = subprocess.run(
        ["git", "archive", "--format=tar", sha], capture_output=True, check=True, cwd=ROOT
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(into, filter="data")
    (into / BRAND_DIR).mkdir(exist_ok=True)
    for key in CLIENT_FILES:
        if env.get(key):
            shutil.copyfile(local_file(env[key]), into / uploaded_name(key, env[key]))


def deploy(env: Mapping[str, str], sha: str) -> None:
    with tempfile.TemporaryDirectory(prefix="deploy-") as folder:
        upload = Path(folder)
        stage(env, sha, upload)
        # The staged folder is the upload as it is: the client's files are ignored
        # by .gitignore, which must not drop them here. The project link is
        # read from the repository, so the command runs there.
        result = subprocess.run(
            [
                railway_cli(), "up", str(upload), "--path-as-root", "--no-gitignore",
                "--service", APP_SERVICE, "--ci",
            ],
            cwd=ROOT,
            check=False,
        )  # fmt: skip
    if result.returncode != 0:
        raise DeployError("The build failed; its log is above.")


def health(url: str) -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read())
        except ValueError:
            return None
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def wait_until_live(
    domain: str,
    sha: str,
    timeout: float = HEALTH_TIMEOUT,
    logs: str = f"railway logs --service {APP_SERVICE}",
) -> dict[str, Any]:
    url = f"https://{domain}{HEALTH_PATH}"
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        body = health(url)
        if body != last:
            note(f"{HEALTH_PATH}: {json.dumps(body) if body else 'no answer yet'}")
            last = body
        if body and body.get("status") == "ok" and body.get("version") == sha:
            return body
        time.sleep(5)
    raise DeployError(
        f"{url} did not report commit {sha[:12]} within {timeout // 60:.0f} minutes. "
        f"Read the logs: {logs}"
    )


# --- main ------------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("env_file", type=Path, help="the client's settings, e.g. clients/acme.env")
    args = parser.parse_args()
    path: Path = args.env_file

    try:
        step("Checking tools and code")
        if not path.is_file():
            raise DeployError(f"{path} does not exist. Copy .env.example and fill it in.")
        if not shutil.which("railway"):
            raise DeployError("The Railway CLI is not installed: https://docs.railway.com/cli")
        who = railway("whoami", check=False)
        if "Logged in" not in who:
            raise DeployError("The Railway CLI is not signed in: run `railway login`.")
        note(who.strip())
        sha = git_sha()
        note(f"commit {sha[:12]}")

        step("Reading the settings")
        env = read_env(path)
        for key in fill_secrets(path, env):
            note(f"generated {key} and saved it to {path}")
        validate(env)
        variables = railway_variables(env, sha)
        note("settings, preset and texts are valid for production")

        step("Railway project")
        ensure_project(path, env)
        ensure_resources(env)
        ensure_backups()

        step("App service")
        set_variables(variables, env)
        configure_service()
        domain = ensure_domains(env)

        step(f"Uploading and building commit {sha[:12]}")
        deploy(env, sha)

        step("Waiting for the new code to answer")
        body = wait_until_live(domain, sha)
    except DeployError as exc:
        print(f"\nDeploy stopped: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

    public = env.get("PUBLIC_URL") or f"https://{domain}"
    step("Done")
    note(f"commit {body['version'][:12]}, migration {body['revision']}")
    note(f"seller form:     {public}/")
    note(f"business card:   {public}/v")
    note(f"dashboard:       {public}/app")
    if not env.get("PUBLIC_URL"):
        note("This is the Railway address. Connect the client's own domain next:")
        note("QR codes and cards are made only for it (docs/deploy.md, Custom domain).")


if __name__ == "__main__":
    main()
