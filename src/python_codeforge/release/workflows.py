"""Install configured Gitea-to-GitHub workflow templates."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from python_codeforge.release import _files

WORKFLOW_DIRECTORY: Final = Path(".gitea/workflows")
PACKAGED_DIRECTORY: Final = "_workflows"
EXPECTED_WORKFLOWS: Final = (
    "check.yaml",
    "release-mirror.yaml",
    "release-prepare.yaml",
    "release-tag.yaml",
)

_PYTHON_VERSION = re.compile(r"\d+\.\d+")
_GITHUB_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_PROJECT_NAME = re.compile(r"[A-Za-z0-9_.-]+")
_UNRESOLVED_MARKER = re.compile(r"__[A-Z][A-Z0-9_]*__")


WorkflowConflictError = _files.WorkflowConflictError


@dataclass(frozen=True, slots=True)
class WorkflowSettings:
    """Repository-specific values rendered into standard workflows."""

    project_name: str
    github_repository: str
    python_version: str


@dataclass(frozen=True, slots=True)
class WorkflowInstallReport:
    """Summary of a standard workflow installation."""

    copied: int
    unchanged: int


def load_settings(root: Path) -> WorkflowSettings:
    """Read and validate ``[tool.python-codeforge.release]`` configuration."""
    with (root / "pyproject.toml").open("rb") as handle:
        document = tomllib.load(handle)
    project = _mapping(document.get("project", {}))
    tool = _mapping(document.get("tool", {}))
    codeforge = _mapping(tool.get("python-codeforge", {}))
    release = _mapping(codeforge.get("release", {}))
    settings = WorkflowSettings(
        project_name=str(project.get("name", "")),
        github_repository=str(release.get("github_repository", "")),
        python_version=str(release.get("python_version", "")),
    )
    _validate(settings)
    return settings


def bundled_root() -> Path:
    """Return the standard workflow directory bundled with Codeforge."""
    root = Path(__file__).parent / PACKAGED_DIRECTORY
    missing = [name for name in EXPECTED_WORKFLOWS if not (root / name).is_file()]
    if missing:
        message = f"python-codeforge's bundled release workflows are missing: {', '.join(missing)}"
        raise FileNotFoundError(message)
    return root


def render(template: str, settings: WorkflowSettings) -> str:
    """Render repository settings into one workflow template."""
    replacements = {
        "__PROJECT_NAME__": settings.project_name,
        "__GITHUB_REPOSITORY__": settings.github_repository,
        "__PYTHON_VERSION__": settings.python_version,
        "__WHEEL_PACKAGE__": re.sub(r"[-_.]+", "_", settings.project_name).lower(),
    }
    rendered = template
    for marker, value in replacements.items():
        rendered = rendered.replace(marker, value)
    unresolved = _UNRESOLVED_MARKER.search(rendered)
    if unresolved:
        message = f"unresolved release workflow marker: {unresolved.group()}"
        raise ValueError(message)
    return rendered


def install(
    root: Path,
    *,
    force: bool = False,
    source: Path | None = None,
) -> WorkflowInstallReport:
    """Install configured workflows, preserving unrelated consumer files."""
    destination_root = root.resolve()
    settings = load_settings(destination_root)
    source_root = source or bundled_root()
    rendered = tuple(
        (
            destination_root / WORKFLOW_DIRECTORY / name,
            render((source_root / name).read_text(encoding="utf-8"), settings),
        )
        for name in EXPECTED_WORKFLOWS
    )
    copied, unchanged = _files.install(
        destination_root,
        rendered,
        force=force,
    )
    return WorkflowInstallReport(copied=copied, unchanged=unchanged)


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return cast("dict[str, object]", value)


def _validate(settings: WorkflowSettings) -> None:
    missing: list[str] = []
    if not _PROJECT_NAME.fullmatch(settings.project_name):
        missing.append("[project].name")
    if not _GITHUB_REPOSITORY.fullmatch(settings.github_repository):
        missing.append('[tool.python-codeforge.release].github_repository = "owner/repository"')
    if not _PYTHON_VERSION.fullmatch(settings.python_version):
        missing.append('[tool.python-codeforge.release].python_version = "3.12"')
    if missing:
        message = "invalid release workflow configuration; set " + " and ".join(missing)
        raise ValueError(message)
