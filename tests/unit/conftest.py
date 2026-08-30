"""Fixtures for task and gate unit tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from python_codeforge.recording import RecordingContext

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@pytest.fixture
def ctx() -> RecordingContext:
    """Return a command-recording Invoke context."""
    return RecordingContext()


@dataclass(frozen=True, slots=True)
class Project:
    """A small configured consumer project."""

    root: Path

    def configure(
        self,
        *,
        crap_limit: float = 10.0,
        mi_floor: float = 40.0,
        cognitive_limit: int = 10,
    ) -> None:
        """Write task configuration."""
        (self.root / "pyproject.toml").write_text(
            '[project]\nname = "consumer"\nversion = "0.1.0"\n'
            '\n[tool.python-codeforge]\npackages = ["pkg"]\n'
            'source_dir = "lib"\ntests_dir = "spec"\n'
            'targets = ["lib", "spec", "tasks.py"]\n'
            'sync_extras = ["postgres"]\n'
            "\n[tool.python-codeforge.quality]\n"
            f"crap_limit = {crap_limit}\nmax_complexity = 10\n"
            f"mi_floor = {mi_floor}\ncognitive_limit = {cognitive_limit}\n"
            "\n[tool.python-codeforge.quality.coverage]\npkg = 100.0\n",
            encoding="utf-8",
        )

    def module(self, relative: str, source: str) -> str:
        """Write a source module and return its relative path."""
        path = self.root / "lib" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return f"lib/{relative}"

    def coverage(self, files: Mapping[str, object]) -> None:
        """Write coverage.py JSON."""
        payload = json.dumps({"files": files})
        (self.root / ".coverage.json").write_text(payload, encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path) -> Project:
    """Return a configured temporary consumer."""
    built = Project(tmp_path)
    built.configure()
    return built
