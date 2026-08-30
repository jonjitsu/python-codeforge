from __future__ import annotations

import shlex

import pytest

from python_codeforge import commands, ns
from python_codeforge.commands import PytestRun, SemgrepConfig, Targets


def test_targets_are_shell_quoted() -> None:
    assert Targets(("src", "a dir")).as_args() == "src 'a dir'"


def test_sync_has_generic_defaults_and_configurable_extras() -> None:
    assert commands.sync() == "uv sync --all-groups"
    assert (
        commands.sync(upgrade=True, extras=("db",)) == "uv sync --all-groups --extra db --upgrade"
    )


def test_clean_quotes_every_artefact() -> None:
    assert commands.clean((".coverage", "a b")) == "rm -rf .coverage 'a b'"


def test_quality_commands_are_uv_run_commands() -> None:
    targets = Targets(("lib", "spec"))
    assert commands.ruff_format(targets, check=True) == "uv run ruff format --check lib spec"
    assert commands.ruff_check(targets, fix=True) == "uv run ruff check --fix lib spec"
    assert commands.mypy() == "uv run mypy"
    assert commands.pyright() == "uv run pyright"
    assert commands.vulture() == "uv run vulture"


def test_radon_validates_its_kind() -> None:
    assert commands.radon("cc", "lib") == "uv run radon cc lib -s -a --total-average"
    with pytest.raises(ValueError, match="radon kind"):
        commands.radon("raw")


def test_pytest_flags_are_composable_and_quoted() -> None:
    command = PytestRun(
        k="not slow",
        fast=True,
        paths=("spec/a dir",),
        cov_packages=("pkg",),
    ).command()
    tokens = shlex.split(command)
    assert tokens[:3] == ["uv", "run", "pytest"]
    assert "spec/a dir" in tokens
    assert "--cov=pkg" in tokens
    assert "not slow" in tokens
    assert "not slow and not network" in tokens


def test_property_run_can_disable_coverage_and_randomly() -> None:
    command = PytestRun(paths=("tests/properties",), cov=False, no_random=True).command()
    assert command == "uv run pytest tests/properties -p no:randomly"


def test_hypothesis_profiles_are_validated() -> None:
    assert commands.hypothesis_profile("ci", "uv run pytest").startswith("HYPOTHESIS_PROFILE=ci ")
    with pytest.raises(ValueError, match="unknown hypothesis profile"):
        commands.hypothesis_profile("turbo", "uv run pytest")


def test_security_commands_include_expected_safety_flags() -> None:
    assert commands.bandit(path="lib") == "uv run bandit -c pyproject.toml -r lib -q"
    assert commands.semgrep_probe() == "uv run semgrep --version"
    local = commands.semgrep(SemgrepConfig(packs=("p/python",), paths=("lib",)))
    assert local == "uv run semgrep --error --quiet --metrics=off --config p/python lib"
    container = commands.semgrep(container=True)
    assert container.startswith("podman run --rm ")
    assert commands.SEMGREP_IMAGE in container
    assert "--no-emit-project" in commands.export_requirements("audit.txt")
    assert commands.pip_audit("audit.txt").endswith("-r audit.txt")


def test_namespace_exposes_root_and_subcollection_tasks() -> None:
    assert set(ns.task_names) >= {"check", "ci"}
    assert "quality.lint" in ns.task_names
    assert "test.crap" in ns.task_names
    assert "security.all" in ns.task_names
    assert "lint" not in ns.tasks
