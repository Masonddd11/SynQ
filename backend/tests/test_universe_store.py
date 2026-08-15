"""
tests/test_universe_store.py — Tests for state/universe.py persistence.

Covers round-trip save/load, empty (no-restriction) default, normalization,
corrupt-file resilience, and path injection.
"""

from __future__ import annotations

import json

from state.universe import UniverseStore


def test_default_load_is_empty(tmp_path):
    s = UniverseStore(tmp_path / "universe.json")
    doc = s.load()
    assert doc == {"symbols": [], "updated_at": ""}
    assert s.symbols() == []


def test_roundtrip_save_load(tmp_path):
    s = UniverseStore(tmp_path / "universe.json")
    saved = s.save(["AAPL", "MSFT", "IREN"])
    assert saved["symbols"] == ["AAPL", "MSFT", "IREN"]
    assert saved["updated_at"]

    # Fresh store instance reads the same file back.
    s2 = UniverseStore(tmp_path / "universe.json")
    assert s2.load()["symbols"] == ["AAPL", "MSFT", "IREN"]


def test_save_normalizes_dedupes_and_normalizes_case(tmp_path):
    s = UniverseStore(tmp_path / "universe.json")
    saved = s.save(["aapl", "AAPL", " msft ", "", " NBIS "])
    assert saved["symbols"] == ["AAPL", "MSFT", "NBIS"]


def test_empty_save_means_unrestricted(tmp_path):
    s = UniverseStore(tmp_path / "universe.json")
    s.save([])
    assert s.load()["symbols"] == []


def test_corrupt_file_falls_back_to_empty(tmp_path):
    p = tmp_path / "universe.json"
    p.write_text("not json{{{", encoding="utf-8")
    s = UniverseStore(p)
    assert s.load() == {"symbols": [], "updated_at": ""}
    assert s.symbols() == []


def test_symbols_field_type_mismatch_falls_back_to_empty(tmp_path):
    p = tmp_path / "universe.json"
    p.write_text(json.dumps({"symbols": "not-a-list"}), encoding="utf-8")
    s = UniverseStore(p)
    assert s.symbols() == []


def test_root_dir_created_on_save(tmp_path):
    nested = tmp_path / "does" / "not" / "exist" / "universe.json"
    s = UniverseStore(nested)
    s.save(["AAPL"])
    assert nested.exists()
