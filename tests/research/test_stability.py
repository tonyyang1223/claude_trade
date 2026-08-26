"""Tests for src.research.stability (volatility / stability / health)."""
from src.research.stability import FactorStabilityAnalyzer


def test_compute_volatility_no_data(store_dir):
    a = FactorStabilityAnalyzer(store_dir=store_dir)
    assert a.compute_volatility("missing", days=30) == 0.0


def test_compute_stability_score_few_points(store_dir, write_history):
    write_history("st_factor", [1.0, 2.0, 3.0])
    a = FactorStabilityAnalyzer(store_dir=store_dir)
    assert a.compute_stability_score("st_factor", days=5) == 50.0


def test_compute_stability_score_constant(store_dir, write_history):
    write_history("st_factor", [5.0] * 10)
    a = FactorStabilityAnalyzer(store_dir=store_dir)
    assert a.compute_stability_score("st_factor", days=10) == 100.0


def test_analyze_health_constant(store_dir, write_history):
    write_history("st_factor", [5.0] * 10)
    a = FactorStabilityAnalyzer(store_dir=store_dir)
    res = a.analyze_factor_health("st_factor", days=10)
    assert res["health_status"] == "healthy"
    assert res["health_score"] == 100.0


def test_analyze_health_no_data(store_dir):
    a = FactorStabilityAnalyzer(store_dir=store_dir)
    res = a.analyze_factor_health("missing", days=30)
    assert res["health_status"] in ("moderate", "degraded")
