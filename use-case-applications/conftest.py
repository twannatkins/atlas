"""
Root conftest for use-case-applications tests.

Each Lambda handler has a unique module name (e.g., wealth_signal_detector.py,
atlas_sparql_mcp.py) so there are no import collisions. This conftest ensures
each test directory is on sys.path so imports resolve correctly.
"""

import sys
import os

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collectstart(collector):
    """Ensure each test directory is on sys.path for local imports."""
    if not hasattr(collector, "fspath"):
        return

    fspath = str(collector.fspath)
    if not fspath.endswith(".py") or not os.path.basename(fspath).startswith("test_"):
        return

    test_dir = os.path.dirname(fspath)
    if test_dir not in sys.path:
        sys.path.insert(0, test_dir)
