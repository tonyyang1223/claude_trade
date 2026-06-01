"""Factor Coverage Analysis."""
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
from src.factors import registry
from src.factors.store import FactorStore

class FactorCoverageAnalyzer:
    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        registry.discover_factors()

    def compute_coverage(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        history = self.store.get_factor_history(factor_name, days=days)
        expected = days
        actual = len(history)
        
        available = actual / expected if expected > 0 else 0
        missing = 1 - available
        
        return {
            "factor_name": factor_name,
            "expected_days": expected,
            "actual_days": actual,
            "coverage_pct": round(available * 100, 1),
            "missing_pct": round(missing * 100, 1),
            "status": "HIGH" if available >= 0.9 else "MEDIUM" if available >= 0.5 else "LOW"
        }

    def analyze_all_factors(self, days: int = 30) -> List[Dict[str, Any]]:
        return sorted([self.compute_coverage(n, days) for n in registry._factors.keys()], key=lambda x: -x["coverage_pct"])

    def get_low_coverage_factors(self, threshold: float = 0.5) -> List[str]:
        return [a["factor_name"] for a in self.analyze_all_factors() if a["coverage_pct"] < threshold * 100]
