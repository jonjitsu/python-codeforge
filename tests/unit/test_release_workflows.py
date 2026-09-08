"""Tests for installing configured Gitea release workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from python_codeforge.release import workflows as release_workflows

if TYPE_CHECKING:
    from pathlib import Path


def _configure(root: Path, *, project: str = "consumer", repository: str = "org/consumer") -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "'
        + project
        + '"\nversion = "1.0.0"\n\n[tool.python-codeforge.release]\n'
        + 'github_repository = "'
        + repository
        + '"\npython_version = "3.12"\n',
        encoding="utf-8",
    )


def test_bundled_workflows_are_complete() -> None:
    """The distribution owns exactly the standard workflow set."""
    source = release_workflows.bundled_root()
    assert tuple(path.name for path in sorted(source.glob("*.yaml"))) == (
        "check.yaml",
        "release-mirror.yaml",
        "release-prepare.yaml",
        "release-tag.yaml",
    )


def test_tagging_pins_the_reviewed_merge_and_serializes_releases() -> None:
    """A later master push cannot change the commit selected for a release."""
    workflow = (release_workflows.bundled_root() / "release-tag.yaml").read_text(encoding="utf-8")

    assert "ref: ${{ github.event.pull_request.merge_commit_sha }}" in workflow
    assert "concurrency:\n  group: release-tag\n  cancel-in-progress: false" in workflow
    assert "ref: master" not in workflow
    assert "MERGE_SHA: ${{ github.event.pull_request.merge_commit_sha }}" in workflow
    verify = workflow.split("- name: Verify the pinned merge commit", 1)[1].split("- uses:", 1)[0]
    assert '[ -z "$MERGE_SHA" ] || [ "$head" != "$MERGE_SHA" ]' in verify
    tag_step = workflow.split("- name: Tag the release", 1)[1].split("- name:", 1)[0]
    assert "GITEA_TOKEN: ${{ secrets.RELEASE_TOKEN }}" in tag_step
    assert "set -euo pipefail" in tag_step


def test_mirror_accepts_only_canonical_releases_without_script_interpolation() -> None:
    """A tag push or crafted dispatch input cannot reach the GitHub credential."""
    mirror = (release_workflows.bundled_root() / "release-mirror.yaml").read_text(encoding="utf-8")
    tagging = (release_workflows.bundled_root() / "release-tag.yaml").read_text(encoding="utf-8")

    assert 'tags: ["*"]' not in mirror
    assert 'tag="${{ inputs.tag' not in mirror
    assert "TAG: ${{ inputs.tag }}" in mirror
    assert mirror.count("${{ inputs.tag }}") == 1
    assert '[[ "$TAG" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+$ ]]' in mirror
    assert '"$API/repos/$REPO/releases/tags/$TAG"' in mirror
    assert mirror.index("releases/tags/$TAG") < mirror.index(
        "TOKEN: ${{ secrets.MIRROR_GITHUB_TOKEN }}"
    )
    assert "Verify the tag matches the project release" in mirror
    assert "Nothing retries automatically." in mirror
    assert "/actions/workflows/release-mirror.yaml/dispatches" in tagging
    assert tagging.index('"$API/repos/$REPO/releases"') < tagging.index(
        "/actions/workflows/release-mirror.yaml/dispatches"
    )


def test_mirror_builds_and_publishes_the_release_wheel() -> None:
    """The GitHub mirror attaches an immutable wheel built from the tagged commit."""
    mirror = (release_workflows.bundled_root() / "release-mirror.yaml").read_text(encoding="utf-8")

    assert "Build the release wheel" in mirror
    assert "uv build --wheel" in mirror
    assert "Publish the release wheel to GitHub" in mirror
    assert "dist/__WHEEL_PACKAGE__-${TAG}-py3-none-any.whl" in mirror
    assert mirror.index("Verify the tag matches the project release") < mirror.index(
        "Build the release wheel"
    )
    assert mirror.index("Create or update the GitHub release") < mirror.index(
        "Publish the release wheel to GitHub"
    )
    publish = mirror.split("- name: Publish the release wheel to GitHub", 1)[1].split(
        "- name:", 1
    )[0]
    assert "already published for $TAG" in publish


def test_gitea_workflows_do_not_claim_unsupported_permission_scoping() -> None:
    """Templates must not imply that Gitea enforces GitHub permission blocks."""
    for name in release_workflows.EXPECTED_WORKFLOWS:
        workflow = (release_workflows.bundled_root() / name).read_text(encoding="utf-8")
        assert "\npermissions:\n" not in workflow
        assert "Gitea does not enforce GitHub `permissions:` scoping" in workflow


def test_pushes_keep_the_release_token_out_of_the_process_arguments() -> None:
    """A credential in argv stays readable to anything else sharing the runner."""
    for name in ("release-prepare.yaml", "release-tag.yaml"):
        workflow = (release_workflows.bundled_root() / name).read_text(encoding="utf-8")
        assert "git -c http.extraHeader" not in workflow
        assert "GIT_CONFIG_KEY_0=http.extraHeader" in workflow
        assert 'GIT_CONFIG_VALUE_0="Authorization: token $GITEA_TOKEN"' in workflow


def test_render_rejects_unknown_template_markers() -> None:
    """A future template typo cannot silently enter a consumer repository."""
    settings = release_workflows.WorkflowSettings("consumer", "org/consumer", "3.12")
    with pytest.raises(ValueError, match="unresolved release workflow marker: __OTHER__"):
        release_workflows.render("value: __OTHER__\n", settings)


def test_install_renders_all_workflows_and_preserves_unrelated_files(tmp_path: Path) -> None:
    """Consumer settings are rendered without taking ownership of other workflows."""
    _configure(tmp_path)
    unrelated = tmp_path / ".gitea/workflows/deploy.yaml"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("name: deploy\n", encoding="utf-8")

    report = release_workflows.install(tmp_path)

    assert report == release_workflows.WorkflowInstallReport(copied=4, unchanged=0)
    installed = tuple(
        (unrelated.parent / name).read_text(encoding="utf-8")
        for name in release_workflows.EXPECTED_WORKFLOWS
    )
    assert all("__" not in workflow for workflow in installed)
    assert any("github.com/org/consumer.git" in workflow for workflow in installed)
    assert any('python-version: "3.12"' in workflow for workflow in installed)
    assert unrelated.read_text(encoding="utf-8") == "name: deploy\n"


def test_install_is_idempotent(tmp_path: Path) -> None:
    """Reinstalling the same configured templates performs no writes."""
    _configure(tmp_path)
    release_workflows.install(tmp_path)
    assert release_workflows.install(tmp_path) == release_workflows.WorkflowInstallReport(
        copied=0,
        unchanged=4,
    )


def test_install_can_render_an_explicit_template_source(tmp_path: Path) -> None:
    """The source override used by downstream packagers remains supported."""
    _configure(tmp_path)
    source = tmp_path / "templates"
    source.mkdir()
    for name in release_workflows.EXPECTED_WORKFLOWS:
        (source / name).write_text("name: __PROJECT_NAME__\n", encoding="utf-8")

    report = release_workflows.install(tmp_path, source=source)

    assert report.copied == 4
    for name in release_workflows.EXPECTED_WORKFLOWS:
        installed = tmp_path / release_workflows.WORKFLOW_DIRECTORY / name
        assert installed.read_text(encoding="utf-8") == "name: consumer\n"


def test_install_preflights_conflicts_before_writing(tmp_path: Path) -> None:
    """One differing managed file prevents every planned write."""
    _configure(tmp_path)
    target = tmp_path / ".gitea/workflows/check.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("consumer workflow\n", encoding="utf-8")

    with pytest.raises(release_workflows.WorkflowConflictError, match=r"check\.yaml differs"):
        release_workflows.install(tmp_path)

    assert target.read_text(encoding="utf-8") == "consumer workflow\n"
    assert not (target.parent / "release-tag.yaml").exists()


def test_force_replaces_files_and_final_symlinks(tmp_path: Path) -> None:
    """Force replaces managed leaf paths after the caller opts in."""
    _configure(tmp_path)
    workflow_root = tmp_path / ".gitea/workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "check.yaml").write_text("consumer workflow\n", encoding="utf-8")
    (workflow_root / "release-tag.yaml").symlink_to("check.yaml")

    report = release_workflows.install(tmp_path, force=True)

    assert report.copied == 4
    assert not (workflow_root / "release-tag.yaml").is_symlink()


@pytest.mark.parametrize("force", [False, True])
def test_install_never_writes_through_parent_symlink(tmp_path: Path, force: bool) -> None:
    """A parent symlink cannot redirect managed workflows outside the repository."""
    _configure(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".gitea").symlink_to(outside, target_is_directory=True)

    with pytest.raises(
        release_workflows.WorkflowConflictError, match="refusing to install through"
    ):
        release_workflows.install(tmp_path, force=force)

    assert list(outside.iterdir()) == []


def test_install_rejects_non_directory_parent_and_leaf_directory(tmp_path: Path) -> None:
    """Force never destroys directory structure owned by a consumer."""
    _configure(tmp_path)
    (tmp_path / ".gitea").write_text("not a directory\n", encoding="utf-8")
    with pytest.raises(release_workflows.WorkflowConflictError, match="is not a directory"):
        release_workflows.install(tmp_path, force=True)

    (tmp_path / ".gitea").unlink()
    leaf = tmp_path / ".gitea/workflows/check.yaml"
    leaf.mkdir(parents=True)
    with pytest.raises(release_workflows.WorkflowConflictError, match="not a regular file"):
        release_workflows.install(tmp_path, force=True)


@pytest.mark.parametrize(
    ("project", "repository", "expected"),
    [
        ("bad name", "org/consumer", r"\[project\]\.name"),
        ("consumer", "github.com/org/consumer", "github_repository"),
    ],
)
def test_invalid_settings_are_rejected(
    tmp_path: Path,
    project: str,
    repository: str,
    expected: str,
) -> None:
    """Template settings accept only values safe for YAML and shell contexts."""
    _configure(tmp_path, project=project, repository=repository)
    with pytest.raises(ValueError, match=expected):
        release_workflows.load_settings(tmp_path)


def test_missing_bundled_workflow_is_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken package cannot silently install an incomplete pipeline."""
    monkeypatch.setattr(release_workflows, "PACKAGED_DIRECTORY", str(tmp_path.name))
    with pytest.raises(FileNotFoundError, match="bundled release workflows are missing"):
        release_workflows.bundled_root()
