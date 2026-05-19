"""
Root conftest for use-case-applications tests.

Uses pytest_collect_file to ensure each test directory's handler module
is importable without namespace collisions.
"""

import sys
import os

import pytest


def pytest_collect_file(parent, file_path):
    """Before collecting a test file, reset handler module cache."""
    if file_path.suffix == ".py" and file_path.name.startswith("test_"):
        test_dir = str(file_path.parent)

        # Clear cached handler modules
        for mod_name in list(sys.modules.keys()):
            if mod_name in ("handler", "register", "select_advisor",
                            "validate_routing", "write_routing_decision",
                            "notify_advisor", "audit_write"):
                del sys.modules[mod_name]

        # Put this test's directory first on sys.path
        if test_dir in sys.path:
            sys.path.remove(test_dir)
        sys.path.insert(0, test_dir)
