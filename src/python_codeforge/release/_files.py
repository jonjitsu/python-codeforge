"""Safely install a fixed set of rendered release workflow files."""

from pathlib import Path

type RenderedWorkflow = tuple[Path, str]


class WorkflowConflictError(RuntimeError):
    """Installing workflows would replace a consumer-owned path."""


def install(
    root: Path,
    rendered: tuple[RenderedWorkflow, ...],
    *,
    force: bool,
) -> tuple[int, int]:
    """Preflight and write rendered files beneath ``root``."""
    conflicts = [
        conflict
        for destination, content in rendered
        if (conflict := _conflict(root, destination, content, force=force))
    ]
    if conflicts:
        details = "\n  - ".join(conflicts)
        message = (
            "release workflow installation would replace existing paths:\n"
            f"  - {details}\n"
            "Re-run with --force to replace conflicting files. Directories are never removed."
        )
        raise WorkflowConflictError(message)

    copied = sum(_write(destination, content) for destination, content in rendered)
    return copied, len(rendered) - copied


def _conflict(root: Path, destination: Path, content: str, *, force: bool) -> str | None:
    parent_conflict = _parent_conflict(root, destination)
    return parent_conflict or _leaf_conflict(destination, content, force=force)


def _parent_conflict(root: Path, destination: Path) -> str | None:
    cursor = root
    for part in destination.relative_to(root).parts[:-1]:
        cursor /= part
        if cursor.is_symlink():
            return f"{cursor} is a symlink; refusing to install through it"
        if cursor.exists() and not cursor.is_dir():
            return f"{cursor} is not a directory"
    return None


def _leaf_conflict(destination: Path, content: str, *, force: bool) -> str | None:
    if destination.is_symlink():
        return None if force else f"{destination} is a symlink"
    if not destination.exists():
        return None
    if not destination.is_file():
        return f"{destination} is not a regular file"
    if destination.read_text(encoding="utf-8") == content or force:
        return None
    return f"{destination} differs from the standard workflow"


def _write(destination: Path, content: str) -> bool:
    if not destination.is_symlink() and destination.is_file():
        if destination.read_text(encoding="utf-8") == content:
            return False
        destination.unlink()
    elif destination.is_symlink():
        destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return True
