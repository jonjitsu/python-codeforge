"""Codeforge's task collection extended with repository release tasks."""

from ci.tasks.release import release_notes, release_prepare, release_version
from python_codeforge import ns

ns.add_task(release_prepare)
ns.add_task(release_version)
ns.add_task(release_notes)

__all__ = ["ns"]
