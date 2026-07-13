"""Behaviour of the container entrypoint around database migrations.

Under Kubernetes a PreSync Job owns migrations, so every pod must boot without
running them -- otherwise each replica races the others. The entrypoint gates
`migrate` behind RUN_MIGRATIONS_ON_BOOT.

These tests execute the real script with `python` and `gunicorn` replaced by
stubs that record their arguments, so nothing touches a database.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = ROOT / "entrypoint.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("sh") is None, reason="POSIX shell unavailable on this platform"
)


def _run_entrypoint(tmp_path, env_overrides):
    """Run entrypoint.sh with stubbed python/gunicorn; return their recorded argv."""
    log = tmp_path / "calls.log"
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()

    for name in ("python", "gunicorn"):
        stub = stub_dir / name
        stub.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n', encoding="utf-8")
        stub.chmod(0o755)

    env = {**os.environ}
    # The developer's shell may already export these; drop them so each test
    # controls the flag it is asserting on.
    env.pop("RUN_MIGRATIONS_ON_BOOT", None)
    env.pop("DJANGO_COLLECTSTATIC", None)
    env["PATH"] = f"{stub_dir}{os.pathsep}{os.environ['PATH']}"
    env.update(env_overrides)
    result = subprocess.run(
        ["sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    return log.read_text(encoding="utf-8") if log.exists() else ""


def test_migrations_are_skipped_when_disabled(tmp_path):
    calls = _run_entrypoint(tmp_path, {"RUN_MIGRATIONS_ON_BOOT": "0"})

    assert "migrate" not in calls
    assert "gunicorn" in calls


def test_migrations_run_when_enabled(tmp_path):
    calls = _run_entrypoint(tmp_path, {"RUN_MIGRATIONS_ON_BOOT": "1"})

    assert "python manage.py migrate --noinput" in calls
    assert "gunicorn" in calls


def test_migrations_run_by_default(tmp_path):
    """Compose is the active deploy path and its host file may predate this flag,
    so an unset variable must keep migrating rather than silently skip."""
    calls = _run_entrypoint(tmp_path, {})

    assert "python manage.py migrate --noinput" in calls


def test_gunicorn_starts_even_when_migrations_are_skipped(tmp_path):
    calls = _run_entrypoint(tmp_path, {"RUN_MIGRATIONS_ON_BOOT": "0"})

    assert "gunicorn config.wsgi:application" in calls
