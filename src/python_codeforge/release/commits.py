"""Infer a release bump from local Git metadata.

Git is called with a fixed executable and argument vector, never through a shell.
"""

import re
import subprocess  # nosec B404
from pathlib import Path

from python_codeforge.release.version import MAJOR, MINOR, PATCH

_HEADER = re.compile(r"\A(?P<type>[a-z]+)(?:\([^)]*\))?(?P<breaking>!)?: .")
_BREAKING_TRAILER = re.compile(r"^BREAKING[ -]CHANGE:", re.MULTILINE)

TYPES = frozenset(
    {
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "release",
        "revert",
        "style",
        "test",
    }
)


def bump_level(messages: list[str]) -> str:
    """Return the largest semantic-version bump requested by ``messages``."""
    levels = {_message_level(message) for message in messages}
    if MAJOR in levels:
        return MAJOR
    if MINOR in levels:
        return MINOR
    return PATCH


def unconventional(messages: list[str]) -> list[str]:
    """Return subjects that do not start with a recognised commit type."""
    return [message.splitlines()[0] for message in messages if not _typed(message)]


def since(root: Path, ref: str | None) -> list[str]:
    """Read every non-merge commit message after ``ref`` in ``root``."""
    span = f"refs/tags/{ref}..HEAD" if ref else "HEAD"
    output = subprocess.run(  # noqa: S603  # nosec B603 B607
        ["git", "log", "--no-merges", "--format=%B%x00", span],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [chunk.strip() for chunk in output.split("\0") if chunk.strip()]


def latest_tag(root: Path) -> str | None:
    """Return the most recent reachable tag in ``root``, if one exists."""
    found = subprocess.run(  # nosec B603 B607
        ["git", "describe", "--tags", "--abbrev=0"],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return found.stdout.strip() or None


def _message_level(message: str) -> str:
    """Return the bump requested by one commit message."""
    header = _HEADER.match(message)
    if header is None or header["type"] not in TYPES:
        return PATCH
    if header["breaking"] or _BREAKING_TRAILER.search(message):
        return MAJOR
    return MINOR if header["type"] == "feat" else PATCH


def _typed(message: str) -> bool:
    """Return whether ``message`` starts with a recognised commit type."""
    header = _HEADER.match(message)
    return header is not None and header["type"] in TYPES
