"""Environment creation and cleanup tasks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from python_codeforge import commands
from python_codeforge._invoke import task
from python_codeforge.config import load

if TYPE_CHECKING:
    from invoke.context import Context


@task
def sync(c: Context, upgrade: bool = False) -> None:
    """Create or refresh the uv environment from the lockfile."""
    settings = load(Path(c.cwd))
    c.run(
        commands.sync(
            upgrade=upgrade,
            groups=settings.sync_groups,
            extras=settings.sync_extras,
        ),
        pty=True,
    )


@task
def clean(c: Context) -> None:
    """Remove configured build, cache, and coverage artefacts."""
    c.run(commands.clean(load(Path(c.cwd)).artefacts), pty=True)
