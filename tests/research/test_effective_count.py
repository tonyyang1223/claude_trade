"""Tests for src.research.effective_count (effective factor count, N_eff)."""
from src.research.effective_count import EffectiveFactorCountAnalyzer


def test_compute_effective_count_two_equal():
    a = EffectiveFactorCountAnalyzer()
    r = a.compute_effective_count({"a": 1.0, "b": 1.0})
    assert r["total_factors"] == 2
    assert r["effective_count"] == 2.0
    assert r["redundancy_ratio"] == 0.0
    assert "GOOD" in r["interpretation"]


def test_compute_effective_count_redundant():
    a = EffectiveFactorCountAnalyzer()
    r = a.compute_effective_count({"a": 100.0, "b": 1.0, "c": 1.0, "d": 1.0})
    assert r["effective_count"] < r["total_factors"]
    assert r["redundancy_ratio"] > 0.0


def test_compute_effective_count_empty():
    a = EffectiveFactorCountAnalyzer()
    r = a.compute_effective_count({})
    assert r["total_factors"] == 0
    assert r["effective_count"] == 0.0
    assert r["redundancy_ratio"] == 0.0


def test_interpret_branches():
    a = EffectiveFactorCountAnalyzer()
    assert "GOOD" in a._interpret(10, 9)              # ratio 0.9
    assert "MODERATE" in a._interpret(10, 7)          # ratio 0.7
    assert "HIGH_REDUNDANCY" in a._interpret(10, 5)   # ratio 0.5
    assert "CRITICAL" in a._interpret(10, 2)          # ratio 0.2


def test_recommendation_well_diversified():
    a = EffectiveFactorCountAnalyzer()
    assert "well-diversified" in a._recommendation({"effective_count": 9, "total_factors": 10})


def test_recommendation_reduce():
    a = EffectiveFactorCountAnalyzer()
    assert "reducing" in a._recommendation({"effective_count": 2, "total_factors": 10})
