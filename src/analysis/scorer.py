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

    def generate_recommendation(self, rating: str) -> str:
        """Generate investment recommendation based on rating.

        Args:
            rating: Project rating (A+/A/B/C/D/F)

        Returns:
            Investment recommendation text
        """
        recommendations = {
            'A+': '强烈建议关注，项目综合表现优秀，风险较低',
            'A': '建议关注，项目综合表现良好，风险可控',
            'B': '可考虑投资，项目表现中等，需要关注风险',
            'C': '谨慎观望，项目表现一般，存在一定风险',
            'D': '暂不推荐，项目表现较差，风险较高',
            'F': '不推荐投资，项目表现不佳，风险很高'
        }
        return recommendations.get(rating, '无法生成建议')

    def determine_risk_level(self, rating: str) -> str:
        """Determine risk level based on rating.

        Args:
            rating: Project rating (A+/A/B/C/D/F)

        Returns:
            Risk level (low/medium/high)

        Raises:
            ValueError: If rating is not a valid rating string
        """
        valid_ratings = ['A+', 'A', 'B', 'C', 'D', 'F']
        if rating not in valid_ratings:
            raise ValueError(f"Invalid rating: {rating}")
        if rating in ['A+', 'A']:
            return 'low'
        elif rating in ['B', 'C']:
            return 'medium'
        else:
            return 'high'

    def calculate_weighted_score(self, scores: Dict[str, int]) -> float:
        """Calculate weighted total score.

        Automatically redistributes weights if some dimensions are missing.

        Args:
            scores: Dictionary of dimension scores (1-5)

        Returns:
            Weighted total score (0-100)
        """
        # 检查缺失的维度
        missing_dims = [dim for dim in self.weights if dim not in scores]

        # 如果有缺失维度，重新分配权重
        if missing_dims:
            adjusted_weights = self._redistribute_weights(missing_dims)
        else:
            adjusted_weights = self.weights.copy()

        # 计算加权平均分 (1-5分制)
        weighted_sum = 0.0
        total_weight = 0.0

        for dim, score in scores.items():
            if dim in adjusted_weights:
                weighted_sum += score * adjusted_weights[dim]
                total_weight += adjusted_weights[dim]

        # 转换为100分制
        if total_weight > 0:
            avg_score = weighted_sum / total_weight
            return avg_score * 20  # 5分制转100分制
        else:
            return 0.0

    def _redistribute_weights(self, missing_dims: list) -> Dict[str, float]:
        """Redistribute weights when dimensions are missing.

        Args:
            missing_dims: List of missing dimension names

        Returns:
            Adjusted weight dictionary
        """
        adjusted = self.weights.copy()
        missing_weight = sum(adjusted[dim] for dim in missing_dims)

        # 移除缺失维度的权重
        for dim in missing_dims:
            del adjusted[dim]

        # 归一化剩余权重
        if adjusted:
            total_remaining = sum(adjusted.values())
            if total_remaining > 0:
                factor = 1.0 / total_remaining
                for dim in adjusted:
                    adjusted[dim] *= factor

        return adjusted