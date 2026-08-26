"""Shared fixtures for src.research tests.

Provides an isolated FactorStore (backed by tmp_path) so analyzer tests can
inject synthetic factor history without touching the real filesystem or network.
"""
import pytest
from datetime import date, timedelta
from pathlib import Path

from src.factors.store import FactorStore


@pytest.fixture
def store_dir(tmp_path) -> Path:
    """Isolated factor store directory."""
    return tmp_path / "factors"


@pytest.fixture
def factor_store(store_dir) -> FactorStore:
    return FactorStore(base_dir=store_dir)


@pytest.fixture
def write_history(factor_store):
    """Return a helper that writes synthetic factor history for the last `days` days.

    Dates are anchored to date.today() (matching FactorStore.get_factor_history),
    so analyzers reading `days` back will pick the data up.
    """

    def _write(factor_name: str, values, days: int = None, fields: dict = None):
        if days is None:
            days = len(values) if values else 10
        today = date.today()
        for i in range(days):
            d = (today - timedelta(days=i)).isoformat()
            val = float(values[i]) if i < len(values) else 0.0
            rec = {
                "raw_value": val,
                "normalized_value": val,
                "score": val,
                "confidence": 0.9,
            }
            if fields:
                rec.update(fields)
            factor_store.save_factors(d, {factor_name: rec})

    return _write
