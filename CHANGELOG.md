# Changelog

## Unreleased

- Python 3.12 is now the minimum supported interpreter instead of Python 3.13.
- Project and lockfile metadata now agree with the existing `1.0.0` release tag.
- Gitea is now the canonical development forge. Gitea Actions runs checks,
  prepares reviewed releases, creates the canonical tag and release, and then
  mirrors only released commits and release notes to the public GitHub repository.

## 1.0.0

- Added the reusable Codeforge quality gates and portable agent-configuration
  installer used by consuming Python projects.
