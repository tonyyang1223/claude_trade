"""Data models for cryptocurrency market data."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CoinData(BaseModel):
    """Represents data for a single cryptocurrency.

    Attributes:
        id: Unique identifier (e.g., 'bitcoin')
        symbol: Trading symbol (e.g., 'BTC')
        name: Full name (e.g., 'Bitcoin')
        current_price: Current price in USD
        market_cap: Market capitalization in USD
        market_cap_rank: Ranking by market cap
        total_volume: 24h trading volume in USD
        circulating_supply: Coins in circulation
        total_supply: Total coins that will ever exist
        max_supply: Maximum supply cap
        price_change_24h: Absolute price change in 24h
        price_change_percentage_24h: Percentage change in 24h
        last_updated: When data was last updated
    """
    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    market_cap_rank: int
    total_volume: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    last_updated: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "bitcoin",
                "symbol": "BTC",
                "name": "Bitcoin",
                "current_price": 50000.0,
                "market_cap": 1000000000000.0,
                "market_cap_rank": 1
            }]
        }
    }


class MarketData(BaseModel):
    """Represents overall market data snapshot.

    Attributes:
        timestamp: When this data was collected
        total_market_cap: Total crypto market cap
        btc_dominance: Bitcoin's market share percentage
        eth_dominance: Ethereum's market share percentage
        coins: List of top coins data
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    total_market_cap: float
    btc_dominance: float
    eth_dominance: Optional[float] = None
    coins: List[CoinData] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "total_market_cap": 2000000000000.0,
                "btc_dominance": 50.0,
                "eth_dominance": 20.0
            }]
        }
    }