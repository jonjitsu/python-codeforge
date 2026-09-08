"""Reusable Invoke tasks for strict, uv-managed Python projects."""

from __future__ import annotations

from python_codeforge import gates
from python_codeforge._invoke import build_namespace, task
from python_codeforge.collections import ai, env, hooks, quality, security, testing
from python_codeforge.collections import release as release_collection
from python_codeforge.commands import PytestRun, SemgrepConfig, Targets
from python_codeforge.config import Settings

ns = build_namespace(
    root=[gates.check, gates.ci],
    collections={
        "ai": ai,
        "env": env,
        "hooks": hooks,
        "quality": quality,
        "release": release_collection,
        "test": testing,
        "security": security,
    },
)

__all__ = [
    "PytestRun",
    "SemgrepConfig",
    "Settings",
    "Targets",
    "build_namespace",
    "ns",
    "task",
]
