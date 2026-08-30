"""Shared reports and emission for in-process quality gates."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from python_codeforge._invoke import Exit


@dataclass(frozen=True, slots=True)
class Report:
    """Human-readable summary lines and build-failing findings."""

    lines: tuple[str, ...]
    failures: tuple[str, ...] = field(default=())

    @property
    def ok(self) -> bool:
        """Whether the gate passed."""
        return not self.failures


def emit(report: Report) -> None:
    """Print a report and abort the task when it has findings."""
    for line in report.lines:
        print(line)
    if report.ok:
        return
    for line in report.failures:
        print(line, file=sys.stderr)
    msg = f"{len(report.failures)} finding(s) over the limit"
    raise Exit(msg, code=1)
