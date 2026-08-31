"""AI agent configuration installation tasks."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from python_codeforge import agent_config
from python_codeforge._invoke import Exit, task

if TYPE_CHECKING:
    from invoke.context import Context


@task(
    name="install-config",
    help={"force": "replace conflicting files and symlinks, but never directories"},
)
def install_config(c: Context, force: bool = False) -> None:
    """Install shared agent instructions, skills, and provider symlinks."""
    try:
        report = agent_config.install(Path(c.cwd), force=force)
    except agent_config.AgentConfigConflictError as error:
        raise Exit(str(error), code=1) from error
    print(
        f"agent config: {report.copied} file(s) copied, "
        f"{report.linked} link(s) created, {report.unchanged} unchanged"
    )
