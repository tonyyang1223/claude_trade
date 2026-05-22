"""Main market data collector."""
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from src.api.coingecko import CoinGeckoClient
from src.api.coinmarketcap import CoinMarketCapClient
from src.data.models import CoinData, MarketData
from src.data.cache import DataCache
from src.data.exporters import DataExporter


class MarketCollector:
    """Orchestrates market data collection.

    Coordinates API clients, caching, and data export.

    Attributes:
        api_source: Which API to use ('coingecko' or 'coinmarketcap')
        cache: DataCache instance
        exporter: DataExporter instance

    Example:
        >>> collector = MarketCollector(api_source="coingecko")
        >>> market_data = collector.collect_market_data(top_n=100)
        >>> collector.export_data(market_data, format="json")
    """

    def __init__(
        self,
        api_source: str = "coingecko",
        api_key: Optional[str] = None,
        cache_dir: Path = Path("data/cache"),
        output_dir: Path = Path("data/processed"),
        cache_expire_hours: int = 24
    ):
        """Initialize market collector.

        Args:
            api_source: API to use ('coingecko' or 'coinmarketcap')
            api_key: Optional API key
            cache_dir: Directory for cache files
            output_dir: Directory for exported files
            cache_expire_hours: Cache expiration time
        """
        self.api_source = api_source
        self.cache = DataCache(cache_dir, expire_hours=cache_expire_hours)
        self.exporter = DataExporter(output_dir)

        if api_source == "coingecko":
            self.api_client = CoinGeckoClient(api_key=api_key)
        elif api_source == "coinmarketcap":
            if not api_key:
                raise ValueError("CoinMarketCap requires API key")
            self.api_client = CoinMarketCapClient(api_key=api_key)
        else:
            raise ValueError(f"Unknown API source: {api_source}")

    def collect_coin_data(self, coin_id: str, use_cache: bool = True) -> CoinData:
        """Collect data for a single coin.

        Args:
            coin_id: Coin identifier
            use_cache: Whether to use cached data

        Returns:
            CoinData instance
        """
        cache_key = f"coin_{coin_id}"

        # Try cache first
        if use_cache:
            cached = self.cache.load(cache_key)
            if cached:
                return CoinData(**cached)

        # Fetch from API
        data = self.api_client.get_coin_data(coin_id)

        # Cache the result
        self.cache.save(cache_key, data)

        return CoinData(**data)

    def collect_market_data(self, top_n: int = 100, use_cache: bool = True) -> MarketData:
        """Collect overall market data.

        Args:
            top_n: Number of top coins to include
            use_cache: Whether to use cached data

        Returns:
            MarketData instance
        """
        # Get market data
        market_cache_key = "market_global"
        market_data = None

        if use_cache:
            cached = self.cache.load(market_cache_key)
            if cached:
                market_data = cached

        if not market_data:
            market_data = self.api_client.get_market_data()
            self.cache.save(market_cache_key, market_data)

        # Get top coins
        coins_cache_key = f"top_coins_{top_n}"
        coins_data = None

        if use_cache:
            cached = self.cache.load(coins_cache_key)
            if cached:
                coins_data = cached

        if not coins_data:
            coins_data = self.api_client.get_top_coins(limit=top_n)
            self.cache.save(coins_cache_key, coins_data)

        # Build MarketData
        coins = [CoinData(**coin) for coin in coins_data]

        return MarketData(
            timestamp=datetime.now(),
            total_market_cap=market_data.get("total_market_cap"),
            btc_dominance=market_data.get("btc_dominance"),
            eth_dominance=market_data.get("eth_dominance"),
            coins=coins
        )

    def export_data(
        self,
        data: MarketData,
        format: str = "json",
        prefix: str = "market_data"
    ) -> Path:
        """Export collected data.

        Args:
            data: MarketData to export
            format: Export format ('json' or 'csv')
            prefix: Filename prefix

        Returns:
            Path to exported file
        """
        # Convert to list of dicts
        data_dict = data.model_dump()

        if format == "json":
            return self.exporter.to_json([data_dict], prefix)
        elif format == "csv":
            # Flatten for CSV
            flat_data = {
                "timestamp": data_dict.get("timestamp"),
                "total_market_cap": data_dict.get("total_market_cap"),
                "btc_dominance": data_dict.get("btc_dominance"),
                "eth_dominance": data_dict.get("eth_dominance"),
                "coin_count": len(data_dict.get("coins", []))
            }
            return self.exporter.to_csv([flat_data], prefix)
        else:
            raise ValueError(f"Unknown format: {format}")