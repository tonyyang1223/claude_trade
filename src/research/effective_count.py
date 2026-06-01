"""Effective Factor Count Analysis.

Calculates N_eff = (sum(weights)^2) / sum(weights^2)

Measures true independent information content.
If N_eff << N, factors are highly correlated (redundant).
"""
from typing import Dict, List, Any
from pathlib import Path
import numpy as np
from src.factors import registry
from src.research.weighting import HierarchicalWeighting

class EffectiveFactorCountAnalyzer:
    def __init__(self):
        self.weighting = HierarchicalWeighting()

    def compute_effective_count(self, weights: Dict[str, float] = None) -> Dict[str, Any]:
        if weights is None:
            weights = self.weighting.get_all_weights()
        
        w = np.array([v for v in weights.values() if v > 0])
        if len(w) == 0:
            return {"total_factors": 0, "effective_count": 0.0, "redundancy_ratio": 0.0}
        
        sum_w = np.sum(w)
        sum_w_sq = np.sum(w ** 2)
        
        n_eff = (sum_w ** 2) / sum_w_sq if sum_w_sq > 0 else 0
        n_total = len(w)
        redundancy = 1 - (n_eff / n_total) if n_total > 0 else 0
        
        return {
            "total_factors": n_total,
            "effective_count": round(n_eff, 2),
            "redundancy_ratio": round(redundancy, 4),
            "interpretation": self._interpret(n_total, n_eff)
        }

    def _interpret(self, total: int, effective: float) -> str:
        ratio = effective / total if total > 0 else 0
        if ratio >= 0.8: return "GOOD: High independent information"
        if ratio >= 0.6: return "MODERATE: Some redundancy present"
        if ratio >= 0.4: return "HIGH_REDUNDANCY: Significant overlap"
        return "CRITICAL: Most factors are redundant"

    def analyze_by_category(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        summary = self.weighting.get_category_summary()
        
        for category, data in summary.items():
            factors = data.get("factors", {})
            if factors:
                cat_weights = {f: w for f, w in factors.items()}
                results[category] = self.compute_effective_count(cat_weights)
        
        return results

    def generate_report(self) -> Dict[str, Any]:
        overall = self.compute_effective_count()
        by_category = self.analyze_by_category()
        
        return {
            "overall": overall,
            "by_category": by_category,
            "recommendation": self._recommendation(overall)
        }

    def _recommendation(self, result: Dict[str, Any]) -> str:
        eff = result["effective_count"]
        total = result["total_factors"]
        
        if eff < total * 0.5:
            return f"Consider reducing from {total} to ~{int(eff)} factors"
        return "Current factor set is well-diversified"
