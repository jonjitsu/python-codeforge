"""Named changelog regressions and repository invariants."""

import re

import pytest

from ci import changelog, project
from ci.version import Version

NOTES = """# Changelog

## Unreleased

- Something worth shipping.

## 1.0.0

First implementation.
"""

EMPTY = """# Changelog

## Unreleased

## 1.0.0

First implementation.
"""


def test_empty_unreleased_section_is_not_a_release() -> None:
    """An empty standing section must not create a meaningless release."""
    with pytest.raises(changelog.NothingToReleaseError):
        changelog.promote(EMPTY, Version.parse("1.0.1"))


def test_missing_release_section_is_rejected() -> None:
    """Release notes must fail loudly when the requested version is absent."""
    with pytest.raises(ValueError, match=re.escape("no '## 9.9.9' heading")):
        changelog.section(NOTES, Version.parse("9.9.9"))


def test_repository_version_has_release_notes() -> None:
    """The checked-in baseline version must always have a changelog section."""
    version = project.current_version(project.PATH.read_text(encoding="utf-8"))
    assert changelog.section(changelog.PATH.read_text(encoding="utf-8"), version)
