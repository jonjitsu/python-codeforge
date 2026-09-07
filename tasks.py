"""Invoke entry point for developing this distribution.

Release automation is kept outside ``src`` so it is checked but not packaged.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "automation"))

from ci.tasks import ns

__all__ = ["ns"]
