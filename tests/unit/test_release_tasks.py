"""Tests for the reusable release Invoke entry points."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_codeforge import ns
from python_codeforge import release as release_domain
from python_codeforge._invoke import Exit
from python_codeforge.collections import release as release_tasks
from python_codeforge.recording import RecordingContext
from python_codeforge.release import MINOR, PreparedRelease, Version
from python_codeforge.release import workflows as release_workflows

if TYPE_CHECKING:
    from pathlib import Path


def test_release_tasks_are_mounted_as_a_collection() -> None:
    """Release commands follow the same collection convention as other tasks."""
    names = set(ns.task_names)
    assert {"release.install", "release.notes", "release.prepare", "release.version"} <= names
    assert not any(name.startswith("release-") for name in names)


def test_prepare_task_locks_and_reports_the_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The task wraps domain preparation with lock refresh and useful output."""
    monkeypatch.chdir(tmp_path)
    prepared = PreparedRelease(Version.parse("1.2.0"), MINOR, ("untyped subject",))

    def prepare(root: Path) -> PreparedRelease:
        assert root == tmp_path
        return prepared

    monkeypatch.setattr(release_domain, "prepare", prepare)
    context = RecordingContext()

    release_tasks.prepare(context)

    assert context.commands == ["uv lock"]
    assert capsys.readouterr().out == (
        "note: untyped commit counted as a patch: untyped subject\nprepared 1.2.0 (minor)\n"
    )


def test_prepare_task_skips_an_empty_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty changelog does not refresh the lockfile."""
    monkeypatch.chdir(tmp_path)

    def prepare(root: Path) -> None:
        assert root == tmp_path

    monkeypatch.setattr(release_domain, "prepare", prepare)
    context = RecordingContext()

    release_tasks.prepare(context)

    assert context.commands == []
    assert "no release to prepare" in capsys.readouterr().out


def test_read_tasks_print_domain_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Version and note tasks expose values for workflow shell steps."""
    monkeypatch.chdir(tmp_path)

    def version(root: Path) -> Version:
        assert root == tmp_path
        return Version.parse("2.3.4")

    def notes(root: Path) -> str:
        assert root == tmp_path
        return "Release notes"

    monkeypatch.setattr(release_domain, "version", version)
    monkeypatch.setattr(release_domain, "notes", notes)
    context = RecordingContext()

    release_tasks.version(context)
    release_tasks.notes(context)

    assert capsys.readouterr().out == "2.3.4\nRelease notes\n"


@pytest.mark.parametrize("name", ["notes", "prepare", "version"])
def test_read_tasks_translate_invalid_release_metadata_to_invoke_exit(
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every workflow step reports an invalid project without a traceback."""
    monkeypatch.chdir(tmp_path)

    def refuse(root: Path) -> object:
        assert root == tmp_path
        message = "CHANGELOG.md has no release heading"
        raise ValueError(message)

    monkeypatch.setattr(release_domain, name, refuse)
    with pytest.raises(Exit, match=r"CHANGELOG\.md has no release heading"):
        getattr(release_tasks, name)(RecordingContext())


def test_install_task_reports_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The installer task forwards force and prints its result."""
    monkeypatch.chdir(tmp_path)

    def install(root: Path, *, force: bool) -> release_workflows.WorkflowInstallReport:
        assert root == tmp_path
        assert force
        return release_workflows.WorkflowInstallReport(copied=3, unchanged=1)

    monkeypatch.setattr(release_workflows, "install", install)
    release_tasks.install(RecordingContext(), force=True)
    assert capsys.readouterr().out == "release workflows: 3 copied, 1 unchanged\n"


def test_install_task_translates_conflicts_to_invoke_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI users receive a concise nonzero failure for unsafe replacement."""
    monkeypatch.chdir(tmp_path)

    def conflict(root: Path, *, force: bool) -> release_workflows.WorkflowInstallReport:
        assert root == tmp_path
        assert not force
        message = "managed workflow differs"
        raise release_workflows.WorkflowConflictError(message)

    monkeypatch.setattr(release_workflows, "install", conflict)
    with pytest.raises(Exit, match="managed workflow differs"):
        release_tasks.install(RecordingContext())
