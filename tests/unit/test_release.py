"""Example-based tests for reusable release preparation."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from python_codeforge import release
from python_codeforge.release import changelog, commits, project

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
        changelog.promote(EMPTY, release.Version.parse("1.0.1"))


def test_missing_release_section_is_rejected() -> None:
    """Release notes must fail loudly when the requested version is absent."""
    with pytest.raises(ValueError, match=re.escape("no '## 9.9.9' heading")):
        changelog.section(NOTES, release.Version.parse("9.9.9"))


def test_changelog_heading_lookups_ignore_prose_mentions() -> None:
    """A heading name embedded in prose cannot capture unrelated content."""
    source = "# Changelog\n\nSee ## Unreleased for policy.\n\n## Unreleased\n\n- Real note.\n"
    promoted = changelog.promote(source, release.Version.parse("1.0.1"))
    assert changelog.section(promoted, release.Version.parse("1.0.1")) == "- Real note."


def test_changelog_heading_lookups_ignore_fenced_code() -> None:
    """Examples in fenced code cannot become release sections."""
    source = (
        "# Changelog\n\n```markdown\n## Unreleased\n\n- Example.\n```\n\n"
        "## Unreleased\n\n- Real note.\n"
    )
    promoted = changelog.promote(source, release.Version.parse("1.0.1"))
    assert changelog.section(promoted, release.Version.parse("1.0.1")) == "- Real note."


def test_invalid_versions_and_bump_levels_are_rejected() -> None:
    """Malformed release metadata must fail before touching project files."""
    with pytest.raises(ValueError, match="not a version"):
        release.Version.parse("1.2")
    with pytest.raises(ValueError, match="not a bump level"):
        release.Version.parse("1.2.3").bumped("other")


def test_only_project_version_line_is_rewritten() -> None:
    """Tool configuration containing 'version' must remain untouched."""
    source = '[project]\nversion = "1.2.3"\n\n[tool.uv]\nrequired-version = ">=0.11"\n'
    rewritten = project.with_version(source, release.Version.parse("2.0.0"))
    assert 'version = "2.0.0"' in rewritten
    assert 'required-version = ">=0.11"' in rewritten


def test_project_version_is_rewritten_when_tool_version_comes_first() -> None:
    """A tool-owned version above ``[project]`` must remain untouched."""
    source = (
        '[tool.commitizen]\nversion = "9.8.7"\n\n[project]\nname = "consumer"\nversion = "1.2.3"\n'
    )

    rewritten = project.with_version(source, release.Version.parse("2.0.0"))

    assert '[tool.commitizen]\nversion = "9.8.7"' in rewritten
    assert '[project]\nname = "consumer"\nversion = "2.0.0"' in rewritten


def test_missing_project_version_line_is_rejected() -> None:
    """Unexpected pyproject structure must not produce a partial release."""
    with pytest.raises(ValueError, match="no project version line"):
        project.with_version('[project]\nname = "consumer"\n', release.Version.parse("1.0.0"))


def test_breaking_trailer_requests_major_bump() -> None:
    """A body trailer is as significant as a bang in the subject."""
    message = "feat: rename everything\n\nBREAKING CHANGE: the old name is gone."
    assert commits.bump_level([message]) == release.MAJOR


def test_near_miss_feature_prefix_is_reported_and_counts_as_patch() -> None:
    """A typo must not silently create a minor release."""
    message = "feature: add a flag"
    assert commits.bump_level([message]) == release.PATCH
    assert commits.unconventional([message]) == [message]


def test_generated_release_commit_is_recognised() -> None:
    """The pipeline must not report its own commit as unconventional."""
    assert commits.unconventional(["release: 1.0.1"]) == []


def test_repository_history_has_a_release_baseline() -> None:
    """Release inference reads history relative to an explicit repository root."""
    root = Path(__file__).parents[2]
    latest = commits.latest_tag(root)
    assert commits.since(root, latest) or latest


def test_prepare_writes_a_complete_release_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preparation promotes notes and changes only the declared project version."""
    pyproject = '[project]\nname = "consumer"\nversion = "1.2.3"\n'
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(NOTES, encoding="utf-8")

    def latest_tag(root: Path) -> str:
        assert root == tmp_path
        return "1.2.3"

    def since(root: Path, ref: str | None) -> list[str]:
        assert root == tmp_path
        assert ref == "1.2.3"
        return ["feat: reusable releases", "oops"]

    monkeypatch.setattr(commits, "latest_tag", latest_tag)
    monkeypatch.setattr(commits, "since", since)

    prepared = release.prepare(tmp_path)

    assert prepared == release.PreparedRelease(
        version=release.Version.parse("1.3.0"),
        level=release.MINOR,
        unconventional=("oops",),
    )
    assert release.version(tmp_path) == release.Version.parse("1.3.0")
    assert release.notes(tmp_path) == "- Something worth shipping."


def test_prepare_leaves_empty_unreleased_tree_untouched(tmp_path: Path) -> None:
    """No release proposal is created when no notes are waiting."""
    pyproject = '[project]\nname = "consumer"\nversion = "1.2.3"\n'
    (tmp_path / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(EMPTY, encoding="utf-8")

    assert release.prepare(tmp_path) is None
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == pyproject
