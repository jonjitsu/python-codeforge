"""Static security and dependency-audit tasks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from python_codeforge import commands
from python_codeforge._invoke import Exit, task
from python_codeforge.config import load

if TYPE_CHECKING:
    from invoke.context import Context

AUDIT_REQUIREMENTS: Final = ".audit-requirements.txt"
UNAVAILABLE: Final = (
    "semgrep's executable could not start. Run "
    "`invoke security.semgrep --container` to use the official Podman image."
)


@task
def bandit(c: Context) -> None:
    """Scan configured first-party source with Bandit."""
    c.run(commands.bandit(path=load(Path(c.cwd)).source_dir), pty=True)


@task(help={"container": "run the official Semgrep image under Podman"})
def semgrep(c: Context, container: bool = False) -> None:
    """Run Semgrep locally or in its official container."""
    if not container and not c.run(commands.semgrep_probe(), warn=True, hide=True).ok:
        raise Exit(UNAVAILABLE, code=1)
    c.run(commands.semgrep(container=container), pty=True)


@task
def audit(c: Context) -> None:
    """Audit all locked dependencies for known vulnerabilities."""
    c.run(commands.export_requirements(AUDIT_REQUIREMENTS), pty=True)
    try:
        c.run(commands.pip_audit(AUDIT_REQUIREMENTS), pty=True)
    finally:
        c.run(f"rm -f {AUDIT_REQUIREMENTS}", pty=True)


@task(pre=[bandit, audit], name="all")
def all_(c: Context) -> None:
    """Run the portable security gates: Bandit and pip-audit."""
