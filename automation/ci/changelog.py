"""Promote hand-written changelog entries into release notes."""

import re
from pathlib import Path

from ci.version import Version

PATH = Path("CHANGELOG.md")
UNRELEASED = "## Unreleased"

_HEADING = re.compile(r"^## ", re.MULTILINE)


class NothingToReleaseError(Exception):
    """The unreleased section has no content to publish."""


def promote(notes: str, version: Version) -> str:
    """Move unreleased notes beneath ``version`` and open a fresh section."""
    if not has_unreleased(notes):
        raise NothingToReleaseError
    return notes.replace(UNRELEASED, f"{UNRELEASED}\n\n## {version}", 1)


def has_unreleased(notes: str) -> bool:
    """Return whether the unreleased section contains content."""
    return bool(_body_after(notes, UNRELEASED))


def section(notes: str, version: Version) -> str:
    """Return the release-note body for ``version``."""
    return _body_after(notes, f"## {version}")


def _body_after(notes: str, heading: str) -> str:
    """Return content between ``heading`` and the next second-level heading."""
    start = notes.find(heading)
    if start == -1:
        message = f"CHANGELOG.md has no {heading!r} heading"
        raise ValueError(message)
    remainder = notes[start + len(heading) :]
    following = _HEADING.search(remainder)
    return remainder[: following.start() if following else None].strip()
