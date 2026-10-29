"""tools/deploy_vps.py: the settings a server of the client's own gets, and the checks before it."""

import shutil
import socket
import subprocess

import pytest

from app.config import BASE_DIR
from tests.test_client_files import client_files
from tests.test_deploy import env_file  # noqa: F401 (fixture)
from tools import deploy, deploy_vps

SHA = "abc123def456"


@pytest.fixture
def env(env_file, tmp_path):  # noqa: F811
    values = deploy.read_env(env_file)
    values.update(
        VPS_HOST="root@203.0.113.10",
        PUBLIC_URL="https://buy.example.com",
        **client_files(tmp_path),
    )
    deploy.fill_secrets(env_file, values)
    deploy_vps.fill_database_password(env_file, values)
    return values


def test_the_server_gets_the_app_settings_and_the_compose_values(env):
    values = deploy_vps.server_env(env, SHA, "buy.example.com")
    assert values["APP_ENV"] == "production"
    assert values["STORAGE_BACKEND"] == "volume"
    assert values["CLIENT_IP_HEADER"] == "X-Real-IP"
    assert values["DATABASE_URL"] == f"postgresql://app:{env['POSTGRES_PASSWORD']}@db:5432/app"
    assert values["GIT_SHA"] == SHA
    assert values["DOMAIN"] == "buy.example.com"
    assert values["BACKUP_DAYS"] == "14"
    assert values["SECRET_KEY"] == env["SECRET_KEY"]
    # The client's own files, where the upload puts them.
    assert values["PRESET_FILE"] == "brand/preset.yaml"
    assert values["LOCALE_FILE"] == "brand/locale.json"
    # What only the deploy script reads stays here; nothing Railway-specific goes.
    for key in ("VPS_HOST", "DOCKER_MIRROR", "RAILWAY_PROJECT_ID", "S3_BUCKET"):
        assert key not in values


def test_the_database_password_is_made_once_and_kept(env_file):  # noqa: F811
    values = deploy.read_env(env_file)
    assert deploy_vps.fill_database_password(env_file, values)
    password = values["POSTGRES_PASSWORD"]
    again = deploy.read_env(env_file)
    assert again["POSTGRES_PASSWORD"] == password
    assert not deploy_vps.fill_database_password(env_file, again)


def test_the_server_file_takes_values_as_written(env):
    text = deploy_vps.env_text({"A": "x$y #z", "B": "plain"})
    assert text == "A='x$y #z'\nB='plain'\n"
    with pytest.raises(deploy.DeployError, match="quote"):
        deploy_vps.env_text({"A": "it's"})


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"VPS_HOST": "203.0.113.10"}, "VPS_HOST"),
        ({"PUBLIC_URL": ""}, "PUBLIC_URL"),
        ({"PUBLIC_URL": "http://buy.example.com"}, "https://"),
    ],
)
def test_the_server_and_the_domain_are_required(env, changes, message):
    with pytest.raises(deploy.DeployError, match=message):
        deploy_vps.target({**env, **changes})


def test_a_domain_that_does_not_point_at_the_server_stops_the_deploy(monkeypatch):
    monkeypatch.setattr(
        socket, "getaddrinfo", lambda *args, **kwargs: [(0, 0, 0, "", ("198.51.100.7", 443))]
    )
    deploy_vps.check_dns("buy.example.com", "198.51.100.7")
    with pytest.raises(deploy.DeployError, match=r"A record for buy\.example\.com"):
        deploy_vps.check_dns("buy.example.com", "203.0.113.10")


def test_commands_for_another_user_run_through_sudo(monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, b"", b"")

    monkeypatch.setattr(subprocess, "run", run)
    deploy_vps.remote("root@203.0.113.10", "docker ps")
    deploy_vps.remote("ubuntu@203.0.113.10", "docker ps")
    assert calls[0][-1] == "docker ps"
    assert calls[1][-1] == "sudo sh -c 'docker ps'"
    assert all("BatchMode=yes" in call for call in calls)


@pytest.mark.skipif(not shutil.which("docker"), reason="docker is not installed")
def test_the_compose_file_is_valid(tmp_path):
    (tmp_path / ".env").write_text("POSTGRES_PASSWORD=x\nDOMAIN=buy.example.com\n")
    (tmp_path / "src").symlink_to(BASE_DIR)
    result = subprocess.run(
        ["docker", "compose", "--project-directory", str(tmp_path), "-f", deploy_vps.COMPOSE,
         "--env-file", ".env", "config", "--quiet"],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("services", "running"), [("app\nbackup\ncaddy\ndb\n", True), ("app\ndb\n", False)]
)
def test_the_backups_count_only_while_the_daily_dump_runs(monkeypatch, services, running):
    commands = []

    def remote(host, command, **kwargs):
        commands.append(command)
        return services

    monkeypatch.setattr(deploy_vps, "remote", remote)
    folder = "/opt/cash-for-cars/acme"
    assert deploy_vps.backups_running("root@203.0.113.10", folder, "acme") is running
    assert "ps --status running --services" in commands[0]


LIVE = {"version": SHA, "revision": "r2"}


def test_the_summary_says_how_the_database_is_backed_up(env, capsys):
    deploy_vps.done({**env, "BACKUP_DAYS": "21"}, LIVE, "acme", backups=True)
    out = capsys.readouterr().out
    assert "backups:         a database dump a day, kept 21 days on the server" in out
    assert "Backups are OFF" not in out


def test_the_summary_cannot_be_missed_when_the_dump_is_not_running(env, capsys):
    deploy_vps.done(env, LIVE, "acme", backups=False)
    out = capsys.readouterr().out
    assert "backups:         OFF" in out and "Backups are OFF" in out
    assert "ssh root@203.0.113.10 'docker compose -p acme logs backup'" in out
