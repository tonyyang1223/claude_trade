"""Tests for coin mappings configuration."""
import pytest


def test_coin_to_symbol_mapping():
    """Test coin to trading symbol mapping."""
    from src.data.coin_mappings import COIN_TO_SYMBOL

    assert COIN_TO_SYMBOL["bitcoin"] == "BTC/USDT"
    assert COIN_TO_SYMBOL["ethereum"] == "ETH/USDT"
    assert COIN_TO_SYMBOL["solana"] == "SOL/USDT"


def test_coin_to_repo_mapping():
    """Test coin to GitHub repo mapping."""
    from src.data.coin_mappings import COIN_TO_REPO

    assert COIN_TO_REPO["bitcoin"] == "bitcoin/bitcoin"
    assert COIN_TO_REPO["ethereum"] == "ethereum/go-ethereum"


def test_symbol_mapping_has_common_coins():
    """Test that common cryptocurrencies are mapped."""
    from src.data.coin_mappings import COIN_TO_SYMBOL

    common_coins = ["bitcoin", "ethereum", "solana", "cardano", "ripple"]
    for coin in common_coins:
        assert coin in COIN_TO_SYMBOL
        assert "USDT" in COIN_TO_SYMBOL[coin]


def test_repo_mapping_has_major_projects():
    """Test that major projects have GitHub repos mapped."""
    from src.data.coin_mappings import COIN_TO_REPO

    major_projects = ["bitcoin", "ethereum", "solana", "cardano"]
    for project in major_projects:
        assert project in COIN_TO_REPO
        assert "/" in COIN_TO_REPO[project]  # Format: owner/repo