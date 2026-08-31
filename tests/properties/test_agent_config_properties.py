from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import strategies as st

from python_codeforge import agent_config

portable_text = st.text(
    alphabet=st.characters(codec="utf-8"),
    max_size=100,
)


@given(content=portable_text)
def test_install_preserves_unrelated_canonical_skills(content: str) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        local_file = root / ".agents/skills/local-skill/note.txt"
        local_file.parent.mkdir(parents=True)
        expected = content.encode()
        local_file.write_bytes(expected)

        agent_config.install(root)

        assert local_file.read_bytes() == expected
