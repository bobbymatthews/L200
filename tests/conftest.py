"""Pytest Configuration and Fixtures for OmniBlog."""

from __future__ import annotations

import pytest

from src.memory.store import BrandMemoryStore


@pytest.fixture(autouse=True)
def isolated_brand_memory(tmp_path, monkeypatch):
    """Ensure every test runs with an isolated temporary SQLite database and artifact folder."""
    db_file = tmp_path / "test_brand_memory.db"
    test_store = BrandMemoryStore(db_path=str(db_file))

    # Monkeypatch singleton brand_memory across modules
    monkeypatch.setattr("src.memory.store.brand_memory", test_store)
    monkeypatch.setattr("src.tools.memory_tools.brand_memory", test_store)
    monkeypatch.setattr("src.tools.artifact_tools.brand_memory", test_store)
    monkeypatch.setattr("src.api.brand_memory", test_store)
    monkeypatch.setattr("src.cli.brand_memory", test_store)

    # Monkeypatch artifacts directory
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    yield test_store
