"""Tests for src.research.ranking (IC / turnover / persistence)."""
from src.research.ranking import FactorRanking


def test_compute_ic_insufficient(store_dir, write_history):
    write_history("rk_factor", [1.0] * 5)
    a = FactorRanking(store_dir=store_dir)
    assert a.compute_ic("rk_factor") == 0.0


def test_compute_ic_constant_nan_fallback(store_dir, write_history):
    write_history("rk_factor", [5.0] * 30)
    a = FactorRanking(store_dir=store_dir)
    assert a.compute_ic("rk_factor") == 0.0


def test_compute_ic_strong(store_dir, write_history):
    write_history("rk_factor", [float(i) for i in range(30)])
    a = FactorRanking(store_dir=store_dir)
    assert a.compute_ic("rk_factor") > 0.9


def test_compute_turnover_constant(store_dir, write_history):
    write_history("rk_factor", [5.0] * 30)
    a = FactorRanking(store_dir=store_dir)
    assert a.compute_turnover("rk_factor", days=30) == 0.0


def test_compute_turnover_changing(store_dir, write_history):
    write_history("rk_factor", [float(i) for i in range(30)])
    a = FactorRanking(store_dir=store_dir)
    assert a.compute_turnover("rk_factor", days=30) == 1.0


def test_compute_persistence_strong(store_dir, write_history):
    write_history("rk_factor", [float(i) for i in range(30)])
    a = FactorRanking(store_dir=store_dir)
    assert a.compute_persistence("rk_factor") > 0.9
