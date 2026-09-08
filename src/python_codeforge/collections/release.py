"""Release preparation and workflow installation tasks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from python_codeforge import release as release_domain
from python_codeforge._invoke import Exit, task
from python_codeforge.release import workflows as release_workflows

if TYPE_CHECKING:
    from collections.abc import Callable

    from invoke.context import Context


def _reading[T](operation: Callable[[Path], T], context: Context) -> T:
    """Run a release read against the context root, reporting refusals as Exit."""
    try:
        return operation(Path(context.cwd).resolve())
    except ValueError as error:
        raise Exit(str(error), code=1) from error


@task
def prepare(context: Context) -> None:
    """Bump the version, promote the changelog, and refresh the lockfile."""
    prepared = _reading(release_domain.prepare, context)
    if prepared is None:
        print(f"nothing under '{release_domain.UNRELEASED}'; no release to prepare")
        return

    context.run("uv lock", hide=True)
    for subject in prepared.unconventional:
        print(f"note: untyped commit counted as a patch: {subject}")
    print(f"prepared {prepared.version} ({prepared.level})")


@task
def version(context: Context) -> None:
    """Print the version declared by ``pyproject.toml``."""
    print(_reading(release_domain.version, context))


@task
def notes(context: Context) -> None:
    """Print the current version's changelog section."""
    print(_reading(release_domain.notes, context))


@task(help={"force": "replace differing standard workflow files, but never directories"})
def install(context: Context, force: bool = False) -> None:
    """Install the standard Gitea development and release workflows."""
    try:
        report = release_workflows.install(Path(context.cwd).resolve(), force=force)
    except release_workflows.WorkflowConflictError as error:
        raise Exit(str(error), code=1) from error
    print(f"release workflows: {report.copied} copied, {report.unchanged} unchanged")
