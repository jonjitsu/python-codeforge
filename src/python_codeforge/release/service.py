"""Filesystem boundary for preparing and reading project releases."""

from dataclasses import dataclass
from pathlib import Path

from python_codeforge.release import changelog, commits, project
from python_codeforge.release.version import Version

CHANGELOG = "CHANGELOG.md"
PYPROJECT = "pyproject.toml"


@dataclass(frozen=True, slots=True)
class PreparedRelease:
    """A release proposal written into a project's working tree."""

    version: Version
    level: str
    unconventional: tuple[str, ...]


def prepare(root: Path) -> PreparedRelease | None:
    """Promote pending notes and bump project metadata beneath ``root``."""
    changelog_path = root / CHANGELOG
    project_path = root / PYPROJECT
    changelog_text = changelog_path.read_text(encoding="utf-8")
    project_text = project_path.read_text(encoding="utf-8")
    if not changelog.has_unreleased(changelog_text):
        return None

    messages = commits.since(root, commits.latest_tag(root))
    level = commits.bump_level(messages)
    next_version = project.current_version(project_text).bumped(level)
    promoted = changelog.promote(changelog_text, next_version)
    updated_project = project.with_version(project_text, next_version)

    changelog_path.write_text(promoted, encoding="utf-8")
    project_path.write_text(updated_project, encoding="utf-8")
    return PreparedRelease(
        version=next_version,
        level=level,
        unconventional=tuple(commits.unconventional(messages)),
    )


def version(root: Path) -> Version:
    """Return the version declared by the project beneath ``root``."""
    return project.current_version((root / PYPROJECT).read_text(encoding="utf-8"))


def notes(root: Path) -> str:
    """Return release notes for the project's currently declared version."""
    current = version(root)
    return changelog.section((root / CHANGELOG).read_text(encoding="utf-8"), current)
