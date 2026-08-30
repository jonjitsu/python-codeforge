"""Typed project configuration loaded from ``pyproject.toml``.

Raw TOML values stop at this boundary. The rest of the package receives a
frozen :class:`Settings` value rather than reaching into nested untyped
dictionaries. A conventional single-package project needs no dedicated table:
its normalized ``[project].name`` supplies the package, while ``src``, ``tests``,
and conservative quality thresholds supply the remaining defaults.

Multi-package projects can name packages explicitly or use the keys in the
per-package coverage table. This keeps test scoping and coverage measurement on
one source of truth.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

PYPROJECT: Final = "pyproject.toml"
TOOL_TABLE: Final = "python-codeforge"
DEFAULT_ARTEFACTS: Final = (
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    "htmlcov",
    ".coverage",
    ".coverage.json",
    ".audit-requirements.txt",
)


@dataclass(frozen=True, slots=True)
class Settings:
    """All project-specific values consumed by the reusable tasks."""

    packages: tuple[str, ...]
    source_dir: str
    tests_dir: str
    targets: tuple[str, ...]
    sync_groups: str
    sync_extras: tuple[str, ...]
    artefacts: tuple[str, ...]
    crap_limit: float
    max_complexity: int
    mi_floor: float
    cognitive_limit: int
    coverage_floors: Mapping[str, float]

    def suite(self, package: str) -> str:
        """Return the package's test-suite path."""
        return f"{self.tests_dir}/{package}"

    def source_prefix(self, package: str) -> str:
        """Return the normalized coverage.py prefix for a package."""
        return f"{self.source_dir}/{package}/"


def load(root: Path) -> Settings:
    """Load settings, applying conventional defaults where values are absent."""
    with (root / PYPROJECT).open("rb") as handle:
        document = tomllib.load(handle)
    tool = _mapping(document.get("tool", {})).get(TOOL_TABLE, {})
    table = _mapping(tool)
    quality = _mapping(table.get("quality", {}))
    coverage = {
        str(name): _float(floor, default=100.0)
        for name, floor in _mapping(quality.get("coverage", {})).items()
    }
    packages = _packages(document, table, coverage)
    floors = coverage or dict.fromkeys(packages, 100.0)
    return Settings(
        packages=packages,
        source_dir=str(table.get("source_dir", "src")),
        tests_dir=str(table.get("tests_dir", "tests")),
        targets=_strings(table.get("targets", ("src", "tests", "tasks.py"))),
        sync_groups=str(table.get("sync_groups", "--all-groups")),
        sync_extras=_strings(table.get("sync_extras", ())),
        artefacts=_strings(table.get("artefacts", DEFAULT_ARTEFACTS)),
        crap_limit=_float(quality.get("crap_limit"), default=10.0),
        max_complexity=_int(quality.get("max_complexity"), default=10),
        mi_floor=_float(quality.get("mi_floor"), default=40.0),
        cognitive_limit=_int(quality.get("cognitive_limit"), default=9),
        coverage_floors=floors,
    )


def _packages(
    document: Mapping[str, object],
    table: Mapping[str, object],
    coverage: Mapping[str, float],
) -> tuple[str, ...]:
    configured = _strings(table.get("packages", ()))
    if configured:
        return configured
    if coverage:
        return tuple(coverage)
    project = _mapping(document.get("project", {}))
    name = str(project.get("name", "")).replace("-", "_")
    if name:
        return (name,)
    msg = "cannot infer a package name; set [project].name or [tool.python-codeforge].packages"
    raise ValueError(msg)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        return {}
    return cast("Mapping[str, object]", value)


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        msg = f"expected a list of strings, got {value!r}"
        raise TypeError(msg)
    result: list[str] = []
    for item in cast("list[object] | tuple[object, ...]", value):
        if not isinstance(item, str):
            msg = f"expected a list of strings, got {value!r}"
            raise TypeError(msg)
        result.append(item)
    return tuple(result)


def _float(value: object, *, default: float) -> float:
    selected = default if value is None else value
    if not isinstance(selected, str | int | float):
        msg = f"expected a number, got {selected!r}"
        raise TypeError(msg)
    return float(selected)


def _int(value: object, *, default: int) -> int:
    selected = default if value is None else value
    if not isinstance(selected, str | int):
        msg = f"expected an integer, got {selected!r}"
        raise TypeError(msg)
    return int(selected)
