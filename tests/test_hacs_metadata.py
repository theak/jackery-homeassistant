"""Regression tests for HACS packaging metadata."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HACS_MANIFEST = REPO_ROOT / "hacs.json"
INTEGRATION_HACS_MANIFEST = REPO_ROOT / "custom_components" / "jackery" / "hacs.json"
INTEGRATION_MANIFEST = REPO_ROOT / "custom_components" / "jackery" / "manifest.json"


def _load_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_hacs_manifest_exists_at_repository_root() -> None:
    assert HACS_MANIFEST.is_file()
    assert not INTEGRATION_HACS_MANIFEST.exists()


def test_hacs_manifest_declares_supported_home_assistant_version() -> None:
    hacs_manifest = _load_json(HACS_MANIFEST)

    assert hacs_manifest["name"] == "Jackery"
    assert hacs_manifest["homeassistant"] == "2023.8.0"


def test_manifest_version_is_bumped_past_broken_release() -> None:
    manifest = _load_json(INTEGRATION_MANIFEST)

    assert manifest["version"] == "1.1.0"
    assert manifest["homeassistant"] == "2023.8.0"
