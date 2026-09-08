"""Consumer checks for release-wheel direct URL dependencies."""

# ruff: noqa: S603, S607

from __future__ import annotations

import re
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, override

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
WHEEL_PATTERN = re.compile(
    r"^python-codeforge @ .+python_codeforge-[\d.]+-py3-none-any\.whl \\\n"
    r"    --hash=sha256:[0-9a-f]{64}$",
    re.MULTILINE,
)


class _QuietHandler(SimpleHTTPRequestHandler):
    @override
    def log_message(self, format: str, *args: object) -> None:
        _ = (format, args)


@pytest.fixture
def wheel_dist(tmp_path: Path) -> Path:
    """Build the distribution wheel in an isolated dist directory."""
    dist = tmp_path / "dist"
    dist.mkdir()
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = tuple(dist.glob("python_codeforge-*-py3-none-any.whl"))
    assert len(wheels) == 1
    return dist


@pytest.fixture
def wheel_server(wheel_dist: Path) -> Iterator[str]:
    """Serve the built wheel over HTTP for uv and pip-audit."""
    wheels = tuple(wheel_dist.glob("python_codeforge-*-py3-none-any.whl"))
    assert len(wheels) == 1
    wheel_name = wheels[0].name

    handler = partial(_QuietHandler, directory=str(wheel_dist))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    host = str(server.server_address[0])
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}/{wheel_name}"
    finally:
        server.shutdown()
        thread.join(timeout=1)
        server.server_close()


@pytest.mark.network
@pytest.mark.slow
def test_release_wheel_supports_uv_lock_export_and_pip_audit_strict(
    tmp_path: Path,
    wheel_server: str,
) -> None:
    """A hashed release-wheel URL locks, exports, and audits through pip-audit --strict."""
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    (consumer / "pyproject.toml").write_text(
        '[project]\nname = "wheel-consumer"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\n'
        'dependencies = ["python-codeforge"]\n\n'
        "[tool.uv.sources]\n"
        f'python-codeforge = {{ url = "{wheel_server}" }}\n',
        encoding="utf-8",
    )

    subprocess.run(["uv", "lock"], cwd=consumer, check=True, capture_output=True, text=True)
    lock = (consumer / "uv.lock").read_text(encoding="utf-8")
    assert wheel_server in lock
    assert "hash = " in lock

    export = subprocess.run(
        ["uv", "export", "--frozen", "--all-groups", "--no-emit-project"],
        cwd=consumer,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert WHEEL_PATTERN.search(export) is not None

    export_path = consumer / "export.txt"
    export_path.write_text(export, encoding="utf-8")
    subprocess.run(
        [
            "uv",
            "run",
            "pip-audit",
            "-s",
            "osv",
            "--strict",
            "--progress-spinner=off",
            "-r",
            str(export_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
