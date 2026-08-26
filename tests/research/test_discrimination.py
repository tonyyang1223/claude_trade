"""Tests for src.research.discrimination (pure functions + store-backed analysis)."""
import numpy as np

from src.research.discrimination import FactorDiscriminationAnalyzer


def _analyzer(store_dir):
    return FactorDiscriminationAnalyzer(store_dir=store_dir)


def test_compute_unique_count_basic(store_dir):
    assert _analyzer(store_dir).compute_unique_count([1.0, 1.0, 2.0, 3.0]) == 3


def test_compute_unique_count_empty(store_dir):
    assert _analyzer(store_dir).compute_unique_count([]) == 0


def test_compute_unique_count_rounding(store_dir):
    assert _analyzer(store_dir).compute_unique_count([1.0, 1.0000001, 1.0]) == 1


def test_compute_entropy_constant_is_zero(store_dir):
    assert _analyzer(store_dir).compute_entropy([5.0, 5.0, 5.0]) == 0.0


def test_compute_entropy_empty_is_zero(store_dir):
    assert _analyzer(store_dir).compute_entropy([]) == 0.0


def test_compute_entropy_spread_is_high(store_dir):
    vals = [float(i) for i in range(20)]
    assert _analyzer(store_dir).compute_entropy(vals, bins=10) > 2.0


def test_compute_variance(store_dir):
    a = _analyzer(store_dir)
    assert abs(a.compute_variance([1.0, 2.0, 3.0]) - float(np.var([1.0, 2.0, 3.0]))) < 1e-9


def test_compute_variance_insufficient_returns_zero(store_dir):
    assert _analyzer(store_dir).compute_variance([1.0]) == 0.0


def test_analyze_dead_factor_constant(store_dir, write_history):
    write_history("df_factor", [1.0] * 10)
    res = _analyzer(store_dir).analyze_factor_discrimination("df_factor", days=10)
    assert res["status"] == "DEAD_FACTOR"
    assert res["variance"] == 0.0


def test_analyze_good_factor_varied(store_dir, write_history):
    write_history("df_factor", [float(i) for i in range(10)])
    res = _analyzer(store_dir).analyze_factor_discrimination("df_factor", days=10)
    assert res["status"] == "GOOD"
    assert res["unique_count"] == 10
    assert res["days_analyzed"] == 10


def test_analyze_no_data(store_dir):
    res = _analyzer(store_dir).analyze_factor_discrimination("missing_factor", days=5)
    assert res["status"] == "NO_DATA"
