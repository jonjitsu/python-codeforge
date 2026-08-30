"""Typing-only names that Vulture cannot see being used."""

from __future__ import annotations


class _Used:
    """Mark arbitrary attribute access as a static use."""

    def __getattr__(self, name: str) -> _Used:
        """Return the marker for every typing-only name."""
        return self


_ = _Used()

# Parameters of typing-only overloads that describe Invoke's keyword API.
_.pre
_.post
_.help

# Referenced only inside the string annotation cast("Task[Any]", ...).
_.Task
