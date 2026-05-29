"""Factor Classification System.

Extends factor metadata with:
- subcategory: Fine-grained classification
- investment_theme: momentum/value/quality/etc
- data_frequency: real-time/daily/weekly
- update_priority: critical/high/normal/low

Classification Structure:
    Category → Subcategory → Factor
    
Example:
    derivatives → funding → funding_rate
    onchain → tvl → protocol_tvl
    social → mentions → reddit_mention_count
"""
from dataclasses import dataclass
from typing import Dict, List, Any
from enum import Enum

from src.factors import registry


class FactorSubcategory(str, Enum):
    """Fine-grained factor subcategories."""
    # Derivatives
    FUNDING = "funding"
    OPEN_INTEREST = "open_interest"
    
    # Onchain
    TVL = "tvl"
    STABLECOIN = "stablecoin"
    FLOW = "flow"
    
    # Social/Sentiment
    MENTIONS = "mentions"
    SENTIMENT_RAW = "sentiment_raw"
    ENGAGEMENT = "engagement"
    
    # Developer
    COMMITS = "commits"
    CONTRIBUTORS = "contributors"
    ISSUES = "issues"
    RELEASES = "releases"
    COMPOSITE_DEV = "composite_dev"
    
    # Market
    PRICE = "price"
    VOLUME = "volume"
    VOLATILITY = "volatility"


class InvestmentTheme(str, Enum):
    """Investment theme classification."""
    MOMENTUM = "momentum"
    VALUE = "value"
    QUALITY = "quality"
    SENTIMENT = "sentiment"
    LIQUIDITY = "liquidity"
    DERIVATIVES = "derivatives"
    DEVELOPER = "developer"
    ONCHAIN = "onchain"


class DataFrequency(str, Enum):
    """Data update frequency."""
    REALTIME = "realtime"      # < 1 hour
    HOURLY = "hourly"          # 1-24 hours
    DAILY = "daily"            # 24 hours
    WEEKLY = "weekly"          # 7 days


class UpdatePriority(str, Enum):
    """Update priority for data freshness."""
    CRITICAL = "critical"      # Must update every cycle
    HIGH = "high"              # Update frequently
    NORMAL = "normal"          # Standard update
    LOW = "low"                # Can delay


@dataclass
class FactorClassification:
    """Complete factor classification."""
    factor_name: str
    category: str
    subcategory: str
    investment_theme: str
    data_frequency: str
    update_priority: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_name": self.factor_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "investment_theme": self.investment_theme,
            "data_frequency": self.data_frequency,
            "update_priority": self.update_priority
        }


# Predefined classification mapping
FACTOR_CLASSIFICATIONS: Dict[str, Dict[str, str]] = {
    # Derivatives
    "funding_rate": {
        "subcategory": "funding",
        "investment_theme": "derivatives",
        "data_frequency": "hourly",
        "update_priority": "critical"
    },
    "open_interest": {
        "subcategory": "open_interest",
        "investment_theme": "derivatives",
        "data_frequency": "daily",
        "update_priority": "high"
    },
    "oi_change_24h": {
        "subcategory": "open_interest",
        "investment_theme": "momentum",
        "data_frequency": "daily",
        "update_priority": "high"
    },
    
    # Onchain
    "stablecoin_net_flow": {
        "subcategory": "stablecoin",
        "investment_theme": "liquidity",
        "data_frequency": "daily",
        "update_priority": "high"
    },
    "stablecoin_total_supply": {
        "subcategory": "stablecoin",
        "investment_theme": "liquidity",
        "data_frequency": "daily",
        "update_priority": "normal"
    },
    "protocol_tvl": {
        "subcategory": "tvl",
        "investment_theme": "onchain",
        "data_frequency": "daily",
        "update_priority": "high"
    },
    "tvl_change_7d": {
        "subcategory": "tvl",
        "investment_theme": "momentum",
        "data_frequency": "daily",
        "update_priority": "normal"
    },
    
    # Social/Sentiment
    "reddit_mention_count": {
        "subcategory": "mentions",
        "investment_theme": "sentiment",
        "data_frequency": "daily",
        "update_priority": "normal"
    },
    "reddit_mention_growth": {
        "subcategory": "mentions",
        "investment_theme": "momentum",
        "data_frequency": "daily",
        "update_priority": "normal"
    },
    "reddit_sentiment_score": {
        "subcategory": "sentiment_raw",
        "investment_theme": "sentiment",
        "data_frequency": "daily",
        "update_priority": "high"
    },
    "reddit_hot_post_score": {
        "subcategory": "engagement",
        "investment_theme": "sentiment",
        "data_frequency": "daily",
        "update_priority": "low"
    },
    
    # Developer
    "github_commit_velocity": {
        "subcategory": "commits",
        "investment_theme": "developer",
        "data_frequency": "daily",
        "update_priority": "normal"
    },
    "github_contributor_growth": {
        "subcategory": "contributors",
        "investment_theme": "developer",
        "data_frequency": "daily",
        "update_priority": "normal"
    },
    "github_issue_activity": {
        "subcategory": "issues",
        "investment_theme": "developer",
        "data_frequency": "daily",
        "update_priority": "low"
    },
    "github_release_frequency": {
        "subcategory": "releases",
        "investment_theme": "developer",
        "data_frequency": "weekly",
        "update_priority": "low"
    },
    "developer_activity_score": {
        "subcategory": "composite_dev",
        "investment_theme": "developer",
        "data_frequency": "daily",
        "update_priority": "normal"
    }
}


class FactorClassifier:
    """Classifies and organizes factors by category hierarchy."""
    
    def __init__(self):
        self._classifications: Dict[str, FactorClassification] = {}
        self._build_classifications()
    
    def _build_classifications(self):
        """Build classification for all registered factors."""
        registry.discover_factors()
        
        for name, meta in registry._factors.items():
            predefined = FACTOR_CLASSIFICATIONS.get(name, {})
            
            classification = FactorClassification(
                factor_name=name,
                category=meta.category.value,
                subcategory=predefined.get("subcategory", "general"),
                investment_theme=predefined.get("investment_theme", meta.category.value),
                data_frequency=predefined.get("data_frequency", "daily"),
                update_priority=predefined.get("update_priority", "normal")
            )
            
            self._classifications[name] = classification
    
    def get_classification(self, factor_name: str) -> FactorClassification:
        """Get classification for a factor."""
        return self._classifications.get(factor_name)
    
    def get_by_category(self, category: str) -> List[FactorClassification]:
        """Get all factors in a category."""
        return [c for c in self._classifications.values() if c.category == category]
    
    def get_by_subcategory(self, subcategory: str) -> List[FactorClassification]:
        """Get all factors in a subcategory."""
        return [c for c in self._classifications.values() if c.subcategory == subcategory]
    
    def get_by_theme(self, theme: str) -> List[FactorClassification]:
        """Get all factors for an investment theme."""
        return [c for c in self._classifications.values() if c.investment_theme == theme]
    
    def get_category_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary: category → subcategory → count."""
        summary = {}
        
        for c in self._classifications.values():
            if c.category not in summary:
                summary[c.category] = {}
            
            if c.subcategory not in summary[c.category]:
                summary[c.category][c.subcategory] = 0
            
            summary[c.category][c.subcategory] += 1
        
        return summary
    
    def get_theme_distribution(self) -> Dict[str, int]:
        """Get factor count by investment theme."""
        distribution = {}
        
        for c in self._classifications.values():
            theme = c.investment_theme
            distribution[theme] = distribution.get(theme, 0) + 1
        
        return distribution
    
    def export_classification_table(self) -> List[Dict[str, Any]]:
        """Export all classifications as table."""
        return [c.to_dict() for c in self._classifications.values()]


def classify_all_factors() -> Dict[str, FactorClassification]:
    """Classify all registered factors."""
    classifier = FactorClassifier()
    return classifier._classifications
