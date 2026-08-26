"""Tests for src.research.health_dashboard (status/recommendation logic)."""
from src.research.health_dashboard import FactorHealthDashboard


def test_determine_status_disabled(store_dir):
    a = FactorHealthDashboard(store_dir=store_dir)
    assert a._determine_status(10, {"status": "GOOD"}, {"coverage_pct": 100}) == "DISABLED"


def test_determine_status_deprecated(store_dir):
    a = FactorHealthDashboard(store_dir=store_dir)
    assert a._determine_status(90, {"status": "DEAD_FACTOR"}, {"coverage_pct": 100}) == "DEPRECATED"


def test_determine_status_watchlist_coverage(store_dir):
    a = FactorHealthDashboard(store_dir=store_dir)
    s = a._determine_status(90, {"status": "GOOD", "entropy": 3.0}, {"coverage_pct": 10})
    assert s == "WATCHLIST"


def test_determine_status_active(store_dir):
    a = FactorHealthDashboard(store_dir=store_dir)
    s = a._determine_status(90, {"status": "GOOD", "entropy": 3.0}, {"coverage_pct": 100})
    assert s == "ACTIVE"


def test_generate_recommendation_keep(store_dir):
    a = FactorHealthDashboard(store_dir=store_dir)
    rec = a._generate_recommendation(80, {"status": "GOOD", "entropy": 3.0}, {"coverage_pct": 100})
    assert "KEEP" in rec


def test_generate_recommendation_monitor(store_dir):
    a = FactorHealthDashboard(store_dir=store_dir)
    rec = a._generate_recommendation(40, {"status": "GOOD", "entropy": 3.0}, {"coverage_pct": 100})
    assert "MONITOR" in rec
