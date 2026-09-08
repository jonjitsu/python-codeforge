# Changelog

## Unreleased

- Each GitHub release now includes an immutable `python_codeforge-<version>-py3-none-any.whl`
  asset built from the tagged commit, so consumers can depend on a hashed release-wheel URL
  instead of a Git dependency.
- `security.audit` now uses the OSV vulnerability service so `pip-audit --strict` can audit
  exports that include hashed release-wheel dependencies.
- The README now opens with a quick start and documents the safety properties of the
  installed release workflows.
- Added reusable semantic-version release tasks and installable Gitea workflow
  templates so consumer projects can standardize Gitea development and publish
  only reviewed releases to GitHub. Tagging pins the reviewed merge commit and
  fails if the pinned commit is not what was checked out, mirroring rejects
  unversioned tags and tags without a canonical Gitea release, pushes keep the
  release token out of the process arguments, and the templates record that Gitea
  does not enforce GitHub `permissions:` scoping.
- Python 3.12 is now the minimum supported interpreter instead of Python 3.13.
- Project and lockfile metadata now agree with the existing `1.0.0` release tag.
- Gitea is now the canonical development forge. Gitea Actions runs checks,
  prepares reviewed releases, creates the canonical tag and release, and then
  mirrors only released commits and release notes to the public GitHub repository.

## 1.0.0

- Added the reusable Codeforge quality gates and portable agent-configuration
  installer used by consuming Python projects.
