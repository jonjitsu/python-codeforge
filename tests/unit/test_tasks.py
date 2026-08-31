from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import pytest
from invoke.runners import Result

from python_codeforge._invoke import Exit
from python_codeforge.collections import ai, env, quality, security, testing
from python_codeforge.recording import RecordingContext

if TYPE_CHECKING:
    from pathlib import Path

    from tests.unit.conftest import Project


def test_ai_install_config_task_uses_consumer_root(
    ctx: RecordingContext,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    ai.install_config(ctx)

    assert (tmp_path / "AGENTS.md").is_file()
    assert "2 link(s) created" in capsys.readouterr().out


def test_environment_tasks_use_consumer_config(
    ctx: RecordingContext,
    project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(project.root)
    env.sync(ctx, upgrade=True)
    env.clean(ctx)
    assert ctx.commands[0] == "uv sync --all-groups --extra postgres --upgrade"
    assert ctx.commands[1].startswith("rm -rf ")


def test_quality_tasks_use_consumer_targets(
    ctx: RecordingContext,
    project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(project.root)
    quality.fmt(ctx)
    quality.lint(ctx, fix=True)
    quality.types(ctx)
    quality.dead(ctx)
    quality.complexity(ctx)
    assert ctx.commands[0] == "uv run ruff format lib spec tasks.py"
    assert "--select I --fix" in ctx.commands[1]
    assert ctx.commands[2] == "uv run ruff check --fix lib spec tasks.py"
    assert ctx.commands[3:6] == ["uv run mypy", "uv run pyright", "uv run vulture"]
    assert "radon cc lib" in ctx.commands[6]


def test_test_tasks_scope_dynamically(
    ctx: RecordingContext,
    project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(project.root)
    testing.run(ctx, package="pkg", k="domain")
    testing.properties(ctx, profile="ci")
    assert "spec/pkg" in ctx.commands[0]
    assert "--cov=pkg" in ctx.commands[0]
    assert "-k=domain" in ctx.commands[0]
    assert ctx.commands[1].startswith("HYPOTHESIS_PROFILE=ci ")
    assert "spec/pkg/properties" in ctx.commands[1]


def test_test_task_rejects_unknown_package(
    ctx: RecordingContext,
    project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(project.root)
    with pytest.raises(ValueError, match="unknown package"):
        testing.run(ctx, package="other")


def test_in_process_tasks_do_not_spawn_commands(
    ctx: RecordingContext,
    project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project.module("pkg/a.py", '"""Doc."""\n\n\ndef f() -> int:\n    return 1\n')
    project.coverage({})
    monkeypatch.chdir(project.root)
    quality.cognitive(ctx)
    quality.mi(ctx)
    testing.crap(ctx)
    assert ctx.commands == []


def test_security_tasks_build_portable_commands(
    ctx: RecordingContext,
    project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(project.root)
    security.bandit(ctx)
    security.semgrep(ctx)
    security.semgrep(ctx, container=True)
    security.audit(ctx)
    assert "-r lib" in ctx.commands[0]
    assert ctx.commands[1] == "uv run semgrep --version"
    assert "podman run" in ctx.commands[3]
    assert "uv export" in ctx.commands[4]
    assert ctx.commands[-1] == "rm -f .audit-requirements.txt"


def test_semgrep_failure_has_container_guidance() -> None:
    class Unusable(RecordingContext):
        @override
        def run(self, command: str, **kwargs: Any) -> Result:
            super().run(command, **kwargs)
            return Result(command=command, exited=127)

    with pytest.raises(Exit, match="--container"):
        security.semgrep(Unusable())


def test_audit_always_removes_temporary_export() -> None:
    class Failing(RecordingContext):
        @override
        def run(self, command: str, **kwargs: Any) -> Result:
            result = super().run(command, **kwargs)
            if "pip-audit" in command:
                msg = "vulnerabilities found"
                raise RuntimeError(msg)
            return result

    context = Failing()
    with pytest.raises(RuntimeError, match="vulnerabilities"):
        security.audit(context)
    assert context.commands[-1] == "rm -f .audit-requirements.txt"
