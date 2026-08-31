"""Install the agent configuration bundled with python-codeforge."""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from python_codeforge._agent_links import ProviderLink, create_link, link_conflict, provider_links

PACKAGED_DIRECTORY: Final = "_agent_config"
SOURCE_DIRECTORY: Final = Path("data/agent-config")
CANONICAL_FILE: Final = "AGENTS.md"
CANONICAL_SKILLS: Final = ".agents/skills"
type _Copy = tuple[Path, Path]


class AgentConfigConflictError(RuntimeError):
    """Raised when installation would replace consumer-owned configuration."""


@dataclass(frozen=True, slots=True)
class InstallReport:
    """Summary of an agent configuration installation."""

    copied: int
    linked: int
    unchanged: int


def bundled_root() -> Path:
    """Locate agent configuration in an installed wheel or source checkout."""
    package_root = Path(__file__).parent
    installed = package_root / PACKAGED_DIRECTORY
    if (installed / CANONICAL_FILE).is_file():
        return installed

    checkout_payload = package_root.parents[1] / SOURCE_DIRECTORY
    if (checkout_payload / CANONICAL_FILE).is_file():
        return checkout_payload

    msg = "python-codeforge's bundled agent configuration is missing"
    raise FileNotFoundError(msg)


def _files_below(root: Path) -> tuple[Path, ...]:
    candidates = (root,) if root.is_file() else root.rglob("*")
    return tuple(path for path in candidates if path.is_file() and not path.is_symlink())


def _source_files(source: Path) -> tuple[Path, ...]:
    files = _files_below(source / CANONICAL_FILE) + _files_below(source / ".agents")
    if source / CANONICAL_FILE not in files or not any(
        path.is_relative_to(source / CANONICAL_SKILLS) for path in files
    ):
        msg = "bundled agent configuration must contain AGENTS.md and at least one skill"
        raise FileNotFoundError(msg)
    return tuple(sorted(files))


def _parent_conflict(root: Path, destination: Path) -> str | None:
    cursor = root
    for part in destination.relative_to(root).parts[:-1]:
        cursor /= part
        if cursor.is_symlink():
            return f"{cursor} is a symlink; refusing to install through it"
        if cursor.exists() and not cursor.is_dir():
            return f"{cursor} is not a directory"
    return None


def _copy_conflict(source: Path, destination: Path, *, force: bool) -> str | None:
    if destination.is_symlink():
        return None if force else f"{destination} is a symlink"
    if not destination.exists():
        return None
    if not destination.is_file():
        return f"{destination} is not a regular file"
    if destination.read_bytes() == source.read_bytes() or force:
        return None
    return f"{destination} differs from the packaged configuration"


def _raise_conflicts(conflicts: list[str]) -> None:
    if not conflicts:
        return
    details = "\n  - ".join(conflicts)
    msg = (
        "agent configuration installation would replace existing paths:\n"
        f"  - {details}\n"
        "Re-run with --force to replace conflicting files. Directories are never removed."
    )
    raise AgentConfigConflictError(msg)


def _copy_conflicts(root: Path, copies: tuple[_Copy, ...], *, force: bool) -> list[str]:
    conflicts: list[str] = []
    for source, destination in copies:
        conflict = _parent_conflict(root, destination) or _copy_conflict(
            source, destination, force=force
        )
        if conflict:
            conflicts.append(conflict)
    return conflicts


def _link_conflicts(root: Path, links: tuple[ProviderLink, ...], *, force: bool) -> list[str]:
    conflicts: list[str] = []
    for link in links:
        conflict = _parent_conflict(root, link.path) or link_conflict(link, force=force)
        if conflict:
            conflicts.append(conflict)
    return conflicts


def _copy(source: Path, destination: Path) -> bool:
    if (
        not destination.is_symlink()
        and destination.is_file()
        and destination.read_bytes() == source.read_bytes()
    ):
        return False
    if destination.is_symlink() or destination.is_file():
        destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return True


def install(root: Path, *, force: bool = False, source: Path | None = None) -> InstallReport:
    """Install canonical agent files and provider aliases into ``root``.

    Existing directories and files not owned by the package are preserved. A
    differing managed file requires ``force``; real directories are never
    removed, even then.
    """
    destination_root = root.resolve()
    source_root = source or bundled_root()
    copies = tuple(
        (path, destination_root / path.relative_to(source_root))
        for path in _source_files(source_root)
    )
    links = provider_links(destination_root)
    conflicts = _copy_conflicts(destination_root, copies, force=force)
    conflicts.extend(_link_conflicts(destination_root, links, force=force))
    _raise_conflicts(conflicts)

    copied = sum(_copy(source_path, destination) for source_path, destination in copies)
    linked = sum(create_link(link) for link in links)
    unchanged = len(copies) + len(links) - copied - linked
    return InstallReport(copied=copied, linked=linked, unchanged=unchanged)
