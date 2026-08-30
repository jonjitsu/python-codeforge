# hygiene: allow-file private-key -- this module names the markers it detects.
"""Pure checks for common tracked-file defects.

These checks replace a small collection of generic hook scripts: conflict
markers, private-key headers, oversized files, trailing whitespace, final
newlines, and parseable TOML/YAML. Git supplies the file list in the thin task
body; every rule here is deterministic over text or a single path.

Waivers are narrow by design. ``hygiene: allow <rule>`` affects one line, and
``hygiene: allow-file <rule>`` must occur in the first ten lines. Both forms
name the exact rule, so suppressing one intentional pattern cannot hide an
unrelated defect.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

MAX_FILE_BYTES: Final = 512 * 1024
ALLOW_LINE: Final = "hygiene: allow"
ALLOW_FILE: Final = "hygiene: allow-file"
ALLOW_SCAN_LINES: Final = 10
CONFLICT_PREFIXES: Final = ("<<<<<<< ", ">>>>>>> ")
PRIVATE_KEY_MARKERS: Final = (
    "BEGIN RSA PRIVATE KEY",
    "BEGIN DSA PRIVATE KEY",
    "BEGIN EC PRIVATE KEY",
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN PGP PRIVATE KEY BLOCK",
    "BEGIN PRIVATE KEY",
    "PuTTY-User-Key-File",
)


@dataclass(frozen=True, slots=True)
class Finding:
    """One precisely located hygiene problem."""

    path: str
    rule: str
    detail: str
    line: int | None = None

    def render(self) -> str:
        """Render an editor-clickable finding."""
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: {self.rule} {self.detail}"


def _numbered(text: str) -> Iterator[tuple[int, str]]:
    yield from enumerate(text.split("\n"), start=1)


def find_conflict_markers(text: str) -> list[int]:
    """Return lines beginning with a sided Git conflict marker."""
    return [number for number, line in _numbered(text) if line.startswith(CONFLICT_PREFIXES)]


def find_private_keys(text: str) -> list[int]:
    """Return lines containing a recognizable private-key header."""
    return [
        number
        for number, line in _numbered(text)
        if any(marker in line for marker in PRIVATE_KEY_MARKERS)
    ]


def find_trailing_whitespace(text: str) -> list[int]:
    """Return lines ending in whitespace."""
    return [number for number, line in _numbered(text) if line and line != line.rstrip()]


def has_final_newline(text: str) -> bool:
    """Whether text is empty or ends in exactly one newline."""
    return not text or (text.endswith("\n") and not text.endswith("\n\n"))


def parse_error(path: Path, text: str) -> str | None:
    """Return the first TOML/YAML parse error, when applicable."""
    try:
        if path.suffix == ".toml":
            tomllib.loads(text)
        elif path.suffix in {".yaml", ".yml"}:
            yaml.safe_load(text)
    except (tomllib.TOMLDecodeError, yaml.YAMLError) as error:
        return str(error).splitlines()[0]
    return None


def _allowed_rule(line: str, token: str) -> str:
    _, separator, rest = line.partition(token)
    return rest.split()[0] if separator and rest.split() else ""


def file_allowances(text: str) -> set[str]:
    """Return whole-file rules waived in the first ten lines."""
    return {
        rule
        for line in text.split("\n")[:ALLOW_SCAN_LINES]
        if (rule := _allowed_rule(line, ALLOW_FILE))
    }


def line_allows(line: str, rule: str) -> bool:
    """Whether a line explicitly waives a named rule."""
    return ALLOW_FILE not in line and _allowed_rule(line, ALLOW_LINE) == rule


def _candidates(path: str, text: str) -> Iterator[Finding]:
    for line in find_conflict_markers(text):
        yield Finding(path, "merge-conflict", "unresolved merge marker", line)
    for line in find_private_keys(text):
        yield Finding(path, "private-key", "looks like a private key", line)
    for line in find_trailing_whitespace(text):
        yield Finding(path, "trailing-whitespace", "line ends in whitespace", line)
    if not has_final_newline(text):
        yield Finding(path, "final-newline", "must end in exactly one newline")


def check_text(path: str, text: str) -> Iterator[Finding]:
    """Yield unsuppressed findings for one text file."""
    waived = file_allowances(text)
    lines = dict(_numbered(text))
    for finding in _candidates(path, text):
        if finding.rule in waived:
            continue
        if finding.line is not None and line_allows(lines[finding.line], finding.rule):
            continue
        yield finding


def check_file(path: Path, root: Path) -> Iterator[Finding]:
    """Check one file, applying text checks only when it is UTF-8."""
    relative = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        yield Finding(relative, "large-file", f"{size} bytes > {MAX_FILE_BYTES} limit")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    yield from check_text(relative, text)
    error = parse_error(path, text)
    if error is not None:
        yield Finding(relative, "unparseable", error)


def check_files(paths: Iterable[Path], root: Path) -> list[Finding]:
    """Collect findings across existing files."""
    return [finding for path in paths if path.is_file() for finding in check_file(path, root)]
