"""Factor Retirement Advisor.

Provides recommendations for factor retirement based on comprehensive analysis.
Integrates health, discrimination, coverage, drift, and missing rate analysis.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from src.factors import registry
from src.research.stability import FactorStabilityAnalyzer
from src.research.discrimination import FactorDiscriminationAnalyzer
from src.research.coverage import FactorCoverageAnalyzer
from src.research.drift import FactorDriftAnalyzer
from src.research.missing_rate import FactorMissingRateAnalyzer


class FactorRetirementAdvisor:
    """Advisor for factor retirement decisions."""

    RETIREMENT_THRESHOLD = 40.0
    WATCHLIST_THRESHOLD = 60.0

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.stability = FactorStabilityAnalyzer(store_dir)
        self.discrimination = FactorDiscriminationAnalyzer(store_dir)
        self.coverage = FactorCoverageAnalyzer(store_dir)
        self.drift = FactorDriftAnalyzer(store_dir)
        self.missing_rate = FactorMissingRateAnalyzer(store_dir)
        registry.discover_factors()

    def compute_retirement_score(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        """Compute comprehensive retirement score."""
        stability = self.stability.analyze_factor_health(factor_name, days=days)
        disc = self.discrimination.analyze_factor_discrimination(factor_name, days=days)
        cov = self.coverage.compute_coverage(factor_name, days=days)
        drift = self.drift.analyze_factor_drift(factor_name, days=days)
        missing = self.missing_rate.analyze_factor_missing(factor_name, days=days)

        stability_score = stability.get("health_score", 50)
        entropy = disc.get("entropy", 0)
        disc_score = min(100, entropy * 30)
        coverage_score = cov.get("coverage_pct", 0)
        drift_zscore = abs(drift.get("drift_zscore", 0))
        drift_score = max(0, 100 - drift_zscore * 20)
        quality_score = missing.get("data_quality_score", 50)

        combined_score = round(
            stability_score * 0.25 +
            disc_score * 0.25 +
            coverage_score * 0.20 +
            drift_score * 0.15 +
            quality_score * 0.15,
            1
        )

        critical_issues = []
        warnings = []

        if disc.get("status") == "DEAD_FACTOR":
            critical_issues.append("DEAD_FACTOR: No information content")
        elif disc.get("status") == "LOW_INFORMATION":
            warnings.append("LOW_INFORMATION: Weak discrimination power")

        if coverage_score < 50:
            critical_issues.append(f"LOW_COVERAGE: Only {coverage_score:.1f}% data available")
        elif coverage_score < 80:
            warnings.append(f"MODERATE_COVERAGE: {coverage_score:.1f}% data available")

        if drift_zscore > 2.0:
            critical_issues.append(f"SEVERE_DRIFT: z-score={drift_zscore:.2f}")
        elif drift_zscore > 1.0:
            warnings.append(f"MODERATE_DRIFT: z-score={drift_zscore:.2f}")

        if quality_score < 30:
            critical_issues.append(f"POOR_QUALITY: score={quality_score:.1f}")
        elif quality_score < 50:
            warnings.append(f"MODERATE_QUALITY: score={quality_score:.1f}")

        recommendation = self._get_recommendation(combined_score, critical_issues, warnings)

        return {
            "factor_name": factor_name,
            "combined_score": combined_score,
            "stability_score": round(stability_score, 1),
            "discrimination_score": round(disc_score, 1),
            "coverage_score": round(coverage_score, 1),
            "drift_score": round(drift_score, 1),
            "quality_score": round(quality_score, 1),
            "critical_issues": critical_issues,
            "warnings": warnings,
            "recommendation": recommendation["action"],
            "priority": recommendation["priority"],
            "should_retire": recommendation["should_retire"]
        }

    def _get_recommendation(self, score: float, critical: List[str], warnings: List[str]) -> Dict[str, Any]:
        """Generate retirement recommendation."""
        if critical or score < self.RETIREMENT_THRESHOLD:
            return {
                "action": "IMMEDIATE_RETIREMENT",
                "priority": "HIGH",
                "should_retire": True
            }
        elif score < self.WATCHLIST_THRESHOLD or len(warnings) >= 2:
            return {
                "action": "REVIEW_FOR_RETIREMENT",
                "priority": "MEDIUM",
                "should_retire": False
            }
        elif warnings:
            return {
                "action": "MONITOR_CLOSELY",
                "priority": "LOW",
                "should_retire": False
            }
        else:
            return {
                "action": "KEEP_ACTIVE",
                "priority": "NONE",
                "should_retire": False
            }

    def analyze_all_factors(self, days: int = 30) -> List[Dict[str, Any]]:
        """Analyze retirement status for all factors."""
        results = []
        for name in registry._factors.keys():
            try:
                score = self.compute_retirement_score(name, days=days)
                results.append(score)
            except Exception as e:
                results.append({
                    "factor_name": name,
                    "error": str(e),
                    "recommendation": "ERROR",
                    "should_retire": False
                })

        return sorted(results, key=lambda x: x.get("combined_score", 0))

    def get_retirement_candidates(self) -> List[Dict[str, Any]]:
        """Get factors recommended for retirement."""
        analysis = self.analyze_all_factors()
        return [a for a in analysis if a.get("should_retire", False)]

    def get_watchlist_factors(self) -> List[Dict[str, Any]]:
        """Get factors on watchlist."""
        analysis = self.analyze_all_factors()
        return [
            a for a in analysis
            if not a.get("should_retire", False)
            and a.get("priority") in ["LOW", "MEDIUM"]
        ]

    def get_healthy_factors(self) -> List[Dict[str, Any]]:
        """Get factors that are healthy."""
        analysis = self.analyze_all_factors()
        return [a for a in analysis if a.get("priority") == "NONE"]

    def generate_retirement_plan(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive retirement plan."""
        analysis = self.analyze_all_factors()

        immediate = [a for a in analysis if a.get("recommendation") == "IMMEDIATE_RETIREMENT"]
        review = [a for a in analysis if a.get("recommendation") == "REVIEW_FOR_RETIREMENT"]
        monitor = [a for a in analysis if a.get("recommendation") == "MONITOR_CLOSELY"]
        active = [a for a in analysis if a.get("recommendation") == "KEEP_ACTIVE"]

        total_critical = sum(len(a.get("critical_issues", [])) for a in analysis)
        total_warnings = sum(len(a.get("warnings", [])) for a in analysis)

        plan = {
            "report_date": datetime.now().isoformat(),
            "summary": {
                "total_factors": len(analysis),
                "immediate_retirement": len(immediate),
                "review_for_retirement": len(review),
                "monitor_closely": len(monitor),
                "keep_active": len(active),
                "total_critical_issues": total_critical,
                "total_warnings": total_warnings
            },
            "immediate_retirement": [
                {"name": a["factor_name"], "score": a["combined_score"], "issues": a["critical_issues"]}
                for a in immediate
            ],
            "review_for_retirement": [
                {"name": a["factor_name"], "score": a["combined_score"], "warnings": a["warnings"]}
                for a in review
            ],
            "monitor_closely": [
                {"name": a["factor_name"], "score": a["combined_score"], "warnings": a["warnings"]}
                for a in monitor
            ],
            "analysis": analysis
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(plan, f, indent=2, default=str)

        return plan

    def batch_retire(self, factor_names: List[str]) -> Dict[str, Any]:
        """Batch retire factors."""
        results = {"retired": [], "failed": []}

        for name in factor_names:
            try:
                score = self.compute_retirement_score(name)
                if score.get("should_retire", False):
                    results["retired"].append({
                        "name": name,
                        "final_score": score["combined_score"],
                        "reasons": score["critical_issues"]
                    })
                else:
                    results["failed"].append({
                        "name": name,
                        "reason": "Does not meet retirement criteria"
                    })
            except Exception as e:
                results["failed"].append({"name": name, "reason": str(e)})

        return results

    def print_retirement_summary(self, days: int = 30):
        """Print retirement summary table."""
        analysis = self.analyze_all_factors(days=days)

        print("\nFactor Retirement Advisor Summary")
        print("=" * 70)

        for item in analysis[:20]:
            if "error" in item:
                print(f"{item['factor_name']:<30} ERROR: {item['error']}")
                continue

            score = item.get("combined_score", 0)
            rec = item.get("recommendation", "UNKNOWN")
            issues = len(item.get("critical_issues", []))
            warns = len(item.get("warnings", []))

            print(f"{item['factor_name']:<30} score={score:<5.1f} issues={issues:<2} warns={warns:<2} [{rec}]")