from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from python_codeforge import hygiene

lines = st.text(alphabet=st.characters(blacklist_characters="\n"), max_size=40)


@given(body=st.lists(lines, max_size=10))
def test_rstripped_lines_never_have_trailing_whitespace(body: list[str]) -> None:
    text = "\n".join(line.rstrip() for line in body) + "\n"
    assert hygiene.find_trailing_whitespace(text) == []


@given(body=st.lists(lines, max_size=10))
def test_one_trailing_newline_satisfies_the_rule(body: list[str]) -> None:
    assert hygiene.has_final_newline("\n".join(body).rstrip("\n") + "\n")


@given(text=st.text(max_size=200))
def test_checks_never_raise_for_arbitrary_text(text: str) -> None:
    hygiene.find_conflict_markers(text)
    hygiene.find_private_keys(text)
    hygiene.find_trailing_whitespace(text)
    hygiene.has_final_newline(text)
    list(hygiene.check_text("f.txt", text))
