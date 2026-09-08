"""Changelog promotion invariants for reusable release automation."""

from hypothesis import given
from hypothesis import strategies as st

from python_codeforge.release import Version, changelog

NOTE = st.lists(
    st.sampled_from(["Added checks.", "Fixed a failure.", "Improved release safety."]),
    min_size=1,
    max_size=5,
).map(lambda entries: "\n".join(f"- {entry}" for entry in entries))


@given(note=NOTE)
def test_promotion_preserves_unreleased_prose_as_release_notes(note: str) -> None:
    """Promotion changes headings while leaving authored prose untouched."""
    source = f"# Changelog\n\n## Unreleased\n\n{note}\n\n## 1.0.0\n\nBaseline.\n"
    version = Version.parse("1.0.1")
    promoted = changelog.promote(source, version)
    assert changelog.section(promoted, version) == note
    assert promoted.count(changelog.UNRELEASED) == 1
    assert changelog.section(promoted, Version.parse("1.0.0")) == "Baseline."
