# python-codeforge

Reusable, typed [Invoke](https://www.pyinvoke.org/) tasks for Python projects managed with
`uv`. The package provides formatting, linting, strict type checking, dead-code detection,
tests, per-package coverage, CRAP, maintainability, cognitive complexity, hygiene, security,
environment, managed pre-commit-hook tasks, and portable agent configuration.

## Use it in another project

Add this project as a development dependency (use its eventual Git URL after moving this
directory into its own repository):

```bash
uv add --group dev "python-codeforge @ git+ssh://git@example/python-codeforge.git"
```

Create `tasks.py` in the consuming project:

```python
"""Project automation."""

from python_codeforge import ns

__all__ = ["ns"]
```

### How Invoke discovers the tasks

Invoke loads one root task collection. By default it searches for a local module named `tasks`;
installing a Python package does not automatically merge that package's tasks into the local
collection. The small `tasks.py` above is therefore the recommended integration point. See
[Invoke's collection-loading documentation](https://docs.pyinvoke.org/en/stable/concepts/loading.html).

The installed collection can also be selected directly without creating `tasks.py`, at the cost
of specifying it on every invocation:

```bash
uv run invoke --collection python_codeforge --list
uv run invoke --collection python_codeforge check
```

### Add project-specific tasks

A consuming project can add its own tasks to the imported root collection. This keeps Codeforge's
tasks and the project's tasks available through the normal `invoke` command:

```python
"""Project automation."""

from invoke.context import Context

from python_codeforge import ns, task


@task
def release(c: Context) -> None:
    """Build the project's release artefacts."""
    c.run("uv build")


ns.add_task(release)

__all__ = ["ns"]
```

This exposes both reusable and local commands:

```bash
uv run invoke check
uv run invoke quality.lint
uv run invoke release
```

Use a subcollection when local task names might collide with Codeforge's root tasks such as
`check` or `ci`:

```python
"""Project automation."""

from invoke import Collection
from invoke.context import Context

from python_codeforge import ns, task


@task
def deploy(c: Context) -> None:
    """Deploy the project."""
    c.run("deploy-command")


ns.add_collection(Collection("project", deploy))

__all__ = ["ns"]
```

The namespaced task is then `uv run invoke project.deploy`. See
[Invoke's namespace documentation](https://docs.pyinvoke.org/en/stable/concepts/namespaces.html)
for larger task trees.

For a conventional single-package project (`src/<normalized-project-name>` and
`tests/<normalized-project-name>`), no task-specific configuration is required. For explicit
control, add:

```toml
[tool.python-codeforge]
packages = ["acme", "acme_cli"]
source_dir = "src"
tests_dir = "tests"
targets = ["src", "tests", "tasks.py", "vulture_whitelist.py"]
sync_groups = "--all-groups"
sync_extras = ["postgres"]

[tool.python-codeforge.quality]
crap_limit = 10.0
max_complexity = 10
mi_floor = 40.0
cognitive_limit = 9

[tool.python-codeforge.quality.coverage]
acme = 100.0
acme_cli = 95.0
```

The coverage table also serves as the package list when `packages` is omitted. Missing quality
limits use the values above, and missing coverage floors default to 100% for each package.

Run `invoke --list` to discover the namespace. The main entry points are:

```text
invoke check
invoke ci
invoke env.sync
invoke quality.lint --fix
invoke test.run --package acme
invoke test.properties
invoke security.all
invoke hooks.install
invoke ai.install-config
```

### Install agent configuration

Install the packaged instructions and skills into the consuming repository:

```bash
uv run invoke ai.install-config
```

The task copies `AGENTS.md` and `.agents/skills` as the canonical configuration, then creates
`CLAUDE.md -> AGENTS.md` and `.claude/skills -> ../.agents/skills`. Re-running it is idempotent.
It preserves unrelated skills and refuses to overwrite differing files or provider paths; inspect
conflicts and pass `--force` only when replacement is intended. Real directories are never removed.
The distributable payload is maintained under `data/agent-config`; the root `.agents` directory
contains repository-local skills and is not packaged for consumers.

The package intentionally carries the complete quality toolchain as dependencies. Add it to a
development group, not to an application's runtime dependencies. It assumes `uv`, a `src/`
layout, Git for hygiene/hook tasks, and package-partitioned tests by default; all path assumptions
can be overridden in the table above.

Semgrep remains an explicit `invoke security.semgrep` task rather than part of `check` or `ci`,
because its native executable is not portable to every development environment. Use
`--container` for the official Podman image.

## Develop this project

```bash
uv sync --all-groups
uv run invoke check
uv run invoke ci
```
