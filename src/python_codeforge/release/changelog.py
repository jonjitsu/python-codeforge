"""Promote hand-written changelog entries into release notes."""

import re

from python_codeforge.release.version import Version

UNRELEASED = "## Unreleased"

_HEADING = re.compile(r"## (?P<text>[^\r\n]+?)\s*$")


class NothingToReleaseError(Exception):
    """The unreleased section has no content to publish."""


def promote(notes: str, version: Version) -> str:
    """Move unreleased notes beneath ``version`` and open a fresh section."""
    if not has_unreleased(notes):
        raise NothingToReleaseError
    _, end = _find_heading(notes, UNRELEASED)
    return f"{notes[:end]}\n\n## {version}{notes[end:]}"


def has_unreleased(notes: str) -> bool:
    """Return whether the unreleased section contains content."""
    return bool(_body_after(notes, UNRELEASED))


def section(notes: str, version: Version) -> str:
    """Return the release-note body for ``version``."""
    return _body_after(notes, f"## {version}")


def _body_after(notes: str, heading: str) -> str:
    """Return content between ``heading`` and the next second-level heading."""
    start, end = _find_heading(notes, heading)
    following = next(
        (next_start for next_start, _, _ in _headings(notes) if next_start > start),
        None,
    )
    return notes[end:following].strip()


def _find_heading(notes: str, heading: str) -> tuple[int, int]:
    for start, end, text in _headings(notes):
        if text == heading:
            return start, end
    message = f"CHANGELOG.md has no {heading!r} heading"
    raise ValueError(message)


def _headings(notes: str) -> tuple[tuple[int, int, str], ...]:
    """Return second-level Markdown headings that are outside fenced code."""
    headings: list[tuple[int, int, str]] = []
    offset = 0
    fence = ""
    for line in notes.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        stripped = content.lstrip()
        if fence:
            if stripped.startswith(fence * 3):
                fence = ""
        elif stripped.startswith(("```", "~~~")):
            fence = stripped[0]
        elif (match := _HEADING.fullmatch(content)) is not None:
            headings.append((offset, offset + len(content), f"## {match['text'].rstrip()}"))
        offset += len(line)
    return tuple(headings)
