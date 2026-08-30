"""Per-module maintainability-index gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from python_codeforge._metrics import maintainability_index, maintainability_rank
from python_codeforge.config import load as load_settings
from python_codeforge.gate import Report

if TYPE_CHECKING:
    from pathlib import Path

WORST: Final = 5


@dataclass(frozen=True, slots=True)
class Module:
    """Maintainability score for one module."""

    path: str
    mi: float
    floor: float

    @property
    def rank(self) -> str:
        """Return Radon's A, B, or C rank."""
        return maintainability_rank(self.mi)

    @property
    def passed(self) -> bool:
        """Whether the configured floor is met."""
        return self.mi + 1e-9 >= self.floor


def report(root: Path) -> Report:
    """Score every configured source module."""
    settings = load_settings(root)
    modules = sorted(
        (
            Module(
                file.relative_to(root).as_posix(),
                maintainability_index(file.read_text(encoding="utf-8")),
                settings.mi_floor,
            )
            for file in (root / settings.source_dir).rglob("*.py")
        ),
        key=lambda module: module.mi,
    )
    if not modules:
        return Report(lines=("mi: no modules found in source directory",))
    lines = (
        f"mi: {len(modules)} modules scored (floor {settings.mi_floor:.2f})",
        *(f"  {module.mi:6.2f}  {module.rank}  {module.path}" for module in modules[:WORST]),
    )
    failures = tuple(
        f"  {module.path} -> MI {module.mi:.2f} ({module.rank})"
        for module in modules
        if not module.passed
    )
    return Report(lines, failures)
