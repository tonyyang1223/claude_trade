"""Data models for cryptocurrency market data."""
from datetime import datetime
from typing import Optional, List, Dict
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


class TechnicalIndicators(BaseModel):
    """Technical indicators data for a cryptocurrency.

    Attributes:
        rsi: RSI value (0-100)
        rsi_signal: RSI signal score (1-5)
        ma_50: 50-day moving average
        ma_200: 200-day moving average
        ma_signal: Moving average signal (1-5)
        support_levels: List of support price levels
        resistance_levels: List of resistance price levels
        trend: Trend direction (up/down/sideways)
        trend_signal: Trend signal (1-5)
        fibonacci_levels: Fibonacci retracement levels
        volume_ratio: Volume/Market cap ratio
        volume_signal: Volume signal (1-5)
        timestamp: When data was calculated
    """
    rsi: float
    rsi_signal: int = Field(ge=1, le=5)
    ma_50: float
    ma_200: float
    ma_signal: int = Field(ge=1, le=5)
    support_levels: List[float]
    resistance_levels: List[float]
    trend: str
    trend_signal: int = Field(ge=1, le=5)
    fibonacci_levels: Dict[str, float]
    volume_ratio: float
    volume_signal: int = Field(ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.now)


class BTCDominance(BaseModel):
    """BTC dominance data.

    Attributes:
        current_dominance: Current BTC dominance percentage
        trend: Trend direction (rising/falling/stable)
        market_phase: Market phase description
        altcoin_season: Whether it's altcoin season
        recommendation: Action recommendation
        timestamp: When data was collected
    """
    current_dominance: float
    trend: str
    market_phase: str
    altcoin_season: bool
    recommendation: str
    timestamp: datetime = Field(default_factory=datetime.now)


class SentimentData(BaseModel):
    """Sentiment analysis data.

    Attributes:
        google_trends_score: Google search interest (0-100)
        google_trends_change: Search interest change rate
        fear_greed_index: Fear & Greed Index (0-100)
        social_sentiment: Social sentiment (bullish/bearish/neutral)
        sentiment_signal: Sentiment signal (1-5)
        timestamp: When data was collected
    """
    google_trends_score: int = Field(ge=0, le=100)
    google_trends_change: float
    fear_greed_index: int = Field(ge=0, le=100)
    social_sentiment: str
    sentiment_signal: int = Field(ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.now)


class OnchainData(BaseModel):
    """Onchain analysis data.

    Attributes:
        nupl: Net unrealized profit/loss ratio
        mvrv: MVRV ratio
        holder_distribution: Holder distribution by percentage
        active_addresses: Number of active addresses
        transaction_count: Transaction count
        onchain_signal: Onchain signal (1-5)
        timestamp: When data was collected
    """
    nupl: Optional[float] = None
    mvrv: Optional[float] = None
    holder_distribution: Optional[Dict] = None
    active_addresses: Optional[int] = None
    transaction_count: Optional[int] = None
    onchain_signal: int = Field(ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.now)


class GithubData(BaseModel):
    """GitHub activity data.

    Attributes:
        repo_url: Repository URL
        commit_count_30d: Commit count in last 30 days
        contributor_count: Number of contributors
        issue_count: Number of open issues
        pr_count: Number of pull requests
        last_commit_date: Last commit timestamp
        activity_score: Activity score (1-5)
        timestamp: When data was collected
    """
    repo_url: str
    commit_count_30d: int
    contributor_count: int
    issue_count: int
    pr_count: int
    last_commit_date: datetime
    activity_score: int = Field(ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.now)