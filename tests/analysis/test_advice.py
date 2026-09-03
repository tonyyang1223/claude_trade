"""Tests for the research-oriented advice layer (src.analysis.advice)."""
import pytest

from src.analysis.advice import (
    DISCLAIMER,
    Advice,
    apply_coverage_cap,
    build_advice,
    position_band,
)


def test_disclaimer_present_and_carries_red_line():
    assert isinstance(DISCLAIMER, str)
    assert "不构成任何投资建议" in DISCLAIMER
    assert "风险自担" in DISCLAIMER


def test_advice_always_carries_disclaimer():
    a = build_advice("A+", "low", 1.0)
    assert a.disclaimer == DISCLAIMER


def test_apply_coverage_cap_low_coverage_caps_to_c():
    # coverage < 0.40 -> cannot exceed C.
    assert apply_coverage_cap("A+", 0.30) == "C"
    assert apply_coverage_cap("B", 0.30) == "C"


def test_apply_coverage_cap_mid_coverage_caps_to_b():
    # 0.40 <= coverage < 0.60 -> cannot exceed B.
    assert apply_coverage_cap("A+", 0.50) == "B"
    assert apply_coverage_cap("C", 0.50) == "C"  # B->C? no: C stays C


def test_apply_coverage_cap_high_coverage_preserves_rating():
    assert apply_coverage_cap("A+", 0.80) == "A+"
    assert apply_coverage_cap("B", 0.65) == "B"


def test_position_band_matrix():
    assert position_band("A+", "low") == (8, 12)
    assert position_band("A+", "high") == (3, 5)
    assert position_band("C", "high") == (0, 0)
    assert position_band("D", "low") == (0, 0)


def test_build_advice_caps_position_by_profile_max():
    # A+ low would suggest 8-12%, but a meme's max is 3% -> capped.
    from src.analysis.profiles import get_profile
    meme = get_profile("meme")
    a = build_advice("A+", "low", 1.0, profile=meme)
    assert a.position_max_pct <= meme.max_position_pct
    # Band string reflects the cap (single token -> "N%" style or range).
    assert "%" in a.position_range


def test_build_advice_zero_band_for_weak_rating():
    a = build_advice("D", "high", 1.0)
    assert a.position_range == "0%"
    assert a.action == "回避"
