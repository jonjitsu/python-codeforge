"""Named project-version regressions."""

import pytest

from ci import project
from ci.version import Version


def test_only_project_version_line_is_rewritten() -> None:
    """Tool configuration containing 'version' must remain untouched."""
    source = '[project]\nversion = "1.2.3"\n\n[tool.uv]\nrequired-version = ">=0.11"\n'
    rewritten = project.with_version(source, Version.parse("2.0.0"))
    assert 'version = "2.0.0"' in rewritten
    assert 'required-version = ">=0.11"' in rewritten


def test_missing_project_version_line_is_rejected() -> None:
    """Unexpected pyproject structure must not produce a partial release."""
    with pytest.raises(ValueError, match="no project version line"):
        project.with_version('[project]\nname = "python-codeforge"\n', Version.parse("1.0.0"))
