"""Hierarchical Factor Weighting System.

Implements Category Weight → Factor Weight hierarchy.

Instead of averaging all factors equally:
1. Assign weight to each category
2. Distribute category weight among factors

Example:
    Sentiment: 20% total
    → reddit_mention_count: 40% of Sentiment = 8%
    → reddit_sentiment_score: 60% of Sentiment = 12%
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from src.factors import registry
from src.research.classification import FactorClassifier, InvestmentTheme


# Default category weights (must sum to 100)
DEFAULT_CATEGORY_WEIGHTS: Dict[str, float] = {
    "derivatives": 25.0,
    "onchain": 20.0,
    "social": 15.0,
    "developer": 15.0,
    "market": 10.0,
    "technical": 10.0,
    "sentiment": 5.0
}

# Default factor weights within categories (must sum to 100 within each category)
DEFAULT_FACTOR_WEIGHTS: Dict[str, Dict[str, float]] = {
    "derivatives": {
        "funding_rate": 40.0,
        "open_interest": 30.0,
        "oi_change_24h": 30.0
    },
    "onchain": {
        "stablecoin_net_flow": 30.0,
        "stablecoin_total_supply": 20.0,
        "protocol_tvl": 30.0,
        "tvl_change_7d": 20.0
    },
    "social": {
        "reddit_mention_count": 25.0,
        "reddit_mention_growth": 25.0,
        "reddit_sentiment_score": 30.0,
        "reddit_hot_post_score": 20.0
    },
    "developer": {
        "github_commit_velocity": 25.0,
        "github_contributor_growth": 20.0,
        "github_issue_activity": 15.0,
        "github_release_frequency": 15.0,
        "developer_activity_score": 25.0
    }
}

# Theme weights for investment style
THEME_WEIGHTS: Dict[str, Dict[str, float]] = {
    "balanced": {
        "momentum": 20.0,
        "derivatives": 25.0,
        "sentiment": 15.0,
        "developer": 15.0,
        "liquidity": 15.0,
        "onchain": 10.0
    },
    "momentum_focused": {
        "momentum": 35.0,
        "derivatives": 25.0,
        "sentiment": 20.0,
        "developer": 10.0,
        "liquidity": 5.0,
        "onchain": 5.0
    },
    "fundamental": {
        "momentum": 10.0,
        "derivatives": 15.0,
        "sentiment": 10.0,
        "developer": 30.0,
        "liquidity": 20.0,
        "onchain": 15.0
    }
}


@dataclass
class WeightedFactor:
    """A factor with its computed weight."""
    factor_name: str
    category: str
    category_weight: float
    factor_weight_within_category: float
    effective_weight: float  # category_weight * factor_weight


class HierarchicalWeighting:
    """Manages hierarchical factor weights."""

    def __init__(
        self,
        category_weights: Dict[str, float] = None,
        factor_weights: Dict[str, Dict[str, float]] = None
    ):
        self.classifier = FactorClassifier()
        self.category_weights = category_weights or DEFAULT_CATEGORY_WEIGHTS.copy()
        self.factor_weights = factor_weights or DEFAULT_FACTOR_WEIGHTS.copy()

    def get_factor_weight(self, factor_name: str) -> float:
        """Calculate effective weight for a factor.

        effective_weight = category_weight * (factor_weight_in_category / 100)
        """
        classification = self.classifier.get_classification(factor_name)
        if not classification:
            return 0.0

        category = classification.category
        category_weight = self.category_weights.get(category, 0.0)

        # Get factor weight within category
        factor_weights_in_cat = self.factor_weights.get(category, {})
        factor_weight = factor_weights_in_cat.get(factor_name, 0.0)

        # If factor not in weights, distribute equally
        if factor_weight == 0.0 and factor_weights_in_cat:
            factor_weight = 100.0 / len(factor_weights_in_cat)

        # Calculate effective weight
        effective = (category_weight * factor_weight) / 100.0
        return effective

    def get_all_weights(self) -> Dict[str, float]:
        """Get effective weights for all factors."""
        weights = {}
        for name in self.classifier._classifications.keys():
            weights[name] = self.get_factor_weight(name)
        return weights

    def get_weighted_factors(self) -> List[WeightedFactor]:
        """Get list of weighted factors."""
        weighted = []
        for name, classification in self.classifier._classifications.items():
            category = classification.category
            category_weight = self.category_weights.get(category, 0.0)

            factor_weights_in_cat = self.factor_weights.get(category, {})
            factor_weight = factor_weights_in_cat.get(name, 0.0)

            effective = self.get_factor_weight(name)

            weighted.append(WeightedFactor(
                factor_name=name,
                category=category,
                category_weight=category_weight,
                factor_weight_within_category=factor_weight,
                effective_weight=effective
            ))

        return sorted(weighted, key=lambda x: -x.effective_weight)

    def normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Normalize weights to sum to 100."""
        total = sum(weights.values())
        if total == 0:
            return weights

        return {k: (v / total) * 100.0 for k, v in weights.items()}

    def set_category_weights(self, weights: Dict[str, float]):
        """Set category weights (will be normalized)."""
        self.category_weights = self.normalize_weights(weights)

    def set_factor_weights(self, category: str, weights: Dict[str, float]):
        """Set factor weights for a category."""
        self.factor_weights[category] = self.normalize_weights(weights)

    def apply_theme_weights(self, theme: str = "balanced"):
        """Apply predefined theme weights."""
        if theme in THEME_WEIGHTS:
            self.category_weights = THEME_WEIGHTS[theme].copy()

    def get_category_summary(self) -> Dict[str, Any]:
        """Get weight summary by category."""
        summary = {}
        for cat, weight in self.category_weights.items():
            factors_in_cat = self.factor_weights.get(cat, {})
            summary[cat] = {
                "category_weight": weight,
                "num_factors": len(factors_in_cat),
                "factors": factors_in_cat
            }
        return summary

    def compute_weighted_score(
        self,
        factor_scores: Dict[str, float]
    ) -> float:
        """Compute weighted average score from factor scores.

        Args:
            factor_scores: Dict of factor_name -> score (0-1 or 1-5)

        Returns:
            Weighted average score
        """
        weights = self.get_all_weights()
        total_weight = 0.0
        weighted_sum = 0.0

        for factor_name, score in factor_scores.items():
            weight = weights.get(factor_name, 0.0)
            if weight > 0:
                weighted_sum += score * weight
                total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def export_weight_table(self) -> List[Dict[str, Any]]:
        """Export weight table for reporting."""
        weighted_factors = self.get_weighted_factors()
        return [wf.__dict__ for wf in weighted_factors]
