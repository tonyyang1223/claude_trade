"""Tests for src.research.correlation (inject _factor_data to avoid IO)."""
from datetime import date, timedelta

import pandas as pd

from src.research.correlation import FactorCorrelationAnalyzer


def _inject(analyzer, series_a, series_b):
    today = date.today()
    d0 = today.isoformat()
    d1 = (today - timedelta(days=1)).isoformat()
    rows = []
    for d, va, vb in [(d0, series_a[0], series_b[0]), (d1, series_a[1], series_b[1])]:
        rows.append({"date": d, "factor_name": "fA", "raw_value": va, "normalized_value": va, "score": va})
        rows.append({"date": d, "factor_name": "fB", "raw_value": vb, "normalized_value": vb, "score": vb})
    analyzer._factor_data = pd.DataFrame(rows)


def test_compute_correlation_matrix(store_dir):
    a = FactorCorrelationAnalyzer(store_dir=store_dir)
    _inject(a, [1.0, 2.0], [1.0, 2.0])
    mat = a.compute_correlation_matrix(days=30)
    assert list(mat.columns) == ["fA", "fB"]
    assert mat.loc["fA", "fB"] == 1.0


def test_find_high_correlations(store_dir):
    a = FactorCorrelationAnalyzer(store_dir=store_dir)
    _inject(a, [1.0, 2.0], [1.0, 2.0])
    high = a.find_high_correlations(threshold=0.85, days=30)
    assert len(high) == 1
    assert high[0]["abs_correlation"] == 1.0


def test_compute_correlation_matrix_invalid_method(store_dir):
    a = FactorCorrelationAnalyzer(store_dir=store_dir)
    _inject(a, [1.0, 2.0], [3.0, 4.0])
    try:
        a.compute_correlation_matrix(days=30, method="invalid")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_rolling_correlation_returns_series(store_dir):
    a = FactorCorrelationAnalyzer(store_dir=store_dir)
    _inject(a, [1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
    ser = a.compute_rolling_correlation("fA", "fB", window=2)
    assert isinstance(ser, pd.Series)


def test_category_correlation_returns_dataframe(store_dir):
    a = FactorCorrelationAnalyzer(store_dir=store_dir)
    _inject(a, [1.0, 2.0], [1.0, 2.0])
    cat = a.compute_category_correlation(days=30)
    assert isinstance(cat, pd.DataFrame)
