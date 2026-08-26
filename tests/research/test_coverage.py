"""Tests for src.research.coverage (factor data coverage)."""
from src.research.coverage import FactorCoverageAnalyzer


def test_compute_coverage_full(store_dir, write_history):
    write_history("cov_factor", [1.0] * 30)
    a = FactorCoverageAnalyzer(store_dir=store_dir)
    res = a.compute_coverage("cov_factor", days=30)
    assert res["coverage_pct"] == 100.0
    assert res["status"] == "HIGH"
    assert res["actual_days"] == 30
    assert res["missing_pct"] == 0.0


def test_compute_coverage_low(store_dir, write_history):
    write_history("cov_factor", [1.0] * 10)
    a = FactorCoverageAnalyzer(store_dir=store_dir)
    res = a.compute_coverage("cov_factor", days=30)
    assert res["status"] == "LOW"
    assert res["actual_days"] == 10
