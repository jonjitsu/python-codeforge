from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_codeforge.config import load

if TYPE_CHECKING:
    from pathlib import Path

    from tests.unit.conftest import Project


def test_explicit_configuration_is_typed(project: Project) -> None:
    settings = load(project.root)
    assert settings.packages == ("pkg",)
    assert settings.source_dir == "lib"
    assert settings.tests_dir == "spec"
    assert settings.targets == ("lib", "spec", "tasks.py")
    assert settings.sync_extras == ("postgres",)
    assert settings.coverage_floors == {"pkg": 100.0}
    assert settings.suite("pkg") == "spec/pkg"
    assert settings.source_prefix("pkg") == "lib/pkg/"


def test_minimal_consumer_is_inferred_from_project_name(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "acme-tools"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    settings = load(tmp_path)
    assert settings.packages == ("acme_tools",)
    assert settings.coverage_floors == {"acme_tools": 100.0}
    assert settings.source_dir == "src"
    assert settings.targets == ("src", "tests", "tasks.py")
    assert settings.sync_extras == ()


def test_coverage_table_can_supply_packages(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[tool.python-codeforge.quality.coverage]\na = 90\nb = 95\n",
        encoding="utf-8",
    )
    settings = load(tmp_path)
    assert settings.packages == ("a", "b")
    assert settings.coverage_floors == {"a": 90.0, "b": 95.0}


def test_missing_package_identity_is_actionable(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot infer a package name"):
        load(tmp_path)


def test_invalid_list_has_a_precise_error(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "pkg"\n[tool.python-codeforge]\npackages = "pkg"\n',
        encoding="utf-8",
    )
    with pytest.raises(TypeError, match="expected a list of strings"):
        load(tmp_path)
