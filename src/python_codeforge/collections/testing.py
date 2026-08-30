"""Test, property, coverage, and CRAP tasks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from python_codeforge import commands
from python_codeforge import coverage as coverage_gate
from python_codeforge import crap as crap_gate
from python_codeforge._invoke import task
from python_codeforge.commands import PytestRun
from python_codeforge.config import Settings, load
from python_codeforge.gate import emit

if TYPE_CHECKING:
    from invoke.context import Context


def _scope(settings: Settings, package: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not package:
        return (), ()
    if package not in settings.packages:
        msg = f"unknown package {package!r}; expected one of {list(settings.packages)}"
        raise ValueError(msg)
    return (settings.suite(package),), (package,)


@task(
    help={
        "k": "pytest -k expression",
        "fast": "skip tests marked slow or network",
        "package": "run one package's configured suite",
    }
)
def run(c: Context, k: str = "", fast: bool = False, cov: bool = True, package: str = "") -> None:
    """Run unit and property tests with optional coverage."""
    settings = load(Path(c.cwd))
    paths, coverage_packages = _scope(settings, package)
    command = PytestRun(
        k=k,
        fast=fast,
        cov=cov,
        paths=paths,
        cov_packages=coverage_packages,
    ).command()
    c.run(command, pty=True)


@task(
    help={
        "profile": "hypothesis profile: dev | ci | thorough",
        "package": "run one package's property suite",
    }
)
def properties(c: Context, profile: str = "thorough", package: str = "") -> None:
    """Run property suites with a selected Hypothesis profile."""
    settings = load(Path(c.cwd))
    paths, _ = _scope(settings, package)
    suites = paths or tuple(f"{settings.suite(name)}/properties" for name in settings.packages)
    pytest = PytestRun(paths=suites, cov=False, no_random=True).command()
    c.run(commands.hypothesis_profile(profile, pytest), pty=True)


@task
def coverage(c: Context) -> None:
    """Check per-package floors after a coverage-producing test run."""
    emit(coverage_gate.report(Path(c.cwd)))


@task
def crap(c: Context) -> None:
    """Enforce coverage-weighted complexity after a test run."""
    emit(crap_gate.report(Path(c.cwd)))
