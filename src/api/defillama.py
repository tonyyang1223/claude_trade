"""DefiLlama API client for Stablecoin Flow and TVL data.

DefiLlama provides free access to:
- Stablecoin supply and chain distribution
- DeFi protocol TVL (Total Value Locked)
- Chain-level metrics

API Documentation: https://defillama.com/docs/api
Free tier: No API key required, unlimited requests.
"""
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from src.data.cache import DataCache
from src.data.coin_mappings import COIN_TO_DEFILLAMA, COIN_TO_CHAIN


class DefiLlamaClient:
    """Client for DefiLlama API.

    Fetches stablecoin flow and TVL data.

    Attributes:
        cache: DataCache for caching responses
        session: requests.Session for connection pooling

    Example:
        >>> client = DefiLlamaClient()
        >>> stablecoins = client.get_stablecoin_flows()
        >>> tvl = client.get_protocol_tvl("uniswap")
    """

    BASE_URL = "https://api.llama.fi"
    STABLECOINS_URL = "https://stablecoins.llama.fi"  # Dedicated stablecoins API

    def __init__(self, cache_dir: Path = Path("data/cache")):
        """Initialize DefiLlama client.

        Args:
            cache_dir: Directory for caching data
        """
        self.cache = DataCache(cache_dir, expire_hours=0.5)  # 30 minutes TTL
        self.session = requests.Session()

    def get_stablecoin_flows(self) -> Dict[str, Any]:
        """Get stablecoin supply and distribution across chains.

        Returns:
            Dictionary with stablecoin flow data including:
            - stablecoins: List of stablecoin data
            - total_supply: Total stablecoin supply
            - chain_distribution: Distribution across chains
            - net_flows: Recent net flows
        """
        cache_key = "stablecoin_flows_global"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            # Use dedicated stablecoins API
            response = self.session.get(
                f"{self.STABLECOINS_URL}/stablecoins",
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # stablecoins.llama.fi returns peggedAssets and chains
                pegged_assets = data.get("peggedAssets", [])
                chains_data = data.get("chains", [])

                stablecoins_data = []

                for asset in pegged_assets[:50]:  # Top 50 stablecoins
                    name = asset.get("name", "")
                    symbol = asset.get("symbol", "")

                    # Get circulating supply
                    circulating = asset.get("circulating", {})
                    total_supply = circulating.get("peggedUSD", 0) if circulating else 0

                    # Get previous day supply for change calculation
                    prev_circulating = asset.get("circulatingPrevDay", {})
                    prev_supply = prev_circulating.get("peggedUSD", total_supply) if prev_circulating else total_supply

                    mint_change_24h = total_supply - prev_supply if total_supply and prev_supply else 0

                    stablecoins_data.append({
                        "name": name,
                        "symbol": symbol,
                        "total_supply": total_supply,
                        "mint_change_24h": mint_change_24h,
                    })

                # Calculate total stablecoin supply
                total_supply = sum(s.get("total_supply", 0) for s in stablecoins_data)

                # Calculate net flows (sum of mint changes)
                net_flows = sum(s.get("mint_change_24h", 0) for s in stablecoins_data)

                # Get chain distribution from chains data
                chain_distribution = {}
                for chain in chains_data:
                    chain_name = chain.get("name", "")
                    chain_circulating = chain.get("totalCirculatingUSD", {})
                    chain_supply = chain_circulating.get("peggedUSD", 0) if chain_circulating else 0
                    if chain_name:
                        chain_distribution[chain_name] = chain_supply

                result = {
                    "stablecoins": stablecoins_data[:20],  # Top 20 stablecoins
                    "total_supply": total_supply,
                    "net_flows_24h": net_flows,
                    "chain_distribution": chain_distribution,
                    "confidence": 0.9,  # DefiLlama API, high confidence
                    "timestamp": datetime.now().isoformat()
                }

                self.cache.save(cache_key, result)
                return result

            return self._get_stablecoin_flows_fallback()

        except Exception as e:
            print(f"Warning: Failed to fetch stablecoin flows: {e}")
            return self._get_stablecoin_flows_fallback()

    def _get_stablecoin_flows_fallback(self) -> Dict[str, Any]:
        """Fallback stablecoin data when API fails.

        Returns:
            Default stablecoin flow data
        """
        return {
            "stablecoins": [],
            "total_supply": 0.0,
            "net_flows_24h": 0.0,
            "chain_distribution": {},
            "confidence": 0.1,  # Fallback data, low confidence
            "timestamp": datetime.now().isoformat(),
            "error": "API unavailable"
        }

    def _calculate_chain_distribution(self, stablecoins_data: List[Dict]) -> Dict[str, float]:
        """Calculate aggregate chain distribution.

        Args:
            stablecoins_data: List of stablecoin data

        Returns:
            Dictionary with chain totals
        """
        chain_totals = {}

        for stablecoin in stablecoins_data:
            chain_balances = stablecoin.get("chain_distribution", {})
            for chain, balance in chain_balances.items():
                if chain not in chain_totals:
                    chain_totals[chain] = 0
                chain_totals[chain] += balance

        return chain_totals

    def get_chain_stablecoin_flows(self, chain: str) -> Dict[str, Any]:
        """Get stablecoin flows for a specific chain.

        Args:
            chain: Chain name (e.g., 'Ethereum')

        Returns:
            Dictionary with chain-specific stablecoin data
        """
        chain_name = COIN_TO_CHAIN.get(chain, chain)
        cache_key = f"stablecoin_flows_{chain_name}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(
                f"{self.BASE_URL}/stablecoins/{chain_name}",
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                stablecoins_data = []
                total_supply = 0
                net_flows = 0

                for stablecoin in data:
                    supply = stablecoin.get("balance", 0)
                    mint_change = stablecoin.get("minted24h", 0)

                    stablecoins_data.append({
                        "symbol": stablecoin.get("symbol", ""),
                        "supply": supply,
                        "mint_change_24h": mint_change
                    })

                    total_supply += supply
                    net_flows += mint_change

                result = {
                    "chain": chain_name,
                    "stablecoins": stablecoins_data,
                    "total_supply": total_supply,
                    "net_flows_24h": net_flows,
                    "confidence": 0.9,  # DefiLlama API, high confidence
                    "timestamp": datetime.now().isoformat()
                }

                self.cache.save(cache_key, result)
                return result

            return self._get_chain_stablecoin_fallback(chain_name)

        except Exception as e:
            print(f"Warning: Failed to fetch chain stablecoin flows for {chain}: {e}")
            return self._get_chain_stablecoin_fallback(chain_name)

    def _get_chain_stablecoin_fallback(self, chain: str) -> Dict[str, Any]:
        """Fallback chain stablecoin data.

        Args:
            chain: Chain name

        Returns:
            Default data
        """
        return {
            "chain": chain,
            "stablecoins": [],
            "total_supply": 0.0,
            "net_flows_24h": 0.0,
            "confidence": 0.1,  # Fallback data, low confidence
            "timestamp": datetime.now().isoformat(),
            "error": "API unavailable"
        }

    def get_protocol_tvl(self, protocol_slug: str) -> Dict[str, Any]:
        """Get TVL for a specific DeFi protocol.

        Args:
            protocol_slug: DefiLlama protocol slug (e.g., 'uniswap')

        Returns:
            Dictionary with TVL data including:
            - protocol: Protocol name
            - tvl: Current TVL
            - tvl_change_24h: 24h change percentage
            - tvl_change_7d: 7d change percentage
            - chain_breakdown: TVL by chain
        """
        cache_key = f"protocol_tvl_{protocol_slug}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(
                f"{self.BASE_URL}/protocol/{protocol_slug}",
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Get current TVL from currentChainTvls (API now returns list for 'tvl')
                current_chain_tvls = data.get("currentChainTvls", {})
                current_tvl = sum(current_chain_tvls.values()) if current_chain_tvls else 0

                # Calculate TVL changes from historical data (tvl is now a list)
                tvl_history = data.get("tvl", [])

                # tvl_history contains historical data points
                tvl_change_24h = 0
                tvl_change_7d = 0

                if isinstance(tvl_history, list) and len(tvl_history) >= 2:
                    # Get latest and previous TVL values
                    latest_tvl = tvl_history[-1].get("totalLiquidityUSD", current_tvl)

                    # 24h change - check if we have enough data
                    if len(tvl_history) >= 2:
                        prev_tvl = tvl_history[-2].get("totalLiquidityUSD", latest_tvl)
                        tvl_change_24h = ((latest_tvl - prev_tvl) / prev_tvl * 100) if prev_tvl else 0

                    # 7d change
                    if len(tvl_history) >= 8:
                        week_ago_tvl = tvl_history[-8].get("totalLiquidityUSD", latest_tvl)
                        tvl_change_7d = ((latest_tvl - week_ago_tvl) / week_ago_tvl * 100) if week_ago_tvl else 0
                    else:
                        tvl_change_7d = tvl_change_24h * 7  # Estimate

                # Get chain breakdown
                chains_data = current_chain_tvls

                result = {
                    "protocol": data.get("name", protocol_slug),
                    "slug": protocol_slug,
                    "tvl": current_tvl,
                    "tvl_change_24h": tvl_change_24h,
                    "tvl_change_7d": tvl_change_7d,
                    "chain_breakdown": chains_data,
                    "confidence": 0.9,  # DefiLlama API, high confidence
                    "timestamp": datetime.now().isoformat()
                }

                self.cache.save(cache_key, result)
                return result

            return self._get_protocol_tvl_fallback(protocol_slug)

        except Exception as e:
            print(f"Warning: Failed to fetch TVL for {protocol_slug}: {e}")
            return self._get_protocol_tvl_fallback(protocol_slug)

    def get_protocol_fees(
        self,
        protocol_slug: str,
        aggregate_versions: bool = True
    ) -> Dict[str, Any]:
        """Get fee/revenue data for a protocol from DefiLlama ``/overview/fees``.

        The per-protocol endpoint (used by :meth:`get_protocol_tvl`) does not
        expose fees for parent protocols, so fee data is pulled from the
        fees overview instead.

        Args:
            protocol_slug: DefiLlama slug (e.g., 'uniswap', 'curve-dex')
            aggregate_versions: If True, also sum child versions named
                ``<slug>-v<N>`` (e.g. uniswap-v1..v4). Uniswap is reported by
                DefiLlama only as per-version rows, so aggregation is required
                to get a protocol-level fee figure.

        Returns:
            Dictionary with fee metrics including:
            - fees_24h / fees_7d / fees_30d / fees_annualized / fees_all_time
            - change_1d / change_7d
            - included_slugs: slugs that were summed
        """
        cache_key = f"protocol_fees_{protocol_slug}_{aggregate_versions}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(
                f"{self.BASE_URL}/overview/fees",
                timeout=60
            )

            if response.status_code == 200:
                protocols = (response.json() or {}).get("protocols") or []

                wanted = {protocol_slug}
                if aggregate_versions:
                    prefix = protocol_slug + "-v"
                    for item in protocols:
                        slug = item.get("slug") or ""
                        if slug.startswith(prefix) and slug[len(prefix):].isdigit():
                            wanted.add(slug)

                def total(field: str) -> float:
                    return sum(
                        (item.get(field) or 0)
                        for item in protocols
                        if item.get("slug") in wanted
                    )

                matched = sorted(
                    slug for slug in wanted
                    if any((item.get("slug") == slug) for item in protocols)
                )

                result = {
                    "slug": protocol_slug,
                    "fees_24h": total("total24h"),
                    "fees_7d": total("total7d"),
                    "fees_30d": total("total30d"),
                    "fees_annualized": total("annualized1y"),
                    "fees_all_time": total("totalAllTime"),
                    "change_1d": next(
                        (item.get("change_1d") for item in protocols
                         if item.get("slug") == protocol_slug), None
                    ),
                    "change_7d": next(
                        (item.get("change_7d") for item in protocols
                         if item.get("slug") == protocol_slug), None
                    ),
                    "included_slugs": matched,
                    "confidence": 0.9 if matched else 0.1,
                    "timestamp": datetime.now().isoformat()
                }

                self.cache.save(cache_key, result)
                return result

            return self._get_protocol_fees_fallback(protocol_slug)

        except Exception as e:
            print(f"Warning: Failed to fetch fees for {protocol_slug}: {e}")
            return self._get_protocol_fees_fallback(protocol_slug)

    def _get_protocol_fees_fallback(self, protocol_slug: str) -> Dict[str, Any]:
        """Fallback fee data when the fees endpoint is unavailable.

        Args:
            protocol_slug: DefiLlama slug

        Returns:
            Empty fee data with low confidence
        """
        return {
            "slug": protocol_slug,
            "fees_24h": 0.0,
            "fees_7d": 0.0,
            "fees_30d": 0.0,
            "fees_annualized": 0.0,
            "fees_all_time": 0.0,
            "change_1d": None,
            "change_7d": None,
            "included_slugs": [],
            "confidence": 0.1,
            "timestamp": datetime.now().isoformat(),
            "error": "Fees API unavailable"
        }

    def _get_protocol_tvl_fallback(self, protocol_slug: str) -> Dict[str, Any]:
        """Fallback protocol TVL data.

        Args:
            protocol_slug: Protocol slug

        Returns:
            Default TVL data
        """
        return {
            "protocol": protocol_slug,
            "slug": protocol_slug,
            "tvl": 0.0,
            "tvl_change_24h": 0.0,
            "tvl_change_7d": 0.0,
            "chain_breakdown": {},
            "confidence": 0.1,  # Fallback data, low confidence
            "timestamp": datetime.now().isoformat(),
            "error": "API unavailable"
        }

    def get_chain_tvl(self, chain: str) -> Dict[str, Any]:
        """Get total TVL for a chain.

        Args:
            chain: Chain name (e.g., 'Ethereum')

        Returns:
            Dictionary with chain TVL data
        """
        chain_name = COIN_TO_CHAIN.get(chain, chain)
        cache_key = f"chain_tvl_{chain_name}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = self.session.get(
                f"{self.BASE_URL}/v2/chains",
                timeout=30
            )

            if response.status_code == 200:
                chains_data = response.json()

                for chain_data in chains_data:
                    if chain_data.get("name", "") == chain_name:
                        current_tvl = chain_data.get("tvl", 0)

                        # Calculate changes
                        tvl_change_24h = chain_data.get("change_1d", 0)
                        tvl_change_7d = chain_data.get("change_7d", 0)

                        result = {
                            "chain": chain_name,
                            "tvl": current_tvl,
                            "tvl_change_24h": tvl_change_24h,
                            "tvl_change_7d": tvl_change_7d,
                            "protocols_count": chain_data.get("protocols", 0),
                            "confidence": 0.9,  # DefiLlama API, high confidence
                            "timestamp": datetime.now().isoformat()
                        }

                        self.cache.save(cache_key, result)
                        return result

            return self._get_chain_tvl_fallback(chain_name)

        except Exception as e:
            print(f"Warning: Failed to fetch chain TVL for {chain}: {e}")
            return self._get_chain_tvl_fallback(chain_name)

    def _get_chain_tvl_fallback(self, chain: str) -> Dict[str, Any]:
        """Fallback chain TVL data.

        Args:
            chain: Chain name

        Returns:
            Default TVL data
        """
        return {
            "chain": chain,
            "tvl": 0.0,
            "tvl_change_24h": 0.0,
            "tvl_change_7d": 0.0,
            "protocols_count": 0,
            "confidence": 0.1,  # Fallback data, low confidence
            "timestamp": datetime.now().isoformat(),
            "error": "API unavailable"
        }

    def score_stablecoin_flow(self, net_flow_24h: float) -> int:
        """Score stablecoin net flow (1-5).

        Interpretation:
        - Positive flow (minting/inflow): Capital entering, potential buy pressure
        - Negative flow (burning/outflow): Capital leaving, potential sell pressure

        Args:
            net_flow_24h: 24h net flow in USD

        Returns:
            Score (1-5)
        """
        # Flows in millions
        flow_millions = net_flow_24h / 1_000_000

        if flow_millions > 100:  # Large inflow
            return 5  # Strong buy pressure
        elif flow_millions > 50:
            return 4
        elif abs(flow_millions) < 10:  # Neutral
            return 3
        elif flow_millions < -100:  # Large outflow
            return 1  # Strong sell pressure
        else:
            return 2

    def score_tvl_change(self, tvl_change_7d: float) -> int:
        """Score TVL change (1-5).

        Interpretation:
        - TVL increasing: Capital flowing into DeFi, confidence growing
        - TVL decreasing: Capital leaving DeFi, risk increasing

        Args:
            tvl_change_7d: 7d TVL change percentage

        Returns:
            Score (1-5)
        """
        if tvl_change_7d > 10:  # Strong growth
            return 5
        elif tvl_change_7d > 5:
            return 4
        elif abs(tvl_change_7d) < 2:  # Stable
            return 3
        elif tvl_change_7d < -10:  # Strong decline
            return 1
        else:
            return 2

    def get_protocol_slug(self, coin_id: str) -> Optional[str]:
        """Get DefiLlama protocol slug for a coin.

        Args:
            coin_id: CoinGecko coin ID

        Returns:
            Protocol slug or None
        """
        return COIN_TO_DEFILLAMA.get(coin_id)