"""Managed pre-commit hook tasks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from python_codeforge._invoke import Exit, task

if TYPE_CHECKING:
    from invoke.context import Context

MARKER: Final = "# managed-by: python-codeforge"
GATE: Final = "uv run invoke check"
SKIP_VARIABLE: Final = "PYTHON_CODEFORGE_SKIP_HOOK"
HOOK_MODE: Final = 0o755


def hook_script(gate: str = GATE) -> str:
    """Render the managed POSIX pre-commit hook."""
    return f"""#!/usr/bin/env sh
{MARKER} -- installed by `invoke hooks.install`, removed by `invoke hooks.uninstall`
set -eu

if [ "${{{SKIP_VARIABLE}:-0}}" = "1" ]; then
    echo "pre-commit: SKIPPED ({SKIP_VARIABLE}=1)" >&2
    exit 0
fi

echo "pre-commit: running `{gate}`" >&2
if ! {gate}; then
    echo "pre-commit: gate failed -- commit aborted." >&2
    echo "            fix it, or bypass once with {SKIP_VARIABLE}=1 git commit ..." >&2
    exit 1
fi
"""


def is_managed(text: str) -> bool:
    """Whether a hook was installed by this package."""
    return MARKER in text


def plan_install(existing: str | None, *, force: bool) -> None:
    """Refuse to replace a foreign hook unless explicitly forced."""
    if existing is None or is_managed(existing) or force:
        return
    msg = (
        "a pre-commit hook already exists and was not written by python-codeforge "
        "(no marker found).\n  Inspect it, then re-run with --force to replace it."
    )
    raise Exit(msg, code=1)


def write_hook(path: Path, text: str) -> None:
    """Write an executable hook."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(HOOK_MODE)


def hooks_dir(c: Context) -> Path:
    """Resolve Git's hooks directory, honoring ``core.hooksPath``."""
    result = c.run("git rev-parse --path-format=absolute --git-path hooks", hide=True, warn=True)
    resolved = result.stdout.strip() if result.ok else ""
    if not resolved:
        msg = "not a git repository (or git is unavailable): cannot install hooks."
        raise Exit(msg, code=1)
    return Path(resolved)


@task(help={"force": "replace a pre-commit hook not managed by this package"})
def install(c: Context, force: bool = False) -> None:
    """Install the pre-commit hook that runs ``invoke check``."""
    path = hooks_dir(c) / "pre-commit"
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    plan_install(existing, force=force)
    write_hook(path, hook_script())
    print(f"installed pre-commit hook -> {path}")


@task
def uninstall(c: Context) -> None:
    """Remove the hook only when this package installed it."""
    path = hooks_dir(c) / "pre-commit"
    if not path.exists():
        print("no pre-commit hook installed")
        return
    if not is_managed(path.read_text(encoding="utf-8")):
        msg = f"{path} was not written by python-codeforge; leaving it alone."
        raise Exit(msg, code=1)
    path.unlink()
    print(f"removed pre-commit hook <- {path}")
