from __future__ import annotations

import pytest

from python_codeforge._invoke import Exit
from python_codeforge.gate import Report, emit


def test_report_ok_reflects_failures() -> None:
    assert Report(("good",)).ok
    assert not Report((), ("bad",)).ok


def test_emit_prints_passing_report(capsys: pytest.CaptureFixture[str]) -> None:
    emit(Report(("first", "second")))
    captured = capsys.readouterr()
    assert captured.out == "first\nsecond\n"
    assert captured.err == ""


def test_emit_prints_failures_and_aborts(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(Exit, match=r"2 finding\(s\) over the limit"):
        emit(Report(("summary",), ("bad a", "bad b")))
    captured = capsys.readouterr()
    assert captured.out == "summary\n"
    assert captured.err == "bad a\nbad b\n"
