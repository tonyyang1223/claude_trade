"""Tests for src.research.retirement (recommendation decision logic)."""
from src.research.retirement import FactorRetirementAdvisor


def test_get_recommendation_immediate_low_score(store_dir):
    a = FactorRetirementAdvisor(store_dir=store_dir)
    r = a._get_recommendation(30, [], [])
    assert r["action"] == "IMMEDIATE_RETIREMENT"
    assert r["should_retire"] is True


def test_get_recommendation_immediate_critical(store_dir):
    a = FactorRetirementAdvisor(store_dir=store_dir)
    r = a._get_recommendation(50, ["crit"], [])
    assert r["action"] == "IMMEDIATE_RETIREMENT"


def test_get_recommendation_review(store_dir):
    a = FactorRetirementAdvisor(store_dir=store_dir)
    r = a._get_recommendation(50, [], ["w"])
    assert r["action"] == "REVIEW_FOR_RETIREMENT"


def test_get_recommendation_watch(store_dir):
    a = FactorRetirementAdvisor(store_dir=store_dir)
    r = a._get_recommendation(70, [], ["w"])
    assert r["action"] == "MONITOR_CLOSELY"


def test_get_recommendation_keep(store_dir):
    a = FactorRetirementAdvisor(store_dir=store_dir)
    r = a._get_recommendation(80, [], [])
    assert r["action"] == "KEEP_ACTIVE"
