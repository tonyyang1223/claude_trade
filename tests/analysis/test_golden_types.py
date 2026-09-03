"""Golden integration test: classification -> profile -> valid evaluation config.

For a representative set of coins, verify that classify_coin maps to the right
type, and that the resolved profile is internally valid (weights sum to 1, has
applicable dimensions) so the typed scorer can consume it directly.
"""
import pytest

from src.research.token_classification import classify_coin, label_of
from src.analysis.profiles import get_profile, TYPE_PROFILES


GOLDEN = [
    # (coin_id, categories, expected_type, expected_label)
    ("bitcoin", ["Layer 1"], "layer-1", "Layer-1 公链"),
    ("ethereum", ["Layer 1", "Smart Contract Platform"], "layer-1", "Layer-1 公链"),
    ("uniswap", ["Decentralized Finance (DeFi)"], "defi", "DeFi"),
    ("aave", ["Decentralized Finance (DeFi)", "Lending"], "defi", "DeFi"),
    ("tether", ["Stablecoin"], "stablecoin", "稳定币"),
    ("dogecoin", ["Meme"], "meme", "Meme 币"),
    ("chainlink", ["Oracle"], "oracle", "预言机"),
    ("render-token", ["Artificial Intelligence"], "ai", "AI 概念"),
    ("decentraland", ["Gaming", "NFT"], "gaming", "GameFi"),
    ("oasis-network", ["Privacy"], "privacy", "隐私币"),
    ("ethena", ["Real World Assets"], "rwa", "RWA 真实资产"),
    ("ethereum-name-service", ["Exchange"], "exchange", "交易所平台币"),
]


@pytest.mark.parametrize("coin_id,cats,exp_type,exp_label", GOLDEN)
def test_classification_golden(coin_id, cats, exp_type, exp_label):
    assert classify_coin(cats) == exp_type
    assert label_of(exp_type) == exp_label


@pytest.mark.parametrize("coin_id,cats,exp_type,exp_label", GOLDEN)
def test_profile_resolves_and_is_valid(coin_id, cats, exp_type, exp_label):
    prof = get_profile(classify_coin(cats))
    assert prof.token_type == exp_type
    # Weights must sum to 1 (golden invariant for every profile).
    assert abs(sum(prof.weights.values()) - 1.0) < 1e-9
    # Every profile must have at least one applicable dimension.
    assert len(prof.applicable_dims) >= 1


def test_all_27_profiles_are_golden():
    # Each of the 27 type profiles resolves to a valid, unit-sum config.
    for token_type in TYPE_PROFILES:
        prof = get_profile(token_type)
        assert prof.token_type == token_type
        assert abs(sum(prof.weights.values()) - 1.0) < 1e-9
        assert len(prof.applicable_dims) >= 1
