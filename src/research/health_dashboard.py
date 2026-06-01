"""Factor Health Dashboard - integrates stability, discrimination, coverage."""
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path
import json

from src.factors import registry
from src.research.stability import FactorStabilityAnalyzer
from src.research.discrimination import FactorDiscriminationAnalyzer
from src.research.coverage import FactorCoverageAnalyzer

class FactorHealthDashboard:
    STATUS_ACTIVE = "ACTIVE"
    STATUS_WATCHLIST = "WATCHLIST"
    STATUS_DEPRECATED = "DEPRECATED"
    STATUS_DISABLED = "DISABLED"

    COVERAGE_WATCHLIST_THRESHOLD = 50
    DISCRIMINATION_WATCHLIST_THRESHOLD = 10
    CONSECUTIVE_DAYS_THRESHOLD = 30

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.stability = FactorStabilityAnalyzer(store_dir)
        self.discrimination = FactorDiscriminationAnalyzer(store_dir)
        self.coverage = FactorCoverageAnalyzer(store_dir)
        registry.discover_factors()

    def compute_health_score(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        stability = self.stability.analyze_factor_health(factor_name, days)
        disc = self.discrimination.analyze_factor_discrimination(factor_name, days)
        cov = self.coverage.compute_coverage(factor_name, days)

        # Compute scores (0-100)
        stability_score = stability.get("health_score", 0)
        
        # Discrimination score based on entropy (max ~3.3 for 10 bins)
        entropy = disc.get("entropy", 0)
        disc_score = min(100, entropy * 30)  # Scale entropy to 0-100
        
        coverage_score = cov.get("coverage_pct", 0)

        # Weighted average
        overall = stability_score * 0.3 + disc_score * 0.4 + coverage_score * 0.3

        return {
            "factor_name": factor_name,
            "stability": round(stability_score, 1),
            "discrimination": round(disc_score, 1),
            "coverage": round(coverage_score, 1),
            "overall_health": round(overall, 1),
            "status": self._determine_status(overall, disc, cov),
            "recommendation": self._generate_recommendation(overall, disc, cov)
        }

    def _determine_status(self, overall: float, disc: Dict, cov: Dict) -> str:
        if overall < 30: return self.STATUS_DISABLED
        if disc.get("status") == "DEAD_FACTOR": return self.STATUS_DEPRECATED
        if cov.get("coverage_pct", 0) < self.COVERAGE_WATCHLIST_THRESHOLD: return self.STATUS_WATCHLIST
        if disc.get("entropy", 0) < 0.5: return self.STATUS_WATCHLIST
        return self.STATUS_ACTIVE

    def _generate_recommendation(self, overall: float, disc: Dict, cov: Dict) -> str:
        status = disc.get("status", "")
        if status == "DEAD_FACTOR": return "DEPRECATE: No information content"
        if status == "LOW_INFORMATION": return "WATCHLIST: Low discrimination power"
        if cov.get("coverage_pct", 0) < 50: return "WATCHLIST: Low data coverage"
        if overall >= 70: return "KEEP: Healthy factor"
        return "MONITOR: Marginal performance"

    def analyze_all_factors(self, days: int = 30) -> List[Dict[str, Any]]:
        return sorted([self.compute_health_score(n, days) for n in registry._factors.keys()], key=lambda x: -x["overall_health"])

    def get_retirement_recommendations(self) -> Dict[str, List[Dict[str, Any]]]:
        analysis = self.analyze_all_factors()
        
        recommendations = {
            "DEPRECATE": [],
            "WATCHLIST": [],
            "ACTIVE": [],
            "DISABLE": []
        }
        
        for item in analysis:
            status = item["status"]
            rec = {"name": item["factor_name"], "discrimination": item["discrimination"], "coverage": item["coverage"], "recommendation": item["recommendation"]}
            if status in recommendations:
                recommendations[status].append(rec)
        
        return recommendations

    def generate_report(self, output_path: Path = None) -> Dict[str, Any]:
        analysis = self.analyze_all_factors()
        retirement = self.get_retirement_recommendations()
        
        report = {
            "report_date": datetime.now().isoformat(),
            "summary": {
                "total_factors": len(analysis),
                "active": len(retirement["ACTIVE"]),
                "watchlist": len(retirement["WATCHLIST"]),
                "deprecated": len(retirement["DEPRECATE"]),
                "disabled": len(retirement["DISABLE"])
            },
            "factors": analysis,
            "retirement_recommendations": retirement
        }
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)
        
        return report

    def print_retirement_table(self):
        retirement = self.get_retirement_recommendations()
        
        print("\n" + "=" * 70)
        print("Factor Retirement Recommendations")
        print("=" * 70)
        
        for status, factors in retirement.items():
            if factors:
                print(f"\n{status}:")
                print("-" * 40)
                for f in factors:
                    print(f"  {f['name']:<30} disc={f['discrimination']:<5.1f} cov={f['coverage']:<5.1f}%")
                    print(f"    -> {f['recommendation']}")
