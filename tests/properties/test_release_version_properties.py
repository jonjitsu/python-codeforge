"""Semantic-version invariants for reusable release automation."""

from hypothesis import given
from hypothesis import strategies as st

from python_codeforge.release import MAJOR, MINOR, PATCH, Version, project

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


@given(
    tool_major=COMPONENT,
    tool_minor=COMPONENT,
    tool_patch=COMPONENT,
    project_major=COMPONENT,
    project_minor=COMPONENT,
    project_patch=COMPONENT,
)
def test_version_rewrite_is_scoped_to_the_project_table(
    tool_major: int,
    tool_minor: int,
    tool_patch: int,
    project_major: int,
    project_minor: int,
    project_patch: int,
) -> None:
    """Versions in tables before and after ``[project]`` are invariant."""
    tool_version = Version(tool_major, tool_minor, tool_patch)
    project_version = Version(project_major, project_minor, project_patch)
    replacement = project_version.bumped(PATCH)
    source = (
        f'[tool.before]\nversion = "{tool_version}"\n\n'
        f'[project]\nversion = "{project_version}"\n\n'
        f'[tool.after]\nversion = "{tool_version}"\n'
    )

    rewritten = project.with_version(source, replacement)

    assert rewritten.count(f'version = "{tool_version}"') == 2
    assert project.current_version(rewritten) == replacement
