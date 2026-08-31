"""Provider-specific symlinks for portable agent configuration."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

PROVIDER_LINKS: Final[tuple[tuple[str, str, bool], ...]] = (
    ("CLAUDE.md", "AGENTS.md", False),
    (".claude/skills", ".agents/skills", True),
)


@dataclass(frozen=True, slots=True)
class ProviderLink:
    """A provider alias and its canonical repository target."""

    path: Path
    target: Path
    target_is_directory: bool


def provider_links(root: Path) -> tuple[ProviderLink, ...]:
    """Resolve configured provider links below a repository root."""
    return tuple(
        ProviderLink(root / link, root / target, target_is_directory)
        for link, target, target_is_directory in PROVIDER_LINKS
    )


def same_link(link: ProviderLink) -> bool:
    """Whether an existing symlink resolves to its canonical target."""
    if not link.path.is_symlink():
        return False
    actual = link.path.readlink()
    if not actual.is_absolute():
        actual = link.path.parent / actual
    return actual.resolve(strict=False) == link.target.resolve(strict=False)


def link_conflict(link: ProviderLink, *, force: bool) -> str | None:
    """Describe a provider-path conflict, if one would block installation."""
    if same_link(link):
        return None
    if not link.path.is_symlink() and not link.path.exists():
        return None
    if link.path.is_dir() and not link.path.is_symlink():
        return f"{link.path} is a directory; move its contents before linking"
    if force:
        return None
    return f"{link.path} exists and does not point to {link.target}"


def create_link(link: ProviderLink) -> bool:
    """Create a relative provider symlink, returning whether it changed."""
    if same_link(link):
        return False
    if link.path.is_symlink() or link.path.is_file():
        link.path.unlink()
    link.path.parent.mkdir(parents=True, exist_ok=True)
    relative_target = os.path.relpath(link.target, start=link.path.parent)
    link.path.symlink_to(relative_target, target_is_directory=link.target_is_directory)
    return True
