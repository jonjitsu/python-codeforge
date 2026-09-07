"""Invoke entry points for release preparation and release notes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ci import changelog, commits, project
from python_codeforge import task

if TYPE_CHECKING:
    from invoke.context import Context


@task(name="release-prepare")
def release_prepare(context: Context) -> None:
    """Bump the version, promote the changelog, and refresh the lockfile."""
    notes = changelog.PATH.read_text(encoding="utf-8")
    pyproject = project.PATH.read_text(encoding="utf-8")
    if not changelog.has_unreleased(notes):
        print(f"nothing under '{changelog.UNRELEASED}'; no release to prepare")
        return

    messages = commits.since(commits.latest_tag())
    level = commits.bump_level(messages)
    version = project.current_version(pyproject).bumped(level)

    changelog.PATH.write_text(changelog.promote(notes, version), encoding="utf-8")
    project.PATH.write_text(project.with_version(pyproject, version), encoding="utf-8")
    context.run("uv lock", hide=True)

    for subject in commits.unconventional(messages):
        print(f"note: untyped commit counted as a patch: {subject}")
    print(f"prepared {version} ({level})")


@task(name="release-version")
def release_version(context: Context) -> None:  # noqa: ARG001
    """Print the version declared by ``pyproject.toml``."""
    print(project.current_version(project.PATH.read_text(encoding="utf-8")))


@task(name="release-notes")
def release_notes(context: Context) -> None:  # noqa: ARG001
    """Print the current version's changelog section."""
    version = project.current_version(project.PATH.read_text(encoding="utf-8"))
    print(changelog.section(changelog.PATH.read_text(encoding="utf-8"), version))
