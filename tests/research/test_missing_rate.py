"""Tests for src.research.missing_rate (quality score + coverage status)."""
from src.research.missing_rate import FactorMissingRateAnalyzer


def test_compute_quality_score_full(store_dir):
    a = FactorMissingRateAnalyzer(store_dir=store_dir)
    score = a._compute_quality_score(
        {"availability_rate": 1.0}, {"pattern": "CONTINUOUS", "max_gap": 0}
    )
    assert score == 100.0


def test_compute_quality_score_penalized(store_dir):
    a = FactorMissingRateAnalyzer(store_dir=store_dir)
    score = a._compute_quality_score(
        {"availability_rate": 0.5}, {"pattern": "SYSTEMATIC_LONG_GAP", "max_gap": 10}
    )
    assert score == 10.0  # 50 - 20 (pattern) - 20 (gap)


def test_compute_quality_score_zero(store_dir):
    a = FactorMissingRateAnalyzer(store_dir=store_dir)
    score = a._compute_quality_score(
        {"availability_rate": 0.0}, {"pattern": "CONTINUOUS", "max_gap": 0}
    )
    assert score == 0.0


def test_compute_missing_rate_full(store_dir, write_history):
    write_history("mr_factor", [1.0] * 30)
    a = FactorMissingRateAnalyzer(store_dir=store_dir)
    res = a.compute_missing_rate("mr_factor", days=30)
    assert res["missing_rate"] == 0.0
    assert res["availability_rate"] == 1.0
    assert res["status"] == "EXCELLENT"


def test_compute_missing_rate_partial(store_dir, write_history):
    write_history("mr_factor", [1.0] * 10)
    a = FactorMissingRateAnalyzer(store_dir=store_dir)
    res = a.compute_missing_rate("mr_factor", days=30)
    assert res["actual_days"] == 10
    assert res["status"] == "POOR"
