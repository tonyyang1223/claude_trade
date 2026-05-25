"""Project scoring system."""
from typing import Dict, Optional


class Scorer:
    """Project comprehensive scoring system.

    This class calculates weighted scores for cryptocurrency projects
    based on multiple analysis dimensions.

    Attributes:
        weights: Weight configuration for each dimension
    """

    DEFAULT_WEIGHTS = {
        'market': 0.20,
        'technical': 0.15,
        'onchain': 0.20,
        'sentiment': 0.10,
        'github': 0.10,
        'social': 0.10,
        'risk': 0.15
    }

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """Initialize scorer with optional custom weights.

        Args:
            custom_weights: Custom weight configuration (optional)
        """
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Validate that weights sum to 1.0."""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def generate_rating(self, total_score: float) -> str:
        """Generate rating based on total score.

        Args:
            total_score: Weighted total score (0-100)

        Returns:
            Rating string (A+/A/B/C/D/F)
        """
        if total_score < 0 or total_score > 100:
            raise ValueError(f"total_score must be between 0 and 100, got {total_score}")
        if total_score >= 90:
            return 'A+'
        elif total_score >= 80:
            return 'A'
        elif total_score >= 70:
            return 'B'
        elif total_score >= 60:
            return 'C'
        elif total_score >= 50:
            return 'D'
        else:
            return 'F'
