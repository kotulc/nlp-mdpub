"""Root test configuration — session-level cleanup of runtime artifacts"""

import shutil
from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).parent.parent

_CLEANUP_FILES = ["mdpub.db", "test.db"]
_CLEANUP_DIRS = [".mdpub"]


@pytest.fixture(scope="session", autouse=True)
def cleanup_artifacts():
    """Remove DB files and staging directories created during the test session."""
    yield
    for name in _CLEANUP_FILES:
        p = _PROJECT_ROOT / name
        if p.exists():
            p.unlink()
    for name in _CLEANUP_DIRS:
        p = _PROJECT_ROOT / name
        if p.exists():
            shutil.rmtree(p)
