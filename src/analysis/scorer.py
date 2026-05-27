"""Project scoring system."""
from typing import Any, Dict, Optional
from src.data.models import (
    ProjectScore, CoinData, TechnicalIndicators,
    SentimentData, OnchainData, GithubData
)
from src.api.coingecko import CoinGeckoClient
from src.analysis.technical import TechnicalAnalyzer
from src.data.coin_mappings import COIN_TO_SYMBOL


class Scorer:
    """Project comprehensive scoring system.

    This class calculates weighted scores for cryptocurrency projects
    based on multiple analysis dimensions.

    Attributes:
        weights: Weight configuration for each dimension
        coingecko: CoinGecko API client for market data
        technical: Technical analyzer for price indicators
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

    def __init__(
        self,
        custom_weights: Optional[Dict[str, float]] = None,
        coingecko_client: Optional[CoinGeckoClient] = None,
        technical_analyzer: Optional[TechnicalAnalyzer] = None
    ):
        """Initialize scorer with optional custom weights and dependencies.

        Args:
            custom_weights: Custom weight configuration (optional)
            coingecko_client: CoinGecko API client instance (optional)
            technical_analyzer: Technical analyzer instance (optional)
        """
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()
        self.coingecko = coingecko_client or CoinGeckoClient()
        self.technical = technical_analyzer or TechnicalAnalyzer()

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

    def score_project(self, coin_id: str) -> ProjectScore:
        """Generate comprehensive project score.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            ProjectScore object with all scoring data
        """
        # 获取各维度数据
        market_data = self._get_market_data(coin_id)
        technical = self._get_technical_indicators(coin_id)
        onchain = self._get_onchain_data(coin_id)
        sentiment = self._get_sentiment_data(coin_id)
        github = self._get_github_data(coin_id)
        social = self._get_social_data(coin_id)
        risk = self._get_risk_data(coin_id)

        # 计算各维度评分
        scores = {
            'market': self._score_market(market_data),
            'technical': self._score_technical(technical),
            'onchain': onchain.onchain_signal if onchain else 3,
            'sentiment': sentiment.sentiment_signal if sentiment else 3,
            'github': github.activity_score if github else 3,
            'social': social.social_score if social else 3,
            'risk': risk.risk_score if risk else 3
        }

        # 计算加权总分
        total_score = self.calculate_weighted_score(scores)

        # 生成评级和建议
        rating = self.generate_rating(total_score)
        recommendation = self.generate_recommendation(rating)
        risk_level = self.determine_risk_level(rating)

        return ProjectScore(
            coin_id=coin_id,
            coin_name=market_data.name if market_data else coin_id,
            symbol=market_data.symbol.upper() if market_data else coin_id.upper(),
            market_score=scores['market'],
            technical_score=scores['technical'],
            onchain_score=scores['onchain'],
            sentiment_score=scores['sentiment'],
            github_score=scores['github'],
            social_score=scores['social'],
            risk_score=scores['risk'],
            total_score=total_score,
            rating=rating,
            recommendation=recommendation,
            risk_level=risk_level
        )

    def _score_market(self, market_data: Optional[CoinData]) -> int:
        """Score market data (1-5)."""
        if not market_data:
            return 3

        score = 3
        # 市值排名
        if market_data.market_cap_rank == 1:
            score = 5
        elif market_data.market_cap_rank <= 10:
            score = 4
        elif market_data.market_cap_rank <= 50:
            score = 3
        elif market_data.market_cap_rank <= 100:
            score = 2
        else:
            score = 1

        return score

    def _score_technical(self, technical: Optional[TechnicalIndicators]) -> int:
        """Score technical indicators (average of all signals)."""
        if not technical:
            return 3

        signals = [
            technical.rsi_signal,
            technical.ma_signal,
            technical.trend_signal,
            technical.volume_signal
        ]
        return int(sum(signals) / len(signals))

    # Placeholder methods for data fetching
    def _get_market_data(self, coin_id: str) -> Optional[CoinData]:
        """Fetch market data for coin from CoinGecko.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            CoinData object or None if fetch fails
        """
        try:
            data = self.coingecko.get_coin_data(coin_id)
            return CoinData(
                id=data["id"],
                symbol=data["symbol"],
                name=data["name"],
                current_price=data.get("current_price", 0),
                market_cap=data.get("market_cap", 0),
                market_cap_rank=data.get("market_cap_rank", 999),
                total_volume=data.get("total_volume"),
                circulating_supply=data.get("circulating_supply"),
                total_supply=data.get("total_supply"),
                max_supply=data.get("max_supply"),
                price_change_24h=data.get("price_change_24h"),
                price_change_percentage_24h=data.get("price_change_percentage_24h")
            )
        except Exception as e:
            print(f"Warning: Failed to fetch market data for {coin_id}: {e}")
            return None

    def _get_technical_indicators(self, coin_id: str) -> Optional[TechnicalIndicators]:
        """Fetch technical indicators for coin using TechnicalAnalyzer.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            TechnicalIndicators object or None if fetch fails
        """
        # Get trading symbol from mapping
        symbol = COIN_TO_SYMBOL.get(coin_id, f"{coin_id.upper()}/USDT")

        # Get market cap for volume ratio calculation
        market_data = self._get_market_data(coin_id)
        market_cap = market_data.market_cap if market_data else None

        try:
            return self.technical.analyze(symbol, days=200, market_cap=market_cap)
        except Exception as e:
            print(f"Warning: Failed to fetch technical indicators for {coin_id}: {e}")
            return None

    def _get_onchain_data(self, coin_id: str) -> Optional[OnchainData]:
        """Fetch onchain data for coin."""
        # TODO: Implement with existing onchain analysis module
        return None

    def _get_sentiment_data(self, coin_id: str) -> Optional[SentimentData]:
        """Fetch sentiment data for coin."""
        # TODO: Implement with existing sentiment analysis module
        return None

    def _get_github_data(self, coin_id: str) -> Optional[GithubData]:
        """Fetch GitHub data for coin."""
        # TODO: Implement with existing GitHub analysis module
        return None

    def _get_social_data(self, coin_id: str) -> Optional[Any]:
        """Fetch social media data for coin."""
        # TODO: Implement with CoinGecko community data
        return None

    def _get_risk_data(self, coin_id: str) -> Optional[Any]:
        """Fetch risk data for coin."""
        # TODO: Implement risk assessment
        return None