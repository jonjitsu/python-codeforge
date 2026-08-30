"""A command-recording :class:`invoke.Context` for task tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from invoke.context import Context
from invoke.runners import Result

if TYPE_CHECKING:
    from collections.abc import Mapping


class RecordingContext(Context):
    """Capture commands instead of starting subprocesses."""

    def __init__(self, stdout: Mapping[str, str] | None = None) -> None:
        """Initialize an empty log and optional substring-keyed canned output."""
        super().__init__()
        self.commands: list[str] = []
        self._stdout = dict(stdout or {})

    @override
    def run(self, command: str, **kwargs: Any) -> Result:
        """Record a command and return a successful result."""
        self.commands.append(command)
        canned = next((text for key, text in self._stdout.items() if key in command), "")
        return Result(command=command, exited=0, stdout=canned)
