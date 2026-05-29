"""Project scoring system."""
from typing import Any, Dict, Optional, List
from src.data.models import (
    ProjectScore, CoinData, TechnicalIndicators,
    SentimentData, OnchainData, GithubData, SocialData, RiskData,
    # New models (Phase 1)
    FundingRateData, OpenInterestData, StablecoinFlowData, TVLData, DerivativesData
)
from src.api.coingecko import CoinGeckoClient
from src.api.coinglass import CoinglassClient
from src.api.defillama import DefiLlamaClient
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.onchain import OnchainAnalyzer
from src.analysis.github_analyzer import GithubAnalyzer
from src.data.coin_mappings import COIN_TO_SYMBOL, COIN_TO_REPO


class Scorer:
    """Project comprehensive scoring system.

    This class calculates weighted scores for cryptocurrency projects
    based on multiple analysis dimensions.

    Attributes:
        weights: Weight configuration for each dimension
        coingecko: CoinGecko API client for market data
        coinglass: Coinglass API client for funding/OI data
        defillama: DefiLlama API client for stablecoin/TVL data
        technical: Technical analyzer for price indicators
        sentiment: Sentiment analyzer for market mood
        onchain: Onchain analyzer for blockchain data
        github: GitHub activity analyzer
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

    # New weights for Phase 1 (optional, can be enabled later)
    PHASE1_WEIGHTS = {
        'market': 0.15,
        'technical': 0.12,
        'funding': 0.10,
        'open_interest': 0.10,
        'stablecoin_flow': 0.08,
        'onchain': 0.10,
        'sentiment': 0.08,
        'github': 0.10,
        'tvl': 0.05,
        'social': 0.05,
        'risk': 0.07
    }

    def __init__(
        self,
        custom_weights: Optional[Dict[str, float]] = None,
        coingecko_client: Optional[CoinGeckoClient] = None,
        coinglass_client: Optional[CoinglassClient] = None,
        defillama_client: Optional[DefiLlamaClient] = None,
        technical_analyzer: Optional[TechnicalAnalyzer] = None,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        onchain_analyzer: Optional[OnchainAnalyzer] = None,
        github_analyzer: Optional[GithubAnalyzer] = None,
        enable_phase1: bool = False
    ):
        """Initialize scorer with optional custom weights and dependencies.

        Args:
            custom_weights: Custom weight configuration (optional)
            coingecko_client: CoinGecko API client instance (optional)
            coinglass_client: Coinglass API client instance (optional)
            defillama_client: DefiLlama API client instance (optional)
            technical_analyzer: Technical analyzer instance (optional)
            sentiment_analyzer: Sentiment analyzer instance (optional)
            onchain_analyzer: Onchain analyzer instance (optional)
            github_analyzer: GitHub analyzer instance (optional)
            enable_phase1: Enable Phase 1 data sources (funding, OI, stablecoin, TVL)
        """
        # Use Phase 1 weights if enabled
        if enable_phase1:
            self.weights = custom_weights or self.PHASE1_WEIGHTS.copy()
        else:
            self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()

        self._validate_weights()

        # Initialize API clients
        self.coingecko = coingecko_client or CoinGeckoClient()
        self.coinglass = coinglass_client or CoinglassClient()
        self.defillama = defillama_client or DefiLlamaClient()

        # Initialize analyzers
        self.technical = technical_analyzer or TechnicalAnalyzer()
        self.sentiment = sentiment_analyzer or SentimentAnalyzer()
        self.onchain = onchain_analyzer or OnchainAnalyzer()
        self.github = github_analyzer or GithubAnalyzer()

        # Flag for Phase 1 features
        self.enable_phase1 = enable_phase1

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

    def calculate_factor_contributions(self, scores: Dict[str, int]) -> Dict[str, Dict]:
        """Calculate each factor's contribution to total score.

        Args:
            scores: Dictionary of dimension scores (1-5)

        Returns:
            Dict mapping factor name to {raw_score, weight, weighted_score, contribution_pct}
        """
        # 检查缺失的维度
        missing_dims = [dim for dim in self.weights if dim not in scores]

        # 如果有缺失维度，重新分配权重
        if missing_dims:
            adjusted_weights = self._redistribute_weights(missing_dims)
        else:
            adjusted_weights = self.weights.copy()

        # 计算每个因子的加权得分和总加权得分
        total_weighted_score = 0.0
        weighted_scores = {}

        for dim, score in scores.items():
            if dim in adjusted_weights:
                weight = adjusted_weights[dim]
                weighted_score = score * weight
                weighted_scores[dim] = weighted_score
                total_weighted_score += weighted_score

        # 计算贡献百分比
        contributions = {}
        for dim, score in scores.items():
            if dim in adjusted_weights:
                weight = adjusted_weights[dim]
                ws = weighted_scores[dim]
                contribution_pct = (ws / total_weighted_score * 100) if total_weighted_score > 0 else 0

                contributions[dim] = {
                    "raw_score": score,
                    "weight": round(weight, 3),
                    "weighted_score": round(ws, 3),
                    "contribution_pct": round(contribution_pct, 1)
                }

        return contributions

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

        # 计算因子贡献
        factor_contributions = self.calculate_factor_contributions(scores)

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
            risk_level=risk_level,
            factor_contributions=factor_contributions
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
        """Fetch onchain data for coin using OnchainAnalyzer.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            OnchainData object or None if fetch fails
        """
        try:
            return self.onchain.analyze(coin_id)
        except Exception as e:
            print(f"Warning: Failed to fetch onchain data for {coin_id}: {e}")
            return None

    def _get_sentiment_data(self, coin_id: str) -> Optional[SentimentData]:
        """Fetch sentiment data for coin using SentimentAnalyzer.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            SentimentData object or None if fetch fails
        """
        try:
            return self.sentiment.analyze(coin_id)
        except Exception as e:
            print(f"Warning: Failed to fetch sentiment data for {coin_id}: {e}")
            return None

    def _get_github_data(self, coin_id: str) -> Optional[GithubData]:
        """Fetch GitHub activity data for coin using GithubAnalyzer.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            GithubData object or None if fetch fails or no repo found
        """
        repo_path = COIN_TO_REPO.get(coin_id)
        if not repo_path:
            return None

        try:
            return self.github.analyze(coin_id, repo_path)
        except Exception as e:
            print(f"Warning: Failed to fetch GitHub data for {coin_id}: {e}")
            return None

    def _get_social_data(self, coin_id: str) -> Optional[SocialData]:
        """Fetch social media data for coin from CoinGecko.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            SocialData object or None if fetch fails
        """
        try:
            data = self.coingecko.get_coin_community_data(coin_id)

            twitter = data.get("twitter_followers") or 0
            reddit = data.get("reddit_subscribers") or 0
            total = twitter + reddit

            # Score based on total followers
            if total > 5000000:
                score = 5
            elif total > 1000000:
                score = 4
            elif total > 100000:
                score = 3
            elif total > 10000:
                score = 2
            else:
                score = 1

            return SocialData(
                twitter_followers=data.get("twitter_followers"),
                reddit_subscribers=data.get("reddit_subscribers"),
                telegram_users=data.get("telegram_users"),
                github_forks=data.get("github_forks"),
                github_stars=data.get("github_stars"),
                social_score=score
            )
        except Exception as e:
            print(f"Warning: Failed to fetch social data for {coin_id}: {e}")
            return None

    def _get_risk_data(self, coin_id: str) -> Optional[RiskData]:
        """Calculate risk assessment for coin based on market data.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            RiskData object with volatility, liquidity, and maturity scores
        """
        market_data = self._get_market_data(coin_id)
        risk_factors: List[str] = []

        # Volatility risk (from price change)
        volatility_score = 3
        if market_data and market_data.price_change_percentage_24h:
            change = abs(market_data.price_change_percentage_24h)
            if change > 20:
                volatility_score = 1
                risk_factors.append("High 24h volatility")
            elif change > 10:
                volatility_score = 2
            elif change < 5:
                volatility_score = 4

        # Liquidity risk (from volume/market cap ratio)
        liquidity_score = 3
        if market_data and market_data.total_volume and market_data.market_cap:
            ratio = market_data.total_volume / market_data.market_cap
            if ratio > 0.1:
                liquidity_score = 5
            elif ratio > 0.05:
                liquidity_score = 4
            elif ratio < 0.01:
                liquidity_score = 2
                risk_factors.append("Low liquidity")

        # Maturity risk (from market cap rank)
        maturity_score = 3
        if market_data:
            rank = market_data.market_cap_rank or 999
            if rank <= 10:
                maturity_score = 5
            elif rank <= 50:
                maturity_score = 4
            elif rank > 200:
                maturity_score = 2
                risk_factors.append("Low market cap")

        # Calculate overall risk score
        risk_score = int((volatility_score + liquidity_score + maturity_score) / 3)

        return RiskData(
            volatility_score=volatility_score,
            liquidity_score=liquidity_score,
            maturity_score=maturity_score,
            risk_score=risk_score,
            risk_factors=risk_factors
        )

    # ==================== Phase 1: New Data Fetching Methods ====================

    def _get_funding_rate(self, coin_id: str) -> Optional[FundingRateData]:
        """Fetch funding rate data for coin using Coinglass API.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            FundingRateData object or None if fetch fails
        """
        if not self.enable_phase1:
            return None

        try:
            data = self.coinglass.get_funding_rate(coin_id)
            avg_rate = data.get("avg_funding_rate", 0)

            funding_signal = self.coinglass.score_funding_rate(avg_rate)

            return FundingRateData(
                symbol=data.get("symbol", ""),
                coin_id=coin_id,
                avg_funding_rate=avg_rate,
                funding_rate_change=data.get("funding_rate_change", 0),
                exchanges=data.get("exchanges", []),
                funding_signal=funding_signal
            )
        except Exception as e:
            print(f"Warning: Failed to fetch funding rate for {coin_id}: {e}")
            return None

    def _get_open_interest(self, coin_id: str) -> Optional[OpenInterestData]:
        """Fetch open interest data for coin using Coinglass API.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            OpenInterestData object or None if fetch fails
        """
        if not self.enable_phase1:
            return None

        try:
            data = self.coinglass.get_open_interest(coin_id)
            oi_change = data.get("oi_change_24h", 0)

            oi_signal = self.coinglass.score_open_interest(oi_change)

            return OpenInterestData(
                symbol=data.get("symbol", ""),
                coin_id=coin_id,
                total_open_interest=data.get("total_open_interest", 0),
                oi_change_24h=oi_change,
                oi_change_7d=data.get("oi_change_7d", 0),
                exchanges=data.get("exchanges", []),
                oi_signal=oi_signal
            )
        except Exception as e:
            print(f"Warning: Failed to fetch open interest for {coin_id}: {e}")
            return None

    def _get_stablecoin_flow(self) -> Optional[StablecoinFlowData]:
        """Fetch global stablecoin flow data using DefiLlama API.

        Returns:
            StablecoinFlowData object or None if fetch fails
        """
        if not self.enable_phase1:
            return None

        try:
            data = self.defillama.get_stablecoin_flows()
            net_flow = data.get("net_flows_24h", 0)

            flow_signal = self.defillama.score_stablecoin_flow(net_flow)

            return StablecoinFlowData(
                total_supply=data.get("total_supply", 0),
                net_flows_24h=net_flow,
                chain_distribution=data.get("chain_distribution", {}),
                stablecoins=data.get("stablecoins", []),
                flow_signal=flow_signal
            )
        except Exception as e:
            print(f"Warning: Failed to fetch stablecoin flow: {e}")
            return None

    def _get_tvl(self, coin_id: str) -> Optional[TVLData]:
        """Fetch TVL data for DeFi protocol using DefiLlama API.

        Args:
            coin_id: Cryptocurrency ID (e.g., 'uniswap')

        Returns:
            TVLData object or None if fetch fails or protocol not found
        """
        if not self.enable_phase1:
            return None

        protocol_slug = self.defillama.get_protocol_slug(coin_id)
        if not protocol_slug:
            return None

        try:
            data = self.defillama.get_protocol_tvl(protocol_slug)
            tvl_change_7d = data.get("tvl_change_7d", 0)

            tvl_signal = self.defillama.score_tvl_change(tvl_change_7d)

            return TVLData(
                protocol=data.get("protocol", protocol_slug),
                slug=protocol_slug,
                tvl=data.get("tvl", 0),
                tvl_change_24h=data.get("tvl_change_24h", 0),
                tvl_change_7d=tvl_change_7d,
                chain_breakdown=data.get("chain_breakdown", {}),
                tvl_signal=tvl_signal
            )
        except Exception as e:
            print(f"Warning: Failed to fetch TVL for {coin_id}: {e}")
            return None

    def score_project_with_phase1(self, coin_id: str) -> Dict[str, Any]:
        """Generate comprehensive project score with Phase 1 data sources.

        This method extends score_project() to include new dimensions:
        - funding_rate
        - open_interest
        - stablecoin_flow
        - tvl

        Args:
            coin_id: Cryptocurrency ID (e.g., 'bitcoin')

        Returns:
            Dictionary with ProjectScore and new Phase 1 data
        """
        # Get base score from existing method
        base_score = self.score_project(coin_id)

        # Get Phase 1 data
        funding = self._get_funding_rate(coin_id)
        open_interest = self._get_open_interest(coin_id)
        stablecoin = self._get_stablecoin_flow()
        tvl = self._get_tvl(coin_id)

        return {
            "base_score": base_score,
            "phase1_data": {
                "funding_rate": funding,
                "open_interest": open_interest,
                "stablecoin_flow": stablecoin,
                "tvl": tvl
            }
        }