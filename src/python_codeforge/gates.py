"""Aggregate root gates: ``invoke check`` and ``invoke ci``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from python_codeforge._invoke import task
from python_codeforge.collections.quality import cognitive, dead, hygiene_, lint, mi, types
from python_codeforge.collections.security import audit, bandit
from python_codeforge.collections.testing import coverage, crap, run

if TYPE_CHECKING:
    from invoke.context import Context


@task(pre=[hygiene_, lint, types, dead, mi, cognitive, run, coverage, crap])
def check(c: Context) -> None:
    """Run hygiene, quality, tests, coverage, and metric gates."""


@task(pre=[check, bandit, audit])
def ci(c: Context) -> None:
    """Run the main gate followed by portable security gates."""
