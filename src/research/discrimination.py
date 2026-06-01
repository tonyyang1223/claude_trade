"""Factor Discrimination Analysis."""
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import numpy as np
from src.factors import registry
from src.factors.store import FactorStore

class FactorDiscriminationAnalyzer:
    UNIQUE_COUNT_MIN = 3
    VARIANCE_MIN = 1e-10
    ENTROPY_MIN = 0.5

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        registry.discover_factors()

    def compute_unique_count(self, values: List[float]) -> int:
        if not values: return 0
        return len(set(round(v, 6) for v in values if v is not None))

    def compute_entropy(self, values: List[float], bins: int = 10) -> float:
        values = [v for v in values if v is not None and not np.isnan(v)]
        if not values: return 0.0
        hist, _ = np.histogram(values, bins=bins)
        probs = hist / len(values)
        probs = probs[probs > 0]
        return round(float(-np.sum(probs * np.log2(probs + 1e-10))), 4)

    def compute_variance(self, values: List[float]) -> float:
        values = [v for v in values if v is not None and not np.isnan(v)]
        return float(np.var(values)) if len(values) >= 2 else 0.0

    def analyze_factor_discrimination(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        history = self.store.get_factor_history(factor_name, days=days)
        if not history:
            return {"factor_name": factor_name, "unique_count": 0, "entropy": 0.0, "variance": 0.0, "status": "NO_DATA"}

        values = [h.get("normalized_value") or h.get("raw_value", 0) for h in history]
        scores = [h.get("score", 3) for h in history]
        
        unique_count = self.compute_unique_count(values)
        entropy = self.compute_entropy(values)
        variance = self.compute_variance(values)
        
        if variance < self.VARIANCE_MIN: status = "DEAD_FACTOR"
        elif unique_count < self.UNIQUE_COUNT_MIN or entropy < self.ENTROPY_MIN: status = "LOW_INFORMATION"
        else: status = "GOOD"

        return {"factor_name": factor_name, "unique_count": unique_count, "entropy": entropy, "variance": round(variance, 10), "status": status, "days_analyzed": len(history)}

    def analyze_all_factors(self, days: int = 30) -> List[Dict[str, Any]]:
        return sorted([self.analyze_factor_discrimination(n, days) for n in registry._factors.keys()], key=lambda x: -x.get("entropy", 0))

    def get_problematic_factors(self) -> Dict[str, List[str]]:
        analysis = self.analyze_all_factors(days=30)
        return {status: [a["factor_name"] for a in analysis if a["status"] == status] for status in ["LOW_INFORMATION", "DEAD_FACTOR", "NO_DATA"]}

    def print_summary_table(self, days: int = 30):
        analysis = self.analyze_all_factors(days=days)
        print(f"Factor Discrimination Analysis ({days} days)")
        print("-" * 60)
        for item in analysis:
            print(f"{item['factor_name']:<30} unique={item['unique_count']:<3} entropy={item['entropy']:.2f} status={item['status']}")
