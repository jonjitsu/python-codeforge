"""Semantic-version parsing and arithmetic."""

from __future__ import annotations

import re
from typing import NamedTuple, Self, override

MAJOR, MINOR, PATCH = "major", "minor", "patch"

_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


class Version(NamedTuple):
    """A semantic version without prerelease or build metadata."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> Self:
        """Parse an exact ``X.Y.Z`` version."""
        match = _SEMVER.fullmatch(text.strip())
        if match is None:
            message = f"not a version: {text!r}"
            raise ValueError(message)
        return cls(*(int(part) for part in match.groups()))

    def bumped(self, level: str) -> Version:
        """Return this version bumped at ``level``."""
        if level == MAJOR:
            return Version(self.major + 1, 0, 0)
        if level == MINOR:
            return Version(self.major, self.minor + 1, 0)
        if level == PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        message = f"not a bump level: {level!r}"
        raise ValueError(message)

    @override
    def __str__(self) -> str:
        """Render the canonical ``X.Y.Z`` representation."""
        return f"{self.major}.{self.minor}.{self.patch}"
