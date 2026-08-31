from __future__ import annotations

from pathlib import Path

import pytest

from python_codeforge import agent_config


def test_source_payload_is_independent_from_repository_agent_config() -> None:
    source = agent_config.bundled_root()

    assert source.name in {"agent-config", "_agent_config"}
    assert (source / "AGENTS.md").is_file()
    assert (source / ".agents/skills/python-development/SKILL.md").is_file()


def test_install_copies_canonical_files_and_links_provider_paths(tmp_path: Path) -> None:
    report = agent_config.install(tmp_path)

    assert report.copied >= 3
    assert report.linked == 2
    assert report.unchanged == 0
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / ".agents/skills/python-development/SKILL.md").is_file()
    assert (tmp_path / "CLAUDE.md").readlink() == Path("AGENTS.md")
    assert (tmp_path / ".claude/skills").readlink() == Path("../.agents/skills")


def test_install_is_idempotent(tmp_path: Path) -> None:
    first = agent_config.install(tmp_path)
    second = agent_config.install(tmp_path)

    assert second.copied == 0
    assert second.linked == 0
    assert second.unchanged == first.copied + first.linked


def test_install_preflights_all_conflicts_before_writing(tmp_path: Path) -> None:
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text("consumer instructions\n", encoding="utf-8")

    with pytest.raises(agent_config.AgentConfigConflictError, match=r"AGENTS\.md differs"):
        agent_config.install(tmp_path)

    assert agents_file.read_text(encoding="utf-8") == "consumer instructions\n"
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_force_replaces_conflicting_files_and_symlinks(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("consumer instructions\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("consumer Claude instructions\n", encoding="utf-8")
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "skills").symlink_to("elsewhere", target_is_directory=True)

    report = agent_config.install(tmp_path, force=True)

    assert report.copied >= 3
    assert report.linked == 2
    assert (tmp_path / "CLAUDE.md").readlink() == Path("AGENTS.md")
    assert (claude / "skills").readlink() == Path("../.agents/skills")


def test_force_never_removes_a_real_provider_directory(tmp_path: Path) -> None:
    local_skill = tmp_path / ".claude/skills/local/SKILL.md"
    local_skill.parent.mkdir(parents=True)
    local_skill.write_text("local\n", encoding="utf-8")

    with pytest.raises(agent_config.AgentConfigConflictError, match="move its contents"):
        agent_config.install(tmp_path, force=True)

    assert local_skill.read_text(encoding="utf-8") == "local\n"
    assert not (tmp_path / "AGENTS.md").exists()


def test_install_refuses_to_write_through_parent_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".agents").symlink_to(outside, target_is_directory=True)

    with pytest.raises(agent_config.AgentConfigConflictError, match="refusing to install through"):
        agent_config.install(tmp_path, force=True)

    assert list(outside.iterdir()) == []
