from __future__ import annotations

import shlex

from hypothesis import given
from hypothesis import strategies as st

from python_codeforge.commands import PytestRun, SemgrepConfig, Targets, semgrep

paths = st.text(min_size=1, max_size=20).filter(lambda text: not text.isspace())


@given(values=st.lists(paths, min_size=1, max_size=5))
def test_targets_survive_a_shell_round_trip(values: list[str]) -> None:
    assert shlex.split(Targets(tuple(values)).as_args()) == values


@given(
    k=st.text(max_size=20),
    fast=st.booleans(),
    cov=st.booleans(),
    quiet=st.booleans(),
    no_random=st.booleans(),
    run_paths=st.lists(paths, max_size=3),
)
def test_pytest_command_is_always_parseable(
    k: str,
    fast: bool,
    cov: bool,
    quiet: bool,
    no_random: bool,
    run_paths: list[str],
) -> None:
    command = PytestRun(
        k=k,
        fast=fast,
        cov=cov,
        quiet=quiet,
        no_random=no_random,
        paths=tuple(run_paths),
    ).command()
    tokens = shlex.split(command)
    assert tokens[:3] == ["uv", "run", "pytest"]
    assert ("--cov" in command) == cov
    assert ("-q" in tokens) == quiet
    assert ("-p" in tokens) == no_random
    assert all(path in tokens for path in run_paths)


@given(
    packs=st.lists(st.sampled_from(["p/python", "p/secrets", "p/ci"]), min_size=1, unique=True),
    scan_paths=st.lists(paths, min_size=1, max_size=3),
)
def test_semgrep_renders_one_flag_per_pack(packs: list[str], scan_paths: list[str]) -> None:
    tokens = shlex.split(semgrep(SemgrepConfig(packs=tuple(packs), paths=tuple(scan_paths))))
    assert tokens.count("--config") == len(packs)
    assert all(pack in tokens for pack in packs)
