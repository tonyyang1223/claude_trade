"""Tests for src.research.weighting (hierarchical factor weighting)."""
from src.research.weighting import HierarchicalWeighting


def test_normalize_weights():
    hw = HierarchicalWeighting()
    assert hw.normalize_weights({"a": 1.0, "b": 3.0}) == {"a": 25.0, "b": 75.0}


def test_normalize_weights_zero_total_returns_original():
    hw = HierarchicalWeighting()
    w = {"a": 0.0, "b": 0.0}
    assert hw.normalize_weights(w) == w


def test_get_factor_weight_known_factor():
    hw = HierarchicalWeighting(
        category_weights={"derivatives": 100.0},
        factor_weights={"derivatives": {"funding_rate": 100.0}},
    )
    # category_weight(100) * factor_weight(100)/100 = 100
    assert hw.get_factor_weight("funding_rate") == 100.0


def test_get_factor_weight_unknown_factor_is_zero():
    hw = HierarchicalWeighting()
    assert hw.get_factor_weight("nonexistent_factor_xyz") == 0.0


def test_compute_weighted_score_single():
    hw = HierarchicalWeighting(
        category_weights={"derivatives": 100.0},
        factor_weights={"derivatives": {"funding_rate": 100.0}},
    )
    assert hw.compute_weighted_score({"funding_rate": 0.8}) == 0.8


def test_compute_weighted_score_empty_is_zero():
    hw = HierarchicalWeighting()
    assert hw.compute_weighted_score({}) == 0.0


def test_apply_theme_weights():
    hw = HierarchicalWeighting()
    hw.apply_theme_weights("balanced")
    assert "momentum" in hw.category_weights
