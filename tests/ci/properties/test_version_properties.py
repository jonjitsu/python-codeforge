"""Semantic-version invariants."""

from hypothesis import given
from hypothesis import strategies as st

from ci.version import MAJOR, MINOR, PATCH, Version

COMPONENT = st.integers(min_value=0, max_value=1_000_000)


@given(major=COMPONENT, minor=COMPONENT, patch=COMPONENT)
def test_version_round_trips(major: int, minor: int, patch: int) -> None:
    """Every supported version has one parseable canonical representation."""
    version = Version(major, minor, patch)
    assert Version.parse(str(version)) == version


@given(major=COMPONENT, minor=COMPONENT, patch=COMPONENT)
def test_bumps_increment_one_level_and_reset_lower_levels(
    major: int,
    minor: int,
    patch: int,
) -> None:
    """Semantic-version bump arithmetic preserves the levels above it."""
    version = Version(major, minor, patch)
    assert version.bumped(MAJOR) == Version(major + 1, 0, 0)
    assert version.bumped(MINOR) == Version(major, minor + 1, 0)
    assert version.bumped(PATCH) == Version(major, minor, patch + 1)
