from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_codeforge import cognitive, coverage, crap, maintainability

if TYPE_CHECKING:
    from tests.unit.conftest import Project

    from python_codeforge.coverage import FileEntry

BRANCHY = '''"""A branchy module."""


def branchy(n: int) -> str:
    if n > 3:
        return "a"
    if n > 2:
        return "b"
    if n > 1:
        return "c"
    return "d"
'''

NESTED = '''"""A nested module."""


def nested(n: int) -> str:
    if n > 1:
        if n > 2:
            if n > 3:
                return "a"
            return "b"
        return "c"
    return "d"
'''


def _entry(*, covered: int, statements: int) -> FileEntry:
    return {
        "executed_lines": list(range(1, covered + 1)),
        "missing_lines": list(range(covered + 1, statements + 1)),
        "summary": {"covered_lines": covered, "num_statements": statements},
    }


def test_coverage_load_explains_a_missing_report(project: Project) -> None:
    with pytest.raises(FileNotFoundError, match=r"run `invoke test\.run` first"):
        coverage.load(project.root)


def test_coverage_measure_uses_configured_source_prefix() -> None:
    files: dict[str, FileEntry] = {
        "lib/pkg/a.py": {
            "executed_lines": [],
            "missing_lines": [],
            "summary": {
                "covered_lines": 8,
                "num_statements": 10,
                "covered_branches": 2,
                "num_branches": 4,
            },
        },
        "src/pkg/ignored.py": _entry(covered=100, statements=100),
    }
    measured = coverage.measure("pkg", "lib/pkg/", 90.0, files)
    assert (measured.covered, measured.total) == (10, 14)
    assert not measured.passed


def test_coverage_empty_package_is_full() -> None:
    assert coverage.measure("pkg", "lib/pkg/", 100.0, {}).percent == 100.0


def test_coverage_report_passes_and_fails(project: Project) -> None:
    project.coverage({"lib/pkg/a.py": _entry(covered=5, statements=5)})
    assert coverage.report(project.root).ok
    project.coverage({"lib/pkg/a.py": _entry(covered=1, statements=4)})
    report = coverage.report(project.root)
    assert not report.ok
    assert report.failures == ("  pkg -> 25.00% (floor 100.00%)",)


def test_line_index_normalizes_windows_paths() -> None:
    files: dict[str, FileEntry] = {"lib\\pkg\\a.py": _entry(covered=2, statements=3)}
    assert coverage.line_index(files) == {"lib/pkg/a.py": ({1, 2}, {3})}


def test_crap_formula_rewards_coverage() -> None:
    assert crap.score(4, 1.0) == 4.0
    assert crap.score(4, 0.0) == 20.0
    assert crap.score(4, 0.5) == pytest.approx(6.0)


def test_crap_discovers_blocks_in_configured_source(project: Project) -> None:
    project.module("pkg/a.py", BRANCHY)
    assert {block.name: block.complexity for block in crap.blocks(project.root)} == {"branchy": 4}


def test_crap_coverage_uses_only_measured_lines() -> None:
    block = crap.Block("lib/pkg/a.py", "f", 1, 4, 1)
    assert crap.coverage_of(block, {}) == 1.0
    assert crap.coverage_of(block, {"lib/pkg/a.py": ({1, 2}, {3, 4})}) == 0.5


def test_crap_report_fails_an_uncovered_branchy_function(project: Project) -> None:
    path = project.module("pkg/a.py", BRANCHY)
    project.coverage(
        {path: {"executed_lines": [], "missing_lines": list(range(1, 20)), "summary": {}}}
    )
    report = crap.report(project.root)
    assert not report.ok
    assert "CRAP 20.00" in report.failures[0]


def test_cognitive_distinguishes_nesting(project: Project) -> None:
    project.module("pkg/branchy.py", BRANCHY)
    project.module("pkg/nested.py", NESTED)
    found = {item.name: item.complexity for item in cognitive.scores(project.root, 10)}
    assert found["nested"] > found["branchy"]


def test_cognitive_report_enforces_configured_limit(project: Project) -> None:
    project.configure(cognitive_limit=1)
    project.module("pkg/nested.py", NESTED)
    report = cognitive.report(project.root)
    assert not report.ok
    assert "lib/pkg/nested.py" in report.failures[0]


def test_empty_metric_trees_pass(project: Project) -> None:
    (project.root / "lib").mkdir()
    project.coverage({})
    assert crap.report(project.root).ok
    assert cognitive.report(project.root).ok
    assert maintainability.report(project.root).ok


def test_maintainability_enforces_floor(project: Project) -> None:
    project.configure(mi_floor=101.0)
    project.module("pkg/a.py", '"""Doc."""\n\n\ndef f() -> int:\n    return 1\n')
    report = maintainability.report(project.root)
    assert not report.ok
    assert "lib/pkg/a.py" in report.failures[0]
