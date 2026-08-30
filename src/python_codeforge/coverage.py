"""Per-package statement and branch coverage floors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, NotRequired, TypedDict, cast

from python_codeforge.config import load as load_settings
from python_codeforge.gate import Report

if TYPE_CHECKING:
    from pathlib import Path

COVERAGE_JSON: Final = ".coverage.json"


class FileSummary(TypedDict):
    """The totals coverage.py writes for one file."""

    covered_lines: int
    num_statements: int
    covered_branches: NotRequired[int]
    num_branches: NotRequired[int]


class FileEntry(TypedDict):
    """One file in coverage.py's JSON report."""

    executed_lines: list[int]
    missing_lines: list[int]
    summary: FileSummary


type Files = dict[str, FileEntry]
type LineIndex = dict[str, tuple[set[int], set[int]]]


@dataclass(frozen=True, slots=True)
class PackageCoverage:
    """Measured coverage for one configured package."""

    package: str
    covered: int
    total: int
    floor: float

    @property
    def percent(self) -> float:
        """Return combined statement and branch coverage."""
        return 100.0 if self.total == 0 else 100.0 * self.covered / self.total

    @property
    def passed(self) -> bool:
        """Whether the configured floor is met."""
        return self.percent + 1e-9 >= self.floor


def load(root: Path) -> Files:
    """Load coverage JSON or explain how to produce it."""
    path = root / COVERAGE_JSON
    if not path.exists():
        msg = f"{path} not found; run `invoke test.run` first."
        raise FileNotFoundError(msg)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return cast("Files", payload["files"])


def line_index(files: Files) -> LineIndex:
    """Map measured files to executed and missing line sets."""
    return {
        _posix(path): (set(entry["executed_lines"]), set(entry["missing_lines"]))
        for path, entry in files.items()
    }


def measure(package: str, prefix: str, floor: float, files: Files) -> PackageCoverage:
    """Total coverage.py counts below a package source prefix."""
    covered = total = 0
    for raw_path, entry in files.items():
        if not _posix(raw_path).startswith(prefix):
            continue
        summary = entry["summary"]
        covered += summary["covered_lines"] + summary.get("covered_branches", 0)
        total += summary["num_statements"] + summary.get("num_branches", 0)
    return PackageCoverage(package, covered, total, floor)


def report(root: Path) -> Report:
    """Check every configured package against its own floor."""
    files = load(root)
    settings = load_settings(root)
    results = [
        measure(package, settings.source_prefix(package), floor, files)
        for package, floor in settings.coverage_floors.items()
    ]
    width = max((len(result.package) for result in results), default=0)
    lines = tuple(
        f"coverage: {'ok  ' if result.passed else 'FAIL'} {result.package:<{width}}"
        f" {result.percent:6.2f}% (floor {result.floor:.2f}%, {result.covered}/{result.total})"
        for result in results
    )
    failures = tuple(
        f"  {result.package} -> {result.percent:.2f}% (floor {result.floor:.2f}%)"
        for result in results
        if not result.passed
    )
    return Report(lines, failures)


def _posix(path: str) -> str:
    return path.replace("\\", "/")
