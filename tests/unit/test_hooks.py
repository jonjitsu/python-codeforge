from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

import pytest

from python_codeforge._invoke import Exit
from python_codeforge.collections import hooks
from python_codeforge.recording import RecordingContext

if TYPE_CHECKING:
    from pathlib import Path


def test_hook_is_generic_and_runs_the_gate() -> None:
    script = hooks.hook_script()
    assert script.startswith("#!/usr/bin/env sh\n")
    assert hooks.MARKER in script
    assert "uv run invoke check" in script
    assert "PYTHON_CODEFORGE_SKIP_HOOK" in script


def test_install_plan_protects_foreign_hooks() -> None:
    hooks.plan_install(None, force=False)
    hooks.plan_install(hooks.hook_script(), force=False)
    with pytest.raises(Exit, match="not written by python-codeforge"):
        hooks.plan_install("#!/bin/sh\necho foreign\n", force=False)
    hooks.plan_install("#!/bin/sh\necho foreign\n", force=True)


def test_write_hook_creates_an_executable(tmp_path: Path) -> None:
    path = tmp_path / "hooks" / "pre-commit"
    hooks.write_hook(path, hooks.hook_script())
    assert hooks.is_managed(path.read_text(encoding="utf-8"))
    assert stat.S_IMODE(path.stat().st_mode) == hooks.HOOK_MODE
    assert os.access(path, os.X_OK)


def test_install_and_uninstall_are_safe_and_idempotent(tmp_path: Path) -> None:
    context = RecordingContext({"rev-parse": str(tmp_path)})
    hooks.install(context)
    hooks.install(context)
    assert hooks.is_managed((tmp_path / "pre-commit").read_text(encoding="utf-8"))
    hooks.uninstall(context)
    hooks.uninstall(context)
    assert not (tmp_path / "pre-commit").exists()


def test_hooks_dir_fails_outside_git() -> None:
    with pytest.raises(Exit, match="not a git repository"):
        hooks.hooks_dir(RecordingContext())


def test_uninstall_never_removes_a_foreign_hook(tmp_path: Path) -> None:
    path = tmp_path / "pre-commit"
    path.write_text("#!/bin/sh\necho foreign\n", encoding="utf-8")
    context = RecordingContext({"rev-parse": str(tmp_path)})
    with pytest.raises(Exit, match="leaving it alone"):
        hooks.uninstall(context)
    assert path.exists()
