# python-codeforge

Reusable, typed [Invoke](https://www.pyinvoke.org/) tasks for Python projects managed with
`uv`. The package provides formatting, linting, strict type checking, dead-code detection,
tests, per-package coverage, CRAP, maintainability, cognitive complexity, hygiene, security,
environment, managed pre-commit-hook tasks, and portable agent configuration.

## Quick start

Add Codeforge to an existing `uv` project and get a green gate in four steps.

1. Install it as a development dependency from the matching GitHub release wheel:

   ```toml
   [dependency-groups]
   dev = ["python-codeforge"]

   [tool.uv.sources]
   python-codeforge = { url = "https://github.com/jonjitsu/python-codeforge/releases/download/1.0.0/python_codeforge-1.0.0-py3-none-any.whl" }
   ```

   Then run `uv lock`. Each released version publishes
   `python_codeforge-<version>-py3-none-any.whl` on GitHub; substitute the version in the
   URL. A Git dependency remains possible for unreleased commits, but the release wheel is the
   normal path for consuming projects that need hash-checked exports and `pip-audit --strict`.

2. Create `tasks.py` at the repository root:

   ```python
   """Project automation."""

   from python_codeforge import ns

   __all__ = ["ns"]
   ```

3. Run the gate:

   ```bash
   uv run invoke check   # format, lint, types, dead code, tests, coverage, complexity
   uv run invoke ci      # everything in check, plus security and dependency auditing
   ```

4. Optionally install the packaged automation:

   ```bash
   uv run invoke hooks.install       # managed pre-commit hooks
   uv run invoke ai.install-config   # AGENTS.md, skills, and provider links
   uv run invoke release.install     # Gitea-to-GitHub release workflows
   ```

`invoke --list` shows the full namespace. Defaults suit a conventional `src/<package>` layout with
package-partitioned tests; everything below covers configuration, per-project tasks, and the
release mechanism in detail.

## Use it in another project

The [quick start](#quick-start) covers installation and the minimal `tasks.py`; released versions
publish an immutable wheel on the public GitHub release mirror. The rest of this section explains
why that file is needed, how to add project-specific tasks, and which settings Codeforge reads.

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
invoke release.install
```

### Standard Gitea-to-GitHub releases

Codeforge can install the release mechanism used by this project into another repository. Gitea
remains the development forge and owns pull requests, CI, tags, and the canonical release. GitHub
receives only the exact tagged commit, matching release notes, and the built wheel asset.

Configure the public mirror and the Python version used by Actions:

```toml
[tool.python-codeforge.release]
github_repository = "owner/repository"
python_version = "3.12"
```

Then render the standard workflows into `.gitea/workflows`:

```bash
uv run invoke release.install
```

The installer manages `check.yaml`, `release-prepare.yaml`, `release-tag.yaml`, and
`release-mirror.yaml`. It is idempotent, preserves unrelated workflows, and refuses to replace a
differing managed file unless `--force` is passed. Commit the rendered workflows so releases do
not depend on Codeforge being available before the job starts.

Add `RELEASE_TOKEN` and `MIRROR_GITHUB_TOKEN` as Gitea repository Actions secrets. The release
token needs permission to push `release/next` and tags, create pull requests and Gitea releases,
and dispatch Actions; the mirror also uses it to verify the canonical Gitea release before the
GitHub token enters scope. The mirror token needs permission to update the configured GitHub
repository and its releases. Configure the Gitea repository to squash commits on merge and delete
merged branches.

Every merged change must use a Conventional Commit subject and add hand-written notes under
`## Unreleased`. A merge to `master` refreshes a standing `release/next` pull request. Merging that
pull request pins its exact merge commit, creates the Gitea tag and release, and only then dispatches
the GitHub mirror. The mirror rejects tags without a matching canonical Gitea release, builds the
wheel from the tagged tree, and attaches `python_codeforge-<version>-py3-none-any.whl` to the
GitHub release. Nothing re-drives a failed mirror: the Gitea release stays canonical, and the retry
is to run the `release-mirror` workflow by hand with the released tag. The tasks
`release.prepare`, `release.version`, and `release.notes` are also available for local inspection.

The installed workflows are written to fail loudly rather than release the wrong thing:

- **The tagged commit is the reviewed commit.** `release-tag` checks out the pull request's
  `merge_commit_sha` and then verifies that `HEAD` is that commit, so a push landing on `master`
  during the release window cannot be tagged, and an empty or unexpected value stops the job
  instead of silently falling back to the default branch.
- **Only canonical releases reach GitHub.** `release-mirror` has no tag trigger. It runs on
  dispatch, requires a `MAJOR.MINOR.PATCH` tag that already exists as a Gitea release, and
  confirms the checked-out tree declares that same version before `MIRROR_GITHUB_TOKEN` enters
  any step's scope. The dispatch input is bound through `env:` and never interpolated into shell
  source.
- **Release work is serialized.** `release-prepare`, `release-tag`, and `release-mirror` each hold
  a concurrency group; the two publishing workflows do not cancel a run in progress.
- **Credentials stay narrow.** Checkouts do not persist credentials, so `RELEASE_TOKEN` is absent
  from `.git/config` while the quality gate runs; pushes bind the authorization header through
  `GIT_CONFIG_*` environment variables rather than `git -c`, keeping the token out of the process
  argument list.
- **Failures are legible.** `release.prepare`, `release.version`, and `release.notes` report an
  invalid `pyproject.toml` or `CHANGELOG.md` as a one-line error rather than a traceback.

Gitea does not enforce GitHub's `permissions:` scoping, so the templates deliberately carry no
permissions block and each records that in a comment; authorization comes from the tokens a step
binds, and nothing else.

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

Development happens in the canonical Gitea repository. GitHub contains released commits and
release notes only; report issues and open pull requests in Gitea.

```bash
uv sync --all-groups
uv run invoke check
uv run invoke ci
```

Every change uses a Conventional Commit subject and adds a hand-written entry beneath
`## Unreleased` in `CHANGELOG.md`. Merging the standing `release/next` pull request creates the
Gitea release and mirrors the tagged commit to GitHub.
