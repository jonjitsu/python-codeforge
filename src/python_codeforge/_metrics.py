# Radon and complexipy ship no type information. Keep their APIs behind this facade.
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false
"""Typed facades over the untyped metric libraries."""

from __future__ import annotations

from dataclasses import dataclass

from complexipy import code_complexity
from radon.complexity import cc_visit
from radon.metrics import mi_rank, mi_visit
from radon.visitors import Class


@dataclass(frozen=True, slots=True)
class CodeBlock:
    """One measurable function or method."""

    name: str
    lineno: int
    endline: int
    complexity: int


def cyclomatic_blocks(source: str) -> tuple[CodeBlock, ...]:
    """Return cyclomatic complexity for every function and method."""
    return tuple(
        CodeBlock(
            name=str(block.fullname),
            lineno=int(block.lineno),
            endline=int(block.endline),
            complexity=int(block.complexity),
        )
        for block in cc_visit(source)
        if not isinstance(block, Class)
    )


def cognitive_blocks(source: str) -> tuple[CodeBlock, ...]:
    """Return cognitive complexity for every function and method."""
    return tuple(
        CodeBlock(
            name=str(function.name),
            lineno=int(function.line_start),
            endline=int(function.line_end),
            complexity=int(function.complexity),
        )
        for function in code_complexity(source).functions
    )


def maintainability_index(source: str) -> float:
    """Return Radon's 0-100 maintainability index."""
    return float(mi_visit(source, multi=True))


def maintainability_rank(index: float) -> str:
    """Return Radon's A, B, or C rank for an index."""
    return str(mi_rank(index))
