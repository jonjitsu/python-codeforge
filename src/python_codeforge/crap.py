"""Coverage-weighted cyclomatic complexity (CRAP) gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from python_codeforge._metrics import cyclomatic_blocks
from python_codeforge.config import load as load_settings
from python_codeforge.coverage import line_index, load
from python_codeforge.gate import Report

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from python_codeforge.coverage import LineIndex

WORST: Final = 5


@dataclass(frozen=True, slots=True)
class Block:
    """One function or method with a source span and complexity."""

    path: str
    name: str
    lineno: int
    endline: int
    complexity: int


@dataclass(frozen=True, slots=True)
class Score:
    """CRAP score and coverage for one block."""

    block: Block
    coverage: float
    crap: float


def blocks(root: Path) -> Iterator[Block]:
    """Yield measurable blocks under the configured source directory."""
    source = root / load_settings(root).source_dir
    for file in sorted(source.rglob("*.py")):
        relative = file.relative_to(root).as_posix()
        for block in cyclomatic_blocks(file.read_text(encoding="utf-8")):
            yield Block(relative, block.name, block.lineno, block.endline, block.complexity)


def coverage_of(block: Block, index: LineIndex) -> float:
    """Return the executed fraction of measured lines in a block's span."""
    executed, missing = index.get(block.path, (set(), set()))
    span = range(block.lineno, block.endline + 1)
    hit = sum(line in executed for line in span)
    miss = sum(line in missing for line in span)
    return 1.0 if hit + miss == 0 else hit / (hit + miss)


def score(complexity: int, coverage: float) -> float:
    """Calculate CRAP = cc^2 * (1 - coverage)^3 + cc."""
    return complexity**2 * (1.0 - coverage) ** 3 + complexity


def report(root: Path) -> Report:
    """Score every block and fail values over configured limits."""
    settings = load_settings(root)
    index = line_index(load(root))
    scores = [
        Score(block, measured, score(block.complexity, measured))
        for block in blocks(root)
        for measured in (coverage_of(block, index),)
    ]
    if not scores:
        return Report(lines=("crap: no measurable blocks found in source directory",))
    header = (
        f"crap: {len(scores)} blocks scored (limit {settings.crap_limit},"
        f" max cc {settings.max_complexity})"
    )
    lines = (
        header,
        *(
            _render(item)
            for item in sorted(scores, key=lambda item: item.crap, reverse=True)[:WORST]
        ),
    )
    failures = tuple(
        _render_failure(item)
        for item in scores
        if item.crap > settings.crap_limit or item.block.complexity > settings.max_complexity
    )
    return Report(lines, failures)


def _render(item: Score) -> str:
    block = item.block
    return (
        f"  {item.crap:7.2f}  cc={block.complexity:<3d} cov={item.coverage:6.1%}  "
        f"{block.path}:{block.lineno} {block.name}"
    )


def _render_failure(item: Score) -> str:
    block = item.block
    return (
        f"  {block.path}:{block.lineno} {block.name} -> CRAP {item.crap:.2f} "
        f"(cc={block.complexity}, cov={item.coverage:.1%})"
    )
