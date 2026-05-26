"""Project comparison engine."""
from datetime import datetime
from typing import List, Dict, Optional

from src.data.models import ProjectScore, ComparisonReport
from src.analysis.scorer import Scorer


class ProjectComparator:
    """Compare multiple cryptocurrency projects.

    This class provides comprehensive comparison functionality
    for analyzing multiple projects side by side.
    """

    DIMENSIONS = [
        ('market', '市场数据', 20),
        ('technical', '技术指标', 15),
        ('onchain', '链上分析', 20),
        ('sentiment', '市场情绪', 10),
        ('github', 'GitHub活动', 10),
        ('social', '社交媒体', 10),
        ('risk', '风险评估', 15)
    ]

    def __init__(self, scorer: Optional[Scorer] = None):
        """Initialize comparator with optional scorer.

        Args:
            scorer: Scorer instance for generating project scores
        """
        self.scorer = scorer or Scorer()

    def compare_projects(self, coin_ids: List[str]) -> ComparisonReport:
        """Compare multiple cryptocurrency projects.

        Args:
            coin_ids: List of cryptocurrency IDs (2-5 projects recommended)

        Returns:
            ComparisonReport with comprehensive comparison data

        Raises:
            ValueError: If less than 2 or more than 5 projects provided
        """
        if len(coin_ids) < 2:
            raise ValueError("At least 2 projects required for comparison")

        if len(coin_ids) > 5:
            raise ValueError("Maximum 5 projects can be compared")

        # Score all projects
        scores = []
        for coin_id in coin_ids:
            score = self.scorer.score_project(coin_id)
            scores.append(score)

        # Build comparison matrix
        comparison_matrix = self.build_comparison_matrix(scores)

        # Determine winner (highest total score)
        winner = max(scores, key=lambda s: s.total_score).coin_id

        # Generate analysis summary
        analysis_summary = self._generate_analysis_summary(scores, winner)

        return ComparisonReport(
            projects=scores,
            comparison_matrix=comparison_matrix,
            winner=winner,
            analysis_summary=analysis_summary,
            created_at=datetime.now()
        )

    def build_comparison_matrix(self, scores: List[ProjectScore]) -> Dict:
        """Build comparison matrix from project scores.

        Args:
            scores: List of ProjectScore objects

        Returns:
            Dictionary with comparison data for each project
        """
        matrix = {}

        for score in scores:
            matrix[score.coin_id] = {
                'market': score.market_score,
                'technical': score.technical_score,
                'onchain': score.onchain_score,
                'sentiment': score.sentiment_score,
                'github': score.github_score,
                'social': score.social_score,
                'risk': score.risk_score,
                'total': score.total_score,
                'rating': score.rating
            }

        return matrix

    def _generate_analysis_summary(self, scores: List[ProjectScore], winner: str) -> str:
        """Generate analysis summary for comparison report.

        Args:
            scores: List of ProjectScore objects
            winner: Winning project ID

        Returns:
            Analysis summary text
        """
        winner_score = next(s for s in scores if s.coin_id == winner)

        summary_parts = []

        # Overall winner statement
        summary_parts.append(
            f"<strong>{winner_score.coin_name} ({winner_score.symbol})</strong> "
            f"在综合评分上领先，得分为 {winner_score.total_score:.1f} 分，"
            f"评级为 {winner_score.rating}。\n"
        )

        # Score differences
        for score in scores:
            if score.coin_id != winner:
                diff = winner_score.total_score - score.total_score
                summary_parts.append(
                    f"- {score.coin_name} ({score.symbol}): {score.total_score:.1f} 分，"
                    f"相差 {diff:.1f} 分，评级 {score.rating}\n"
                )

        # Dimension analysis
        summary_parts.append("\n<strong>各维度对比分析：</strong>\n")

        for dim_key, dim_name, weight in self.DIMENSIONS:
            dim_scores = []
            for score in scores:
                attr_name = f'{dim_key}_score'
                dim_value = getattr(score, attr_name)
                dim_scores.append((score.coin_name, score.symbol, dim_value))

            # Find best performer in this dimension
            best = max(dim_scores, key=lambda x: x[2])
            worst = min(dim_scores, key=lambda x: x[2])

            summary_parts.append(
                f"- {dim_name} (权重{weight}%): "
                f"{best[0]} 领先 ({best[2]}/5)，"
                f"{worst[0]} 较弱 ({worst[2]}/5)\n"
            )

        # Strengths and weaknesses of winner
        summary_parts.append(f"\n<strong>{winner_score.coin_name} 的优势与劣势：</strong>\n")

        strengths = []
        weaknesses = []

        for dim_key, dim_name, _ in self.DIMENSIONS:
            attr_name = f'{dim_key}_score'
            value = getattr(winner_score, attr_name)
            if value >= 4:
                strengths.append(f"{dim_name}({value}/5)")
            elif value <= 2:
                weaknesses.append(f"{dim_name}({value}/5)")

        if strengths:
            summary_parts.append(f"- 优势: {', '.join(strengths)}\n")
        else:
            summary_parts.append("- 优势: 无明显优势\n")

        if weaknesses:
            summary_parts.append(f"- 劣势: {', '.join(weaknesses)}\n")
        else:
            summary_parts.append("- 劣势: 无明显劣势\n")

        # Investment recommendation
        summary_parts.append("\n<strong>投资建议：</strong>\n")
        summary_parts.append(
            f"综合分析，推荐关注 {winner_score.coin_name}。"
            f"风险等级: {winner_score.risk_level}。"
            f"{winner_score.recommendation}\n"
        )

        # Additional notes
        summary_parts.append("\n<strong>备注：</strong>\n")
        summary_parts.append(
            "本报告基于当前可获取的数据生成，投资决策需结合市场实时情况。"
            "建议分散投资，控制风险。"
        )

        return ''.join(summary_parts)

    def get_dimension_rankings(self, scores: List[ProjectScore]) -> Dict[str, List]:
        """Get rankings for each dimension.

        Args:
            scores: List of ProjectScore objects

        Returns:
            Dictionary with rankings for each dimension
        """
        rankings = {}

        for dim_key, dim_name, _ in self.DIMENSIONS:
            attr_name = f'{dim_key}_score'
            ranked = sorted(
                scores,
                key=lambda s: getattr(s, attr_name),
                reverse=True
            )
            rankings[dim_key] = [
                {
                    'coin': s.coin_name,
                    'symbol': s.symbol,
                    'score': getattr(s, attr_name)
                }
                for s in ranked
            ]

        return rankings

    def calculate_win_counts(self, scores: List[ProjectScore]) -> Dict[str, int]:
        """Calculate how many dimensions each project wins.

        Args:
            scores: List of ProjectScore objects

        Returns:
            Dictionary with win counts for each project
        """
        win_counts = {score.coin_id: 0 for score in scores}

        for dim_key, _, _ in self.DIMENSIONS:
            attr_name = f'{dim_key}_score'
            max_score = max(getattr(s, attr_name) for s in scores)

            # All projects with max score in this dimension get a win
            for score in scores:
                if getattr(score, attr_name) == max_score:
                    win_counts[score.coin_id] += 1

        return win_counts