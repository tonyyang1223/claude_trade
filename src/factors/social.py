"""Social sentiment factors: Reddit mentions and sentiment."""
from src.factors import register_factor, FactorCategory, FactorSource
from src.factors.registry import registry
from src.api.reddit import RedditClient


@register_factor(
    name="reddit_mention_count",
    display_name="Reddit Mention Count",
    category=FactorCategory.SOCIAL,
    source=FactorSource.REDDIT,
    description="Number of mentions across target subreddits in 24h",
    confidence=0.85,
    version="1.0.0",
    tags=["social", "reddit", "mentions"],
    higher_is_better=True,
    typical_range=(0, 500)
)
def compute_reddit_mention_count(coin_name: str) -> float:
    """Compute Reddit mention count for a coin."""
    client = RedditClient()
    data = client.get_coin_mentions(coin_name)
    return float(data.get("mention_count", 0))


@register_factor(
    name="reddit_mention_growth",
    display_name="Reddit Mention Growth",
    category=FactorCategory.SOCIAL,
    source=FactorSource.REDDIT,
    description="Growth rate of mentions vs 7d average (%)",
    confidence=0.80,
    version="1.0.0",
    tags=["social", "reddit", "momentum"],
    higher_is_better=True,
    typical_range=(-100, 200)
)
def compute_reddit_mention_growth(coin_name: str) -> float:
    """Compute Reddit mention growth rate."""
    client = RedditClient()
    data = client.get_coin_mentions(coin_name)
    return float(data.get("mention_growth", 0))


@register_factor(
    name="reddit_sentiment_score",
    display_name="Reddit Sentiment Score",
    category=FactorCategory.SOCIAL,
    source=FactorSource.REDDIT,
    description="Sentiment score from Reddit posts (0-100, 50=neutral)",
    confidence=0.75,
    version="1.0.0",
    tags=["social", "reddit", "sentiment"],
    higher_is_better=True,
    typical_range=(0, 100)
)
def compute_reddit_sentiment_score(coin_name: str) -> float:
    """Compute Reddit sentiment score."""
    client = RedditClient()
    data = client.get_coin_mentions(coin_name)
    return float(data.get("sentiment_score", 50))


@register_factor(
    name="reddit_hot_post_score",
    display_name="Reddit Hot Post Score",
    category=FactorCategory.SOCIAL,
    source=FactorSource.REDDIT,
    description="Engagement score for hot posts mentioning the coin",
    confidence=0.70,
    version="1.0.0",
    tags=["social", "reddit", "engagement"],
    higher_is_better=True,
    typical_range=(0, 100)
)
def compute_reddit_hot_post_score(coin_name: str) -> float:
    """Compute Reddit hot post engagement score."""
    client = RedditClient()
    data = client.get_coin_mentions(coin_name)
    return float(data.get("hot_post_score", 0))


@registry.register_normalizer("reddit_mention_count")
def normalize_reddit_mention_count(raw_value: float) -> float:
    """Normalize mention count: 0=0.0, 50=0.5, 100+=1.0."""
    normalized = min(1.0, raw_value / 100)
    return max(0.0, normalized)


@registry.register_normalizer("reddit_mention_growth")
def normalize_reddit_mention_growth(raw_value: float) -> float:
    """Normalize growth: -100%=0.0, 0%=0.5, +100%=1.0."""
    clamped = max(-100, min(200, raw_value))
    normalized = 0.5 + (clamped / 400)
    return max(0.0, min(1.0, normalized))


@registry.register_normalizer("reddit_sentiment_score")
def normalize_reddit_sentiment(raw_value: float) -> float:
    """Normalize sentiment (0-100) to 0-1."""
    return max(0.0, min(1.0, raw_value / 100))