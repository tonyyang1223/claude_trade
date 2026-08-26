"""Tests for src.research.database (DuckDB research store).

Safe-degradation path is always exercised; the SQL path runs only when the
optional `duckdb` package is installed.
"""
from pathlib import Path

from src.research.database import FactorDatabase, HAS_DUCKDB


def test_instantiates(tmp_path):
    db = FactorDatabase(db_path=tmp_path / "x.duckdb")
    assert db is not None


def test_degrades_without_connection(tmp_path, monkeypatch):
    db = FactorDatabase(db_path=tmp_path / "x.duckdb")
    monkeypatch.setattr(db, "conn", None)
    assert db.query("SELECT 1") == []
    assert db.get_stats() == {"status": "duckdb_not_available"}
    assert db.load_from_store() == 0


def test_load_and_query_sql(tmp_path):
    if not HAS_DUCKDB:
        import pytest

        pytest.skip("duckdb not installed")
    from datetime import date, timedelta

    from src.factors.store import FactorStore

    db = FactorDatabase(db_path=tmp_path / "x.duckdb")
    store = FactorStore(base_dir=tmp_path / "factors")
    today = date.today()
    for i in range(3):
        d = (today - timedelta(days=i)).isoformat()
        store.save_factors(
            d,
            {
                "fA": {
                    "raw_value": float(i),
                    "normalized_value": float(i),
                    "score": int(i),
                    "confidence": 0.9,
                }
            },
        )
    db.store = store
    n = db.load_from_store(days=5)
    assert n == 3
    assert len(db.get_factor_series("fA")) == 3
    assert "fA" in db.get_latest_factors()
    assert db.get_stats()["total_records"] == 3
    db.close()
