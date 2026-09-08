"""Commit-to-version mapping invariants for reusable releases."""

from hypothesis import given
from hypothesis import strategies as st

from python_codeforge.release import MAJOR, MINOR, PATCH, commits

PATCH_TYPE = st.sampled_from(sorted(commits.TYPES - {"feat"}))


@given(commit_type=PATCH_TYPE)
def test_recognised_non_feature_types_request_patch(commit_type: str) -> None:
    """Only a feature or breaking marker can exceed a patch bump."""
    assert commits.bump_level([f"{commit_type}: describe the change"]) == PATCH


@given(scope=st.from_regex(r"[a-z]{1,12}", fullmatch=True))
def test_feature_scope_does_not_change_minor_bump(scope: str) -> None:
    """Any valid scope preserves a feature's minor bump."""
    assert commits.bump_level([f"feat({scope}): add capability"]) == MINOR


@given(commit_type=st.sampled_from(sorted(commits.TYPES)))
def test_bang_on_recognised_type_requests_major(commit_type: str) -> None:
    """Every recognised type can declare a breaking change."""
    assert commits.bump_level([f"{commit_type}!: break compatibility"]) == MAJOR
