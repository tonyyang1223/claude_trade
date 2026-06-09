"""Unit tests for factor multi-coin adaptation.

Tests:
1. resolve_chain - Chain resolution logic
2. TVL fallback - Protocol TVL fallback to chain TVL
3. Stablecoin flow chain-specific - Chain-level stablecoin data
4. FactorMetadata - New attributes (min_days, min_points)
5. Data quantity check - Historical data validation
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import math

from src.factors.onchain import (
    resolve_chain,
    compute_stablecoin_net_flow,
    compute_stablecoin_total_supply,
    compute_protocol_tvl,
    compute_tvl_change_7d
)
from src.factors.models import FactorMetadata, FactorCategory, FactorSource
from src.factors.engine import FactorEngine
from src.factors.registry import registry


# ============================================================================
# TestResolveChain - Chain Resolution Logic
# ============================================================================

class TestResolveChain:
    """Test chain resolution for coin IDs."""

    def test_resolve_chain_from_hardcoded_mapping(self):
        """Test resolving chain from hardcoded COIN_TO_CHAIN mapping."""
        # Ethereum L1
        result = resolve_chain("ethereum")
        assert result == "Ethereum"

        # Solana
        result = resolve_chain("solana")
        assert result == "Solana"

        # ERC-20 tokens should resolve to Ethereum
        result = resolve_chain("uniswap")
        assert result == "Ethereum"

        result = resolve_chain("aave")
        assert result == "Ethereum"

    def test_resolve_chain_for_l2_tokens(self):
        """Test resolving chain for L2 ecosystem tokens."""
        # Arbitrum
        result = resolve_chain("arbitrum")
        assert result == "Arbitrum"

        # Optimism
        result = resolve_chain("optimism")
        assert result == "Optimism"

    def test_resolve_chain_unknown_coin_without_api(self):
        """Test resolving chain for unknown coin (no hardcoded mapping)."""
        with patch('src.factors.onchain.CoinGeckoClient') as mock_client:
            # Mock API to return None (no platform)
            mock_instance = Mock()
            mock_instance.get_asset_platform.return_value = None
            mock_client.return_value = mock_instance

            result = resolve_chain("unknown-coin")
            assert result is None

    def test_resolve_chain_unknown_coin_with_api(self):
        """Test resolving chain via CoinGecko API for unknown coin."""
        with patch('src.factors.onchain.CoinGeckoClient') as mock_client:
            # Mock API to return platform
            mock_instance = Mock()
            mock_instance.get_asset_platform.return_value = "solana"
            mock_client.return_value = mock_instance

            result = resolve_chain("new-token")
            # Should capitalize and return
            assert result == "Solana"

    def test_resolve_chain_api_exception(self):
        """Test graceful handling when CoinGecko API fails."""
        with patch('src.factors.onchain.CoinGeckoClient') as mock_client:
            # Mock API to raise exception
            mock_instance = Mock()
            mock_instance.get_asset_platform.side_effect = Exception("API Error")
            mock_client.return_value = mock_instance

            result = resolve_chain("some-coin")
            assert result is None


# ============================================================================
# TestTvlFallback - TVL Fallback Logic
# ============================================================================

class TestTvlFallback:
    """Test TVL computation with fallback from protocol to chain."""

    def test_tvl_protocol_success(self):
        """Test TVL when protocol data is available."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client:
            mock_instance = Mock()
            mock_instance.get_protocol_tvl.return_value = {
                "tvl": 5e9,
                "tvl_change_7d": 10.0,
                "confidence": 0.9
            }
            mock_client.return_value = mock_instance

            result = compute_protocol_tvl("uniswap")
            assert result == 5e9
            assert not math.isnan(result)

    def test_tvl_fallback_to_chain(self):
        """Test TVL fallback to chain when protocol unavailable."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client, \
             patch('src.factors.onchain.resolve_chain') as mock_resolve:

            mock_instance = Mock()
            # Protocol TVL returns 0
            mock_instance.get_protocol_tvl.return_value = {"tvl": 0}
            # Chain TVL returns valid data
            mock_instance.get_chain_tvl.return_value = {
                "tvl": 30e9,
                "confidence": 0.9
            }
            mock_client.return_value = mock_instance
            mock_resolve.return_value = "Ethereum"

            result = compute_protocol_tvl("ethereum")
            # Should use chain TVL
            assert result == 30e9

    def test_tvl_no_data_available(self):
        """Test TVL returns NaN when no data available."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client, \
             patch('src.factors.onchain.resolve_chain') as mock_resolve:

            mock_instance = Mock()
            mock_instance.get_protocol_tvl.return_value = {"tvl": 0}
            mock_instance.get_chain_tvl.return_value = {"tvl": 0}
            mock_client.return_value = mock_instance
            mock_resolve.return_value = None

            result = compute_protocol_tvl("unknown-coin")
            assert math.isnan(result)

    def test_tvl_change_7d_fallback(self):
        """Test 7d TVL change with fallback."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client, \
             patch('src.factors.onchain.resolve_chain') as mock_resolve:

            mock_instance = Mock()
            # Protocol returns 0 TVL
            mock_instance.get_protocol_tvl.return_value = {
                "tvl": 0,
                "tvl_change_7d": 0
            }
            # Chain returns valid data
            mock_instance.get_chain_tvl.return_value = {
                "tvl": 50e9,
                "tvl_change_7d": 15.0,
                "confidence": 0.9
            }
            mock_client.return_value = mock_instance
            mock_resolve.return_value = "Solana"

            result = compute_tvl_change_7d("solana")
            # Should use chain TVL change
            assert result == 15.0


# ============================================================================
# TestStablecoinFlowChainSpecific - Chain-Level Stablecoin Data
# ============================================================================

class TestStablecoinFlowChainSpecific:
    """Test chain-specific stablecoin flow computation."""

    def test_stablecoin_flow_with_chain(self):
        """Test stablecoin net flow for chain-specific coin."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client, \
             patch('src.factors.onchain.resolve_chain') as mock_resolve:

            mock_instance = Mock()
            mock_instance.get_chain_stablecoin_flows.return_value = {
                "net_flows_24h": 500e6,
                "total_supply": 10e9,
                "confidence": 0.9
            }
            mock_client.return_value = mock_instance
            mock_resolve.return_value = "Ethereum"

            result = compute_stablecoin_net_flow("ethereum")
            assert result == 500e6

    def test_stablecoin_flow_global_fallback(self):
        """Test fallback to global stablecoin flow when chain unavailable."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client, \
             patch('src.factors.onchain.resolve_chain') as mock_resolve:

            mock_instance = Mock()
            mock_instance.get_chain_stablecoin_flows.return_value = {
                "net_flows_24h": 0,
                "confidence": 0.1
            }
            mock_instance.get_stablecoin_flows.return_value = {
                "net_flows_24h": 1e9,
                "confidence": 0.9
            }
            mock_client.return_value = mock_instance
            mock_resolve.return_value = None

            result = compute_stablecoin_net_flow("bitcoin")
            # Should use global fallback
            assert result == 1e9

    def test_stablecoin_supply_chain_specific(self):
        """Test stablecoin total supply for chain-specific coin."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client, \
             patch('src.factors.onchain.resolve_chain') as mock_resolve:

            mock_instance = Mock()
            mock_instance.get_chain_stablecoin_flows.return_value = {
                "total_supply": 5e9,
                "net_flows_24h": 100e6,
                "confidence": 0.9
            }
            mock_client.return_value = mock_instance
            mock_resolve.return_value = "Avalanche"

            result = compute_stablecoin_total_supply("avalanche-2")
            assert result == 5e9

    def test_stablecoin_supply_global_fallback(self):
        """Test fallback to global supply when chain unavailable."""
        with patch('src.factors.onchain.DefiLlamaClient') as mock_client, \
             patch('src.factors.onchain.resolve_chain') as mock_resolve:

            mock_instance = Mock()
            mock_instance.get_chain_stablecoin_flows.return_value = {
                "total_supply": 0,
                "confidence": 0.1
            }
            mock_instance.get_stablecoin_flows.return_value = {
                "total_supply": 150e9,
                "confidence": 0.9
            }
            mock_client.return_value = mock_instance
            mock_resolve.return_value = None

            result = compute_stablecoin_total_supply("dogecoin")
            # Should use global fallback
            assert result == 150e9


# ============================================================================
# TestFactorMetadata - Metadata New Attributes
# ============================================================================

class TestFactorMetadata:
    """Test FactorMetadata new attributes for multi-coin adaptation."""

    def test_metadata_min_days_attribute(self):
        """Test min_days attribute in FactorMetadata."""
        metadata = FactorMetadata(
            name="test_factor",
            display_name="Test Factor",
            category=FactorCategory.ONCHAIN,
            source=FactorSource.DEFILLAMA,
            min_days=7
        )
        assert metadata.min_days == 7

    def test_metadata_min_points_attribute(self):
        """Test min_points attribute in FactorMetadata."""
        metadata = FactorMetadata(
            name="test_factor",
            display_name="Test Factor",
            category=FactorCategory.TECHNICAL,
            source=FactorSource.BINANCE,
            min_points=30
        )
        assert metadata.min_points == 30

    def test_metadata_defaults(self):
        """Test default values for min_days and min_points."""
        metadata = FactorMetadata(
            name="test_factor",
            display_name="Test Factor",
            category=FactorCategory.MARKET,
            source=FactorSource.COINGECKO
        )
        # Defaults should be 0
        assert metadata.min_days == 0
        assert metadata.min_points == 0

    def test_metadata_to_dict_includes_new_attributes(self):
        """Test that to_dict() includes min_days and min_points."""
        metadata = FactorMetadata(
            name="tvl_change_7d",
            display_name="TVL Change 7d",
            category=FactorCategory.ONCHAIN,
            source=FactorSource.DEFILLAMA,
            min_days=7,
            min_points=30
        )
        dict_result = metadata.to_dict()
        assert "min_days" in dict_result
        assert dict_result["min_days"] == 7
        assert "min_points" in dict_result
        assert dict_result["min_points"] == 30

    def test_registered_factor_has_metadata(self):
        """Test that registered factors have complete metadata."""
        # Force discover factors
        registry.discover_factors()

        # Check stablecoin_net_flow metadata
        metadata = registry.get_factor("stablecoin_net_flow")
        if metadata:
            assert metadata.min_days == 1
            assert metadata.min_points == 7


# ============================================================================
# TestDataQuantityCheck - Historical Data Validation
# ============================================================================

class TestDataQuantityCheck:
    """Test data quantity checking in FactorEngine."""

    def test_insufficient_data_points(self):
        """Test that insufficient data points returns NaN."""
        engine = FactorEngine()
        engine.discover_factors()

        # Mock compute function
        with patch.object(registry, 'get_compute_func') as mock_func:
            mock_func.return_value = lambda: 100.0

            metadata = FactorMetadata(
                name="test_factor",
                display_name="Test Factor",
                category=FactorCategory.ONCHAIN,
                source=FactorSource.DEFILLAMA,
                min_points=10
            )

            with patch.object(registry, 'get_factor') as mock_meta:
                mock_meta.return_value = metadata

                # Only 5 data points (< 10 required)
                historical_values = [1.0, 2.0, 3.0, 4.0, 5.0]

                result = engine.compute_factor(
                    "test_factor",
                    historical_values=historical_values
                )

                # Should return NaN with confidence 0
                assert math.isnan(result.raw_value)
                assert result.confidence == 0
                assert result.metadata.get("reason") == "insufficient_data_points"

    def test_insufficient_unique_days(self):
        """Test that insufficient unique days returns NaN."""
        engine = FactorEngine()
        engine.discover_factors()

        with patch.object(registry, 'get_compute_func') as mock_func:
            mock_func.return_value = lambda: 50.0

            metadata = FactorMetadata(
                name="test_factor",
                display_name="Test Factor",
                category=FactorCategory.ONCHAIN,
                source=FactorSource.DEFILLAMA,
                min_days=7
            )

            with patch.object(registry, 'get_factor') as mock_meta:
                mock_meta.return_value = metadata

                # 10 points but only 2 unique days (< 7 required)
                historical_values = [
                    {"value": 1.0, "date": "2026-06-01"},
                    {"value": 2.0, "date": "2026-06-01"},
                    {"value": 3.0, "date": "2026-06-02"},
                    {"value": 4.0, "date": "2026-06-02"},
                    {"value": 5.0, "date": "2026-06-02"},
                    {"value": 6.0, "date": "2026-06-02"},
                    {"value": 7.0, "date": "2026-06-02"},
                    {"value": 8.0, "date": "2026-06-02"},
                    {"value": 9.0, "date": "2026-06-02"},
                    {"value": 10.0, "date": "2026-06-02"},
                ]

                result = engine.compute_factor(
                    "test_factor",
                    historical_values=historical_values
                )

                # Should return NaN with confidence 0
                assert math.isnan(result.raw_value)
                assert result.confidence == 0
                assert result.metadata.get("reason") == "insufficient_days"

    def test_sufficient_data_passes(self):
        """Test that sufficient data passes the check."""
        engine = FactorEngine()
        engine.discover_factors()

        with patch.object(registry, 'get_compute_func') as mock_func:
            mock_func.return_value = lambda: 75.0

            metadata = FactorMetadata(
                name="test_factor",
                display_name="Test Factor",
                category=FactorCategory.ONCHAIN,
                source=FactorSource.DEFILLAMA,
                min_days=0,  # Don't check days for pure float values
                min_points=10,
                typical_range=(0, 100)
            )

            with patch.object(registry, 'get_factor') as mock_meta:
                mock_meta.return_value = metadata

                # 10 float values
                historical_values = [float(i) for i in range(1, 11)]

                result = engine.compute_factor(
                    "test_factor",
                    historical_values=historical_values
                )

                # Should compute successfully
                assert result.raw_value == 75.0
                assert result.confidence == 0.9

    def test_no_minimum_requirements(self):
        """Test factors with no minimum requirements always pass."""
        engine = FactorEngine()
        engine.discover_factors()

        with patch.object(registry, 'get_compute_func') as mock_func:
            mock_func.return_value = lambda: 100.0

            metadata = FactorMetadata(
                name="simple_factor",
                display_name="Simple Factor",
                category=FactorCategory.MARKET,
                source=FactorSource.COINGECKO,
                min_days=0,
                min_points=0
            )

            with patch.object(registry, 'get_factor') as mock_meta:
                mock_meta.return_value = metadata

                # Empty historical data should still work
                result = engine.compute_factor(
                    "simple_factor",
                    historical_values=None
                )

                assert result.raw_value == 100.0