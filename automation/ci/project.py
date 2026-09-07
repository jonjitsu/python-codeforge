"""Read and update the project version in ``pyproject.toml``."""

import re
import tomllib
from pathlib import Path

from ci.version import Version

PATH = Path("pyproject.toml")

_VERSION_LINE = re.compile(r'^version = "\d+\.\d+\.\d+"$', re.MULTILINE)


def current_version(text: str) -> Version:
    """Return the version declared by the project table."""
    return Version.parse(str(tomllib.loads(text)["project"]["version"]))


def with_version(text: str, version: Version) -> str:
    """Replace only the project version line."""
    replaced, count = _VERSION_LINE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        message = "pyproject.toml has no project version line to replace"
        raise ValueError(message)
    return replaced
