"""Read and update a project's version in ``pyproject.toml``."""

import re
import tomllib

from python_codeforge.release.version import PATCH, Version

_VERSION_LINE = re.compile(
    r"^(?P<prefix>[ \t]*version[ \t]*=[ \t]*)(?P<quote>['\"])"
    r"\d+\.\d+\.\d+(?P=quote)(?P<suffix>[ \t]*(?:#.*)?)$",
    re.MULTILINE,
)


def current_version(text: str) -> Version:
    """Return the version declared by the project table."""
    return Version.parse(str(tomllib.loads(text)["project"]["version"]))


def with_version(text: str, version: Version) -> str:
    """Replace only the version declared directly in ``[project]``."""
    matches = tuple(_VERSION_LINE.finditer(text))
    message = "pyproject.toml has no project version line to replace"
    try:
        marker = current_version(text).bumped(PATCH)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(message) from error
    for match in matches:
        if current_version(_replace(text, match, marker)) == marker:
            return _replace(text, match, version)
    raise ValueError(message)


def _replace(text: str, match: re.Match[str], version: Version) -> str:
    rendered = f"{match['prefix']}{match['quote']}{version}{match['quote']}{match['suffix']}"
    return f"{text[: match.start()]}{rendered}{text[match.end() :]}"
