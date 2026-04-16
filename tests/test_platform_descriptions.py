"""Regression tests for platform description definitions."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

PLATFORM_FILES = ("switch.py", "select.py", "number.py")


class PlatformDescriptionTests(unittest.TestCase):
    """Ensure platform definitions keep using base EntityDescription objects."""

    def test_platform_files_construct_entity_description_instances(self) -> None:
        """Each platform should build plain EntityDescription values."""
        for filename in PLATFORM_FILES:
            with self.subTest(filename=filename):
                tree = ast.parse(
                    (REPO_ROOT / "custom_components" / "jackery" / filename).read_text()
                )
                constructor_calls = [
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "EntityDescription"
                ]
                self.assertTrue(constructor_calls)


if __name__ == "__main__":
    unittest.main()
