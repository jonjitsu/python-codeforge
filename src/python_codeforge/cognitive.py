"""Per-function cognitive-complexity gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from python_codeforge._metrics import cognitive_blocks
from python_codeforge.config import load as load_settings
from python_codeforge.gate import Report

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

WORST: Final = 5


@dataclass(frozen=True, slots=True)
class Scored:
    """A cognitive-complexity score with its source location."""

    path: str
    name: str
    lineno: int
    complexity: int
    limit: int

    @property
    def passed(self) -> bool:
        """Whether the configured limit is met."""
        return self.complexity <= self.limit

    def render(self) -> str:
        """Render an editor-clickable report line."""
        return f"  {self.complexity:3d}  {self.path}:{self.lineno} {self.name}"


def scores(root: Path, limit: int) -> Iterator[Scored]:
    """Score every function under the configured source directory."""
    source = root / load_settings(root).source_dir
    for file in sorted(source.rglob("*.py")):
        path = file.relative_to(root).as_posix()
        for block in cognitive_blocks(file.read_text(encoding="utf-8")):
            yield Scored(path, block.name, block.lineno, block.complexity, limit)


def report(root: Path) -> Report:
    """Score every function and fail values above the configured limit."""
    limit = load_settings(root).cognitive_limit
    found = sorted(scores(root, limit), key=lambda item: item.complexity, reverse=True)
    if not found:
        return Report(lines=("cognitive: no functions found in source directory",))
    lines = (
        f"cognitive: {len(found)} functions scored (limit {limit})",
        *(item.render() for item in found[:WORST]),
    )
    failures = tuple(
        f"  {item.path}:{item.lineno} {item.name} -> cognitive {item.complexity} (limit {limit})"
        for item in found
        if not item.passed
    )
    return Report(lines, failures)
