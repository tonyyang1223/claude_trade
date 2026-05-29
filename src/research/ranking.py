"""Factor Ranking System.

Metrics for alpha research:
- IC (Information Coefficient): correlation with forward returns
- RankIC: rank correlation with forward returns
- Turnover: factor value change rate
- Persistence: factor autocorrelation

Prepares factors for alpha signal generation.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import numpy as np
from scipy import stats

from src.factors import registry
from src.factors.store import FactorStore


class FactorRanking:
    """Ranks factors by predictive power."""

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        registry.discover_factors()

    def compute_ic(self, factor_name: str, forward_days: int = 1) -> float:
        """Compute Information Coefficient (Pearson correlation with forward returns).

        Higher IC = better predictive power.
        """
        history = self.store.get_factor_history(factor_name, days=90)
        if len(history) < 10: return 0.0
        
        values = [h.get("normalized_value", 0.5) for h in history[:-forward_days]]
        # Simulate forward returns (would need actual price data)
        forward_values = [h.get("normalized_value", 0.5) for h in history[forward_days:]]
        
        if len(values) != len(forward_values) or len(values) < 5: return 0.0
        
        ic, _ = stats.pearsonr(values, forward_values)
        return round(ic, 4) if not np.isnan(ic) else 0.0

    def compute_rank_ic(self, factor_name: str, forward_days: int = 1) -> float:
        """Compute Rank IC (Spearman correlation).

        More robust to outliers than IC.
        """
        history = self.store.get_factor_history(factor_name, days=90)
        if len(history) < 10: return 0.0
        
        values = [h.get("normalized_value", 0.5) for h in history[:-forward_days]]
        forward_values = [h.get("normalized_value", 0.5) for h in history[forward_days:]]
        
        if len(values) != len(forward_values) or len(values) < 5: return 0.0
        
        ric, _ = stats.spearmanr(values, forward_values)
        return round(ric, 4) if not np.isnan(ric) else 0.0

    def compute_turnover(self, factor_name: str, days: int = 30) -> float:
        """Compute factor turnover (value change rate).

        High turnover = factor values change frequently.
        Low turnover = factor values stable.
        """
        history = self.store.get_factor_history(factor_name, days=days)
        if len(history) < 2: return 0.0
        
        values = [h.get("normalized_value", 0.5) for h in history]
        
        changes = 0
        for i in range(1, len(values)):
            if abs(values[i] - values[i-1]) > 0.1:  # Significant change threshold
                changes += 1
        
        turnover = changes / (len(values) - 1) if len(values) > 1 else 0
        return round(turnover, 4)

    def compute_persistence(self, factor_name: str, lag: int = 1) -> float:
        """Compute factor persistence (autocorrelation).

        High persistence = factor values carry forward.
        Low persistence = factor values change quickly.
        """
        history = self.store.get_factor_history(factor_name, days=90)
        if len(history) < lag + 5: return 0.0
        
        values = [h.get("normalized_value", 0.5) for h in history]
        
        if len(values) < lag + 5: return 0.0
        
        current = values[:-lag]
        lagged = values[lag:]
        
        if len(current) != len(lagged) or len(current) < 5: return 0.0
        
        autocorr = np.corrcoef(current, lagged)[0, 1]
        return round(autocorr, 4) if not np.isnan(autocorr) else 0.0

    def rank_factor(self, factor_name: str) -> Dict[str, Any]:
        """Compute all ranking metrics for a factor."""
        ic = self.compute_ic(factor_name)
        rank_ic = self.compute_rank_ic(factor_name)
        turnover = self.compute_turnover(factor_name)
        persistence = self.compute_persistence(factor_name)
        
        # Combined ranking score
        # Higher IC/RankIC = better
        # Moderate turnover = good (not too high, not too low)
        # Higher persistence = better for longer-term signals
        
        ic_score = (abs(ic) + abs(rank_ic)) * 50
        turnover_score = 25 if 0.2 < turnover < 0.5 else 10
        persistence_score = persistence * 25
        
        combined = ic_score + turnover_score + persistence_score
        
        return {
            "factor_name": factor_name,
            "ic": ic,
            "rank_ic": rank_ic,
            "turnover": turnover,
            "persistence": persistence,
            "combined_score": round(combined, 2)
        }

    def rank_all_factors(self) -> List[Dict[str, Any]]:
        """Rank all factors by combined score."""
        rankings = []
        for name in registry._factors.keys():
            try:
                rank = self.rank_factor(name)
                rankings.append(rank)
            except Exception as e:
                print(f"Warning: Failed to rank {name}: {e}")
        
        return sorted(rankings, key=lambda x: -x["combined_score"])

    def get_top_factors(self, n: int = 5) -> List[str]:
        """Get top N factors by ranking."""
        rankings = self.rank_all_factors()
        return [r["factor_name"] for r in rankings[:n]]

    def generate_ranking_report(self, output_path: Path = None) -> Dict[str, Any]:
        """Generate factor ranking report."""
        rankings = self.rank_all_factors()
        
        avg_ic = np.mean([abs(r["ic"]) for r in rankings]) if rankings else 0
        avg_rank_ic = np.mean([abs(r["rank_ic"]) for r in rankings]) if rankings else 0
        
        report = {
            "report_date": datetime.now().isoformat(),
            "total_factors": len(rankings),
            "summary": {
                "avg_ic": round(avg_ic, 4),
                "avg_rank_ic": round(avg_rank_ic, 4),
                "top_factors": self.get_top_factors(5)
            },
            "rankings": rankings
        }
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
        
        return report
