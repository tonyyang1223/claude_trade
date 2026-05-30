"""Factor Stability Analysis - analyzes volatility, stability, missing rate, drift."""
from typing import Dict, List, Any
from pathlib import Path
import numpy as np

from src.factors import registry
from src.factors.store import FactorStore

class FactorStabilityAnalyzer:
    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        registry.discover_factors()

    def compute_volatility(self, factor_name: str, days: int = 90) -> float:
        history = self.store.get_factor_history(factor_name, days=days)
        if not history: return 0.0
        values = [h.get("raw_value", 0) for h in history if h.get("raw_value")]
        if not values: return 0.0
        mean = np.mean(values)
        std = np.std(values)
        return round(std / abs(mean), 4) if mean != 0 else 0.0

    def compute_stability_score(self, factor_name: str, days: int = 90) -> float:
        history = self.store.get_factor_history(factor_name, days=days)
        if len(history) < 5: return 50.0
        values = [h.get("normalized_value", 0.5) for h in history if h.get("normalized_value")]
        if len(values) < 5: return 50.0
        vol = np.std(values)
        return max(0, 100 - vol * 200)

    def analyze_factor_health(self, factor_name: str, days: int = 90) -> Dict[str, Any]:
        vol = self.compute_volatility(factor_name, days)
        stab = self.compute_stability_score(factor_name, days)
        missing = len(self.store.get_factor_history(factor_name, days)) / max(days, 1)
        health = stab * 0.5 + (1 - vol) * 30 + missing * 20
        status = "healthy" if health >= 70 else "moderate" if health >= 50 else "degraded"
        return {"factor_name": factor_name, "health_score": round(health, 2), "health_status": status}

    def analyze_all_factors(self, days: int = 90) -> List[Dict]:
        return [self.analyze_factor_health(n, days) for n in registry._factors.keys()]
