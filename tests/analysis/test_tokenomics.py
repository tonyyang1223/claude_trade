"""Tests for the new evaluation-dimension scoring functions (tokenomics)."""
import pytest

import src.analysis.tokenomics as tx
from src.analysis.tokenomics import (
    score_tokenomics,
    score_valuation,
    score_peg_stability,
    score_narrative,
    score_tvl_momentum,
    _band,
)


class _Snap:
    """Duck-typed snapshot for the scoring functions."""
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_score_tokenomics_none_when_all_missing():
    assert score_tokenomics(_Snap()) is None
    assert score_tokenomics(None) is None


def test_score_tokenomics_healthy_supply():
    s = _Snap(circulating_ratio=0.95, dilution_multiple=1.1, locked_ratio=0.05)
    score = score_tokenomics(s)
    assert isinstance(score, int)
    assert 1 <= score <= 5
    assert score >= 4  # very healthy supply picture


def test_score_tokenomics_dilutive_supply():
    s = _Snap(circulating_ratio=0.2, dilution_multiple=20, locked_ratio=0.8)
    score = score_tokenomics(s)
    assert score <= 2  # heavy unlock / dilution risk


def test_score_valuation_none_when_missing():
    assert score_valuation(_Snap()) is None


def test_score_valuation_fdvmc():
    s = _Snap(fdv_mc_ratio=1.1)
    score = score_valuation(s)
    assert score == 5  # very low dilution premium


def test_score_peg_stability_on_peg():
    assert score_peg_stability(price=1.0, target=1.0) == 5
    # 0.999 sits right at the 0.1% boundary (float-ambiguous) -> still "on peg".
    assert score_peg_stability(price=0.999, target=1.0) >= 4


def test_score_peg_stability_off_peg():
    score = score_peg_stability(price=0.90, target=1.0)
    assert score <= 2


def test_score_peg_stability_reserve_downgrade():
    tight = score_peg_stability(price=0.99, target=1.0, reserve_ratio=0.5)
    assert tight <= 4


def test_score_narrative_none_when_missing():
    assert score_narrative() is None


def test_score_narrative_reddit_mentions():
    # log10 scale: 1e4 mentions -> level 4 -> +1 = 5 (capped)
    assert score_narrative(reddit_mentions=10000) == 5
    assert score_narrative(reddit_mentions=10) == 2


def test_score_tvl_momentum_none_when_missing():
    assert score_tvl_momentum(_Snap()) is None


def test_score_tvl_momentum_positive():
    assert score_tvl_momentum(_Snap(tvl_change_7d=20.0)) == 5
    assert score_tvl_momentum(_Snap(tvl_change_7d=-20.0)) <= 2


def test_band_helper():
    # ascending: higher value -> higher score
    assert _band(10, [(5, 5), (1, 3)], 1) == 5
    # descending: value within range maps to the matching threshold
    assert _band(7, [(5, 5), (10, 3)], 1, ascending=False) == 3
    assert _band(2, [(5, 5), (10, 3)], 1, ascending=False) == 5
    # below all thresholds -> default
    assert _band(0.1, [(5, 5), (1, 3)], 1) == 1
