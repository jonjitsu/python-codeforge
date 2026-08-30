"""Formatting, linting, typing, dead-code, and metric tasks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from python_codeforge import cognitive as cognitive_gate
from python_codeforge import commands, hygiene, maintainability
from python_codeforge._invoke import Exit, task
from python_codeforge.commands import Targets
from python_codeforge.config import load
from python_codeforge.gate import emit

if TYPE_CHECKING:
    from invoke.context import Context


def _targets(c: Context) -> Targets:
    return Targets(load(Path(c.cwd)).targets)


@task
def fmt(c: Context, check: bool = False) -> None:
    """Format with Ruff and sort imports."""
    targets = _targets(c)
    c.run(commands.ruff_format(targets, check=check), pty=True)
    c.run(commands.ruff_check(targets, select="I", fix=not check), pty=True)


@task
def lint(c: Context, fix: bool = False) -> None:
    """Run Ruff over configured targets."""
    c.run(commands.ruff_check(_targets(c), fix=fix), pty=True)


@task
def types(c: Context) -> None:
    """Run mypy and Pyright using project configuration."""
    c.run(commands.mypy(), pty=True)
    c.run(commands.pyright(), pty=True)


@task
def dead(c: Context) -> None:
    """Find unused code with Vulture."""
    c.run(commands.vulture(), pty=True)


@task
def complexity(c: Context) -> None:
    """Report Radon cyclomatic complexity and maintainability."""
    source = load(Path(c.cwd)).source_dir
    c.run(commands.radon("cc", source), pty=True)
    c.run(commands.radon("mi", source), pty=True)


@task
def cognitive(c: Context) -> None:
    """Enforce per-function cognitive complexity."""
    emit(cognitive_gate.report(Path(c.cwd)))


@task
def mi(c: Context) -> None:
    """Enforce per-module maintainability."""
    emit(maintainability.report(Path(c.cwd)))


@task(name="hygiene", help={"name": "only check paths containing this substring"})
def hygiene_(c: Context, name: str = "") -> None:
    """Check tracked files for generic defects."""
    root_result = c.run("git rev-parse --show-toplevel", hide=True, warn=True)
    root = Path(root_result.stdout.strip() or c.cwd)
    listing = c.run("git ls-files -z", hide=True, warn=True).stdout
    tracked = [
        root / entry for entry in listing.split("\0") if entry and (not name or name in entry)
    ]
    findings = hygiene.check_files(tracked, root)
    for finding in findings:
        print(finding.render())
    print(f"hygiene: {len(tracked)} tracked files checked, {len(findings)} finding(s)")
    if findings:
        msg = "hygiene checks failed"
        raise Exit(msg, code=1)
