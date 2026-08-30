# hygiene: allow-file private-key -- tests contain representative headers.
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_codeforge import hygiene
from python_codeforge._invoke import Exit
from python_codeforge.collections import quality
from python_codeforge.hygiene import Finding
from python_codeforge.recording import RecordingContext

if TYPE_CHECKING:
    from pathlib import Path


def test_finding_renders_with_optional_line() -> None:
    assert Finding("a.py", "rule", "detail", 7).render() == "a.py:7: rule detail"
    assert Finding("a.py", "rule", "detail").render() == "a.py: rule detail"


def test_text_checks_find_each_problem() -> None:
    text = "<<<<<<< HEAD\n-----BEGIN RSA PRIVATE KEY-----\nbad \nno newline"
    findings = list(hygiene.check_text("f.txt", text))
    assert [finding.rule for finding in findings] == [
        "merge-conflict",
        "private-key",
        "trailing-whitespace",
        "final-newline",
    ]
    assert hygiene.find_conflict_markers("Title\n=======\n") == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [("", True), ("a\n", True), ("a", False), ("a\n\n", False)],
)
def test_final_newline(text: str, expected: bool) -> None:
    assert hygiene.has_final_newline(text) is expected


def test_toml_and_yaml_parse_errors_are_reported(tmp_path: Path) -> None:
    assert hygiene.parse_error(tmp_path / "bad.toml", "value = [") is not None
    assert hygiene.parse_error(tmp_path / "good.toml", "value = []") is None
    assert hygiene.parse_error(tmp_path / "bad.yaml", "value: [") is not None
    assert hygiene.parse_error(tmp_path / "notes.md", "value = [") is None


def test_allowances_are_narrow_and_named() -> None:
    text = (
        "# hygiene: allow-file trailing-whitespace\n"
        "-----BEGIN PRIVATE KEY-----  # hygiene: allow private-key\n"
        "bad \n"
    )
    assert list(hygiene.check_text("f.txt", text)) == []
    assert hygiene.file_allowances("# hygiene: allow-file\n") == set()
    assert not hygiene.line_allows("# hygiene: allow", "private-key")


def test_binary_is_size_checked_but_not_decoded(tmp_path: Path) -> None:
    path = tmp_path / "blob.bin"
    path.write_bytes(b"\xff" * (hygiene.MAX_FILE_BYTES + 1))
    assert [finding.rule for finding in hygiene.check_file(path, tmp_path)] == ["large-file"]


def test_notebooks_are_not_blocked_by_generic_package(tmp_path: Path) -> None:
    path = tmp_path / "notebooks" / "research.py"
    path.parent.mkdir()
    path.write_text("value = 1\n", encoding="utf-8")
    assert list(hygiene.check_file(path, tmp_path)) == []


def test_check_files_skips_directories(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "bad.py").write_text("x = 1 \n", encoding="utf-8")
    findings = hygiene.check_files(sorted(tmp_path.rglob("*")), tmp_path)
    assert [finding.rule for finding in findings] == ["trailing-whitespace"]


def test_hygiene_task_uses_git_tracked_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "bad.py").write_text("x = 1 \n", encoding="utf-8")
    context = RecordingContext({"show-toplevel": str(tmp_path), "ls-files": "bad.py"})
    with pytest.raises(Exit):
        quality.hygiene_(context)
    assert "trailing-whitespace" in capsys.readouterr().out


def test_hygiene_task_can_filter_names(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "bad.py").write_text("x = 1 \n", encoding="utf-8")
    (tmp_path / "good.py").write_text("x = 1\n", encoding="utf-8")
    context = RecordingContext({"show-toplevel": str(tmp_path), "ls-files": "bad.py\0good.py"})
    quality.hygiene_(context, name="good")
    assert "1 tracked files checked, 0 finding" in capsys.readouterr().out
