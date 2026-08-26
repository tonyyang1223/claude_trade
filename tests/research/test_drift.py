"""Tests for src.research.drift (alert-level mapping + store-backed drift/trend)."""
from src.research.drift import FactorDriftAnalyzer


def test_alert_level_mapping(store_dir):
    a = FactorDriftAnalyzer(store_dir=store_dir)
    assert a._get_alert_level("SEVERE_DRIFT") == "HIGH"
    assert a._get_alert_level("MODERATE_DRIFT") == "MEDIUM"
    assert a._get_alert_level("MINOR_DRIFT") == "LOW"
    assert a._get_alert_level("STABLE") == "NONE"


def test_compute_baseline_no_data(store_dir):
    a = FactorDriftAnalyzer(store_dir=store_dir)
    base = a.compute_baseline("missing_factor", days=30)
    assert base == {"mean": 0.5, "std": 0.1, "min": 0.0, "max": 1.0}


def test_compute_drift_stable(store_dir, write_history):
    write_history("dr_factor", [5.0] * 30)
    a = FactorDriftAnalyzer(store_dir=store_dir)
    res = a.compute_drift("dr_factor", days=30)
    assert res["drift_status"] == "STABLE"
    assert res["drift_direction"] == "FLAT"
    assert abs(res["drift_zscore"]) < 0.5


def test_compute_trend_upward(store_dir, write_history):
    write_history("dr_factor", [float(i) for i in range(30)])
    a = FactorDriftAnalyzer(store_dir=store_dir)
    res = a.compute_trend("dr_factor", days=30)
    assert res["trend_direction"] == "UP"
    assert res["trend_slope"] > 0
    assert res["days_analyzed"] == 30


def test_compute_trend_insufficient(store_dir, write_history):
    write_history("dr_factor", [1.0, 2.0, 3.0])
    a = FactorDriftAnalyzer(store_dir=store_dir)
    res = a.compute_trend("dr_factor", days=5)
    assert res["trend_direction"] == "INSUFFICIENT_DATA"
