"""Pure, shell-safe command builders used by the task bodies.

The task modules intentionally contain almost no logic: they load consumer
configuration, call a builder from here, and pass the resulting string to
``Context.run``. Keeping construction in this module makes quoting rules and
flag combinations testable without starting a subprocess.

All Python tools run through ``uv run`` so the same namespace works when
Invoke itself is started from a global interpreter. Environment-management
commands are the exception because ``uv sync`` and ``uv export`` must operate
on the project environment rather than from inside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from shlex import quote

UV_RUN = "uv run"
SEMGREP_IMAGE = "docker.io/semgrep/semgrep:latest"


@dataclass(frozen=True, slots=True)
class Targets:
    """Paths operated on by formatting and linting tools."""

    paths: tuple[str, ...] = ("src", "tests", "tasks.py")

    def as_args(self) -> str:
        """Render paths as shell-safe arguments."""
        return " ".join(quote(path) for path in self.paths)


DEFAULT_TARGETS = Targets()


def _uv(*parts: str) -> str:
    return " ".join([UV_RUN, *(part for part in parts if part)])


def sync(
    *, upgrade: bool = False, groups: str = "--all-groups", extras: tuple[str, ...] = ()
) -> str:
    """Build the development-environment sync command."""
    extra_args = tuple(f"--extra {quote(extra)}" for extra in extras)
    return " ".join(
        part for part in ("uv sync", groups, *extra_args, "--upgrade" if upgrade else "") if part
    )


def clean(artefacts: tuple[str, ...]) -> str:
    """Build a command that removes configured generated artefacts."""
    return "rm -rf " + " ".join(quote(name) for name in artefacts)


def ruff_format(targets: Targets = DEFAULT_TARGETS, *, check: bool = False) -> str:
    """Build a Ruff formatter command."""
    return _uv("ruff format", "--check" if check else "", targets.as_args())


def ruff_check(
    targets: Targets = DEFAULT_TARGETS,
    *,
    fix: bool = False,
    select: str = "",
) -> str:
    """Build a Ruff lint command."""
    return _uv(
        "ruff check",
        f"--select {quote(select)}" if select else "",
        "--fix" if fix else "",
        targets.as_args(),
    )


def mypy() -> str:
    """Build a mypy command; paths come from the consumer's configuration."""
    return _uv("mypy")


def pyright() -> str:
    """Build a Pyright command; paths come from the consumer's configuration."""
    return _uv("pyright")


def vulture() -> str:
    """Build a Vulture command; paths come from the consumer's configuration."""
    return _uv("vulture")


def radon(kind: str, path: str = "src") -> str:
    """Build a Radon cyclomatic-complexity or maintainability command."""
    if kind not in {"cc", "mi"}:
        msg = f"radon kind must be 'cc' or 'mi', got {kind!r}"
        raise ValueError(msg)
    extra = "-s -a --total-average" if kind == "cc" else "-s"
    return _uv(f"radon {kind}", quote(path), extra)


@dataclass(frozen=True, slots=True)
class PytestRun:
    """A pytest invocation described declaratively."""

    k: str = ""
    fast: bool = False
    cov: bool = True
    quiet: bool = False
    paths: tuple[str, ...] = ()
    no_random: bool = False
    cov_packages: tuple[str, ...] = ()

    def _coverage_flags(self) -> str:
        if not self.cov:
            return ""
        sources = " ".join(f"--cov={quote(package)}" for package in self.cov_packages) or "--cov"
        return f"{sources} --cov-report=term-missing --cov-report=json"

    def command(self) -> str:
        """Render the full command."""
        return _uv(
            "pytest",
            " ".join(quote(path) for path in self.paths),
            "-q" if self.quiet else "",
            self._coverage_flags(),
            f"-k {quote(self.k)}" if self.k else "",
            "-m 'not slow and not network'" if self.fast else "",
            "-p no:randomly" if self.no_random else "",
        )


def hypothesis_profile(profile: str, command: str) -> str:
    """Prefix a command with a supported Hypothesis profile selection."""
    allowed = {"dev", "ci", "thorough"}
    if profile not in allowed:
        msg = f"unknown hypothesis profile {profile!r}; expected one of {sorted(allowed)}"
        raise ValueError(msg)
    return f"HYPOTHESIS_PROFILE={quote(profile)} {command}"


def bandit(config: str = "pyproject.toml", path: str = "src") -> str:
    """Build a Bandit command."""
    return _uv("bandit", f"-c {quote(config)}", "-r", quote(path), "-q")


@dataclass(frozen=True, slots=True)
class SemgrepConfig:
    """Semgrep rule packs and scan paths."""

    packs: tuple[str, ...] = ("p/python", "p/security-audit", "p/secrets")
    paths: tuple[str, ...] = ("src", "tests")
    extra: tuple[str, ...] = field(default=("--error", "--quiet", "--metrics=off"))


def semgrep(config: SemgrepConfig | None = None, *, container: bool = False) -> str:
    """Build a local or Podman-based Semgrep command."""
    selected = config or SemgrepConfig()
    args = " ".join(
        (
            " ".join(selected.extra),
            " ".join(f"--config {quote(pack)}" for pack in selected.packs),
            " ".join(quote(path) for path in selected.paths),
        )
    )
    if container:
        return f'podman run --rm -v "$PWD":/src:ro -w /src {SEMGREP_IMAGE} semgrep {args}'
    return _uv("semgrep", args)


def semgrep_probe() -> str:
    """Build a cheap command that verifies the Semgrep executable starts."""
    return _uv("semgrep", "--version")


def export_requirements(output: str) -> str:
    """Export all locked development dependencies without the local project."""
    return (
        "uv export --frozen --all-groups --no-emit-project"
        f" --format requirements.txt -o {quote(output)}"
    )


def pip_audit(requirements: str) -> str:
    """Build a pip-audit command for an exported requirements file."""
    return _uv("pip-audit", "--strict", "--progress-spinner=off", "-r", quote(requirements))
