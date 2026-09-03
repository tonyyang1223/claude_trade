"""Tests for token type classification (src.research.token_classification)."""
import pytest

from src.research.token_classification import (
    classify_coin,
    classify_coin_detailed,
    label_of,
    ALL_TOKEN_TYPES,
    CATEGORY_PRIORITY,
    TYPE_LABELS,
)


def test_all_token_types_count():
    # 27 distinguishable types + the implicit "unclassified" fallback.
    assert len(ALL_TOKEN_TYPES) == 27
    assert "unclassified" not in ALL_TOKEN_TYPES
    assert len(CATEGORY_PRIORITY) == 28  # 27 + unclassified


def test_known_categories_map_correctly():
    assert classify_coin(["Layer 1"]) == "layer-1"
    assert classify_coin(["Decentralized Finance (DeFi)"]) == "defi"
    assert classify_coin(["Meme"]) == "meme"
    assert classify_coin(["Stablecoin"]) == "stablecoin"
    assert classify_coin(["Real World Assets"]) == "rwa"
    assert classify_coin(["Artificial Intelligence"]) == "ai"


def test_chainlink_ai_bug_is_fixed():
    # Regression: 'Chainlink' must NOT match 'ai' (substring of "chAInlInk").
    assert classify_coin(["Chainlink"]) == "unclassified"
    assert classify_coin(["Oracle"]) == "oracle"
    assert classify_coin(["AI", "Oracle"]) == "ai"  # 'ai' outranks 'oracle'


def test_word_boundary_prevents_false_positive():
    # 'ai' only fires as a standalone token, not inside other words.
    assert classify_coin(["chainlink"]) == "unclassified"
    assert classify_coin(["email token"]) == "unclassified"
    assert classify_coin(["AI & Data"]) == "ai"


def test_priority_picks_highest_match():
    # When multiple categories match, the highest-priority one wins.
    # CATEGORY_PRIORITY starts: stablecoin, defi, layer-1, layer-2, meme, ...
    assert classify_coin(["Meme", "DeFi"]) == "defi"      # defi before meme
    assert classify_coin(["Gaming", "Meme"]) == "meme"    # meme before gaming
    assert classify_coin(["Layer 1", "DeFi"]) == "defi"   # defi before layer-1


def test_usdc_not_misclassified_as_layer2():
    # Regression for the USDC bug: it carries "Morph L2 Ecosystem" plus a
    # cluster of stablecoin tags. It must resolve to stablecoin, never
    # layer-2.
    usdc_cats = [
        "Stablecoins", "USD Stablecoin", "Fiat-backed Stablecoin",
        "Morph L2 Ecosystem", "Yield", "Portfolio", "Real World Assets",
    ]
    assert classify_coin(usdc_cats) == "stablecoin"


def test_ecosystem_tag_does_not_pull_network_slug():
    # "X Ecosystem" tags must not imply a network-layer type.
    assert classify_coin(["Morph L2 Ecosystem"]) == "unclassified"
    assert classify_coin(["BNB Chain Ecosystem"]) == "unclassified"
    # A real type alongside the ecosystem tag still wins.
    assert classify_coin(["Morph L2 Ecosystem", "Meme"]) == "meme"
    assert classify_coin(["Morph L2 Ecosystem", "Stablecoins"]) == "stablecoin"


def test_stablecoin_outranks_network_layers():
    # A stablecoin tagged with network-layer categories stays a stablecoin.
    assert classify_coin(["Stablecoin", "Layer 1"]) == "stablecoin"
    assert classify_coin(["Stablecoin", "Layer 2"]) == "stablecoin"
    assert classify_coin(["Stablecoin", "DeFi"]) == "stablecoin"


def test_empty_and_none_fallback():
    assert classify_coin([]) == "unclassified"
    assert classify_coin(None) == "unclassified"
    assert classify_coin(["Unknown Category"]) == "unclassified"


def test_detailed_match_fields():
    m = classify_coin_detailed(["Layer 1", "Smart Contract Platform"])
    assert m.primary == "layer-1"
    assert m.is_fallback is False
    assert "layer-1" in m.all_matched
    assert m.raw_categories == ["Layer 1", "Smart Contract Platform"]
    assert m.label == "Layer-1 公链"


def test_detailed_fallback_flag():
    m = classify_coin_detailed(["Totally Unknown"])
    assert m.primary == "unclassified"
    assert m.is_fallback is True


def test_label_of():
    assert label_of("layer-1") == "Layer-1 公链"
    assert label_of("meme") == "Meme 币"
    # Unknown slug falls back to the slug itself.
    assert label_of("does-not-exist") == "does-not-exist"


def test_every_type_has_a_label():
    for t in ALL_TOKEN_TYPES + ["unclassified"]:
        assert t in TYPE_LABELS
