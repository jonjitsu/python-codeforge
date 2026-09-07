"""Named Conventional Commit regressions and repository history checks."""

from ci import commits
from ci.version import MAJOR, PATCH


def test_breaking_trailer_requests_major_bump() -> None:
    """A body trailer is as significant as a bang in the subject."""
    message = "feat: rename everything\n\nBREAKING CHANGE: the old name is gone."
    assert commits.bump_level([message]) == MAJOR


def test_near_miss_feature_prefix_is_reported_and_counts_as_patch() -> None:
    """A typo must not silently create a minor release."""
    message = "feature: add a flag"
    assert commits.bump_level([message]) == PATCH
    assert commits.unconventional([message]) == [message]


def test_generated_release_commit_is_recognised() -> None:
    """The pipeline must not report its own commit as unconventional."""
    assert commits.unconventional(["release: 1.0.1"]) == []


def test_repository_history_has_a_release_baseline() -> None:
    """Release inference needs either a tag or readable commit history."""
    latest = commits.latest_tag()
    assert commits.since(latest) or latest
