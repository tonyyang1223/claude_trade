"""Market sentiment factors: Google Trends and Fear & Greed Index.

These factors measure market interest and sentiment without requiring
API keys (completely free).
"""
from src.factors import register_factor, FactorCategory, FactorSource
from src.factors.registry import registry
from src.api.google_trends import GoogleTrendsClient
from src.api.sentiment_api import SentimentAPIClient


# ==================== Google Trends Factors ====================

@register_factor(
    name="google_trends_interest",
    display_name="Google Search Interest",
    category=FactorCategory.SOCIAL,
    source=FactorSource.GOOGLE_TRENDS,
    description="Google search interest for coin keyword (0-100)",
    confidence=0.85,
    version="1.0.0",
    tags=["social", "google", "trends", "hype"],
    higher_is_better=True,
    typical_range=(0, 100)
)
def compute_google_trends_interest(coin_name: str) -> float:
    """Compute Google search interest for a coin."""
    client = GoogleTrendsClient()
    if not client.is_available():
        return 50.0  # Neutral default

    data = client.get_search_trends(coin_name, days=30)
    return float(data.get("current_interest", 50))


@register_factor(
    name="google_trends_change",
    display_name="Google Trends Change",
    category=FactorCategory.SOCIAL,
    source=FactorSource.GOOGLE_TRENDS,
    description="Change in search interest vs previous period (%)",
    confidence=0.80,
    version="1.0.0",
    tags=["social", "google", "trends", "momentum"],
    higher_is_better=True,
    typical_range=(-50, 100)
)
def compute_google_trends_change(coin_name: str) -> float:
    """Compute Google trends change rate."""
    client = GoogleTrendsClient()
    if not client.is_available():
        return 0.0

    data = client.get_search_trends(coin_name, days=30)
    return float(data.get("interest_change_pct", 0))


# ==================== Fear & Greed Index Factors ====================

@register_factor(
    name="fear_greed_index",
    display_name="Fear & Greed Index",
    category=FactorCategory.SENTIMENT,
    source=FactorSource.ALTERNATIVE_ME,
    description="Crypto market Fear & Greed Index (0-100)",
    confidence=0.90,
    version="1.0.0",
    tags=["sentiment", "market", "fear_greed"],
    higher_is_better=False,  # Lower (fear) is actually better for buying
    typical_range=(0, 100)
)
def compute_fear_greed_index() -> float:
    """Compute Fear & Greed Index."""
    client = SentimentAPIClient()
    data = client.get_fear_greed_index(limit=1)
    return float(data.get("value", 50))


@register_factor(
    name="fear_greed_trend",
    display_name="Fear & Greed Trend",
    category=FactorCategory.SENTIMENT,
    source=FactorSource.ALTERNATIVE_ME,
    description="Trend direction of Fear & Greed (more_fearful/stable/more_greedy)",
    confidence=0.85,
    version="1.0.0",
    tags=["sentiment", "market", "trend"],
    higher_is_better=True,
    typical_range=(-1, 1)  # -1 = more fearful, 0 = stable, 1 = more greedy
)
def compute_fear_greed_trend() -> float:
    """Compute Fear & Greed trend direction as numeric value."""
    client = SentimentAPIClient()
    trend = client.get_sentiment_trend(days=7)

    direction = trend.get("direction", "stable")
    if direction == "more_fearful":
        return -1.0
    elif direction == "more_greedy":
        return 1.0
    else:
        return 0.0


@register_factor(
    name="combined_sentiment_score",
    display_name="Combined Sentiment Score",
    category=FactorCategory.SENTIMENT,
    source=FactorSource.ALTERNATIVE_ME,
    description="Combined sentiment score from multiple sources (1-5)",
    confidence=0.85,
    version="1.0.0",
    tags=["sentiment", "combined", "overall"],
    higher_is_better=True,
    typical_range=(1, 5)
)
def compute_combined_sentiment_score(coin_name: str = None) -> float:
    """Compute combined sentiment score (1-5)."""
    client = SentimentAPIClient()
    data = client.get_combined_sentiment(coin_name)
    return float(data.get("combined_score", 3))


# ==================== Normalizers ====================

@registry.register_normalizer("google_trends_interest")
def normalize_google_trends_interest(raw_value: float) -> float:
    """Normalize search interest (0-100) to 0-1."""
    return max(0.0, min(1.0, raw_value / 100))


@registry.register_normalizer("google_trends_change")
def normalize_google_trends_change(raw_value: float) -> float:
    """Normalize change: -50%=0.0, 0%=0.5, +100%=1.0."""
    clamped = max(-50, min(100, raw_value))
    normalized = 0.5 + (clamped / 200)
    return max(0.0, min(1.0, normalized))


@registry.register_normalizer("fear_greed_index")
def normalize_fear_greed_index(raw_value: float) -> float:
    """Normalize Fear & Greed (0-100) to 0-1.

    Note: Lower values (fear) are actually better for buying,
    so we invert: 0 (fear) -> 1.0, 100 (greed) -> 0.0
    """
    return max(0.0, min(1.0, 1.0 - (raw_value / 100)))


@registry.register_normalizer("combined_sentiment_score")
def normalize_combined_sentiment(raw_value: float) -> float:
    """Normalize sentiment score (1-5) to 0-1."""
    return max(0.0, min(1.0, (raw_value - 1) / 4))