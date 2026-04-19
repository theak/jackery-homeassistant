"""Regression tests for repository metadata used by HACS."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "custom_components" / "jackery" / "manifest.json"
README_PATH = REPO_ROOT / "README.md"
HACS_PATH = REPO_ROOT / "hacs.json"


class MetadataTests(unittest.TestCase):
    """Validate versioning and canonical repository links."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text())
        cls.hacs = json.loads(HACS_PATH.read_text())
        cls.readme = README_PATH.read_text()

    def test_manifest_points_to_current_repository(self) -> None:
        """Manifest links should resolve to this repository."""
        self.assertEqual(
            self.manifest["documentation"],
            "https://github.com/theak/jackery-homeassistant/blob/main/README.md",
        )
        self.assertEqual(
            self.manifest["issue_tracker"],
            "https://github.com/theak/jackery-homeassistant/issues",
        )
        self.assertEqual(self.manifest["codeowners"], ["@theak"])

    def test_readme_version_badge_matches_manifest(self) -> None:
        """README badge should advertise the same release as the manifest."""
        version = self.manifest["version"]
        self.assertIn(
            f"https://img.shields.io/badge/version-{version}-blue.svg",
            self.readme,
        )

    def test_hacs_default_branch_install_remains_enabled(self) -> None:
        """HACS should continue to offer the default branch between releases."""
        self.assertFalse(self.hacs["hide_default_branch"])
        self.assertIn(
            "HACS can also install the repository's default branch",
            self.readme,
        )

    def test_repository_files_do_not_reference_fork_links(self) -> None:
        """The published metadata should not point at the temporary contributor fork."""
        legacy_repo = "usersaynoso/jackery-homeassistant"
        checked_files = [
            MANIFEST_PATH,
            README_PATH,
            HACS_PATH,
        ]
        for file_path in checked_files:
            self.assertNotIn(legacy_repo, file_path.read_text(), str(file_path))


if __name__ == "__main__":
    unittest.main()
