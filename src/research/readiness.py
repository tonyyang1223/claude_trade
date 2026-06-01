"""Alpha Readiness Assessment.

Evaluates whether the factor system is ready for alpha signal generation.
Checks data quality, coverage, stability, and statistical properties.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from enum import Enum
import json

from src.factors import registry
from src.research.stability import FactorStabilityAnalyzer
from src.research.discrimination import FactorDiscriminationAnalyzer
from src.research.coverage import FactorCoverageAnalyzer
from src.research.correlation import FactorCorrelationAnalyzer
from src.research.effective_count import EffectiveFactorCountAnalyzer
from src.research.accumulation import DataAccumulationPlanner


class ReadinessLevel(str, Enum):
    """Alpha readiness levels."""
    READY = "READY"
    APPROACHING = "APPROACHING"
    NOT_READY = "NOT_READY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AlphaReadinessAssessor:
    """Assesses alpha signal generation readiness."""

    MIN_FACTORS = 5
    MIN_COVERAGE = 0.80
    MIN_DISCRIMINATION_ENTROPY = 1.0
    MAX_CORRELATION = 0.70
    MIN_EFFECTIVE_COUNT_RATIO = 0.60
    MIN_HISTORY_DAYS = 90

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.stability = FactorStabilityAnalyzer(store_dir)
        self.discrimination = FactorDiscriminationAnalyzer(store_dir)
        self.coverage = FactorCoverageAnalyzer(store_dir)
        self.correlation = FactorCorrelationAnalyzer(store_dir)
        self.effective_count = EffectiveFactorCountAnalyzer()
        self.accumulation = DataAccumulationPlanner(store_dir)
        registry.discover_factors()

    def check_factor_count(self) -> Dict[str, Any]:
        """Check if enough factors are available."""
        total = len(registry._factors)
        sufficient = total >= self.MIN_FACTORS

        return {
            "check": "factor_count",
            "total_factors": total,
            "minimum_required": self.MIN_FACTORS,
            "passed": sufficient,
            "status": "PASS" if sufficient else "FAIL"
        }

    def check_data_coverage(self) -> Dict[str, Any]:
        """Check data coverage across factors."""
        coverage_analysis = self.coverage.analyze_all_factors(days=90)

        high_coverage = len([c for c in coverage_analysis if c.get("coverage_pct", 0) >= self.MIN_COVERAGE * 100])
        total = len(coverage_analysis)
        ratio = high_coverage / total if total > 0 else 0

        passed = ratio >= 0.80

        return {
            "check": "data_coverage",
            "factors_with_good_coverage": high_coverage,
            "total_factors": total,
            "coverage_ratio": round(ratio, 2),
            "threshold": self.MIN_COVERAGE,
            "passed": passed,
            "status": "PASS" if passed else "FAIL"
        }

    def check_discrimination(self) -> Dict[str, Any]:
        """Check factor discrimination power."""
        disc_analysis = self.discrimination.analyze_all_factors(days=90)

        good_discrimination = len([
            d for d in disc_analysis
            if d.get("entropy", 0) >= self.MIN_DISCRIMINATION_ENTROPY
            and d.get("status") == "GOOD"
        ])
        total = len(disc_analysis)
        ratio = good_discrimination / total if total > 0 else 0

        passed = ratio >= 0.60

        return {
            "check": "discrimination",
            "factors_with_good_discrimination": good_discrimination,
            "total_factors": total,
            "ratio": round(ratio, 2),
            "threshold": self.MIN_DISCRIMINATION_ENTROPY,
            "passed": passed,
            "status": "PASS" if passed else "FAIL"
        }

    def check_correlation(self) -> Dict[str, Any]:
        """Check factor correlation (diversity)."""
        try:
            corr_matrix = self.correlation.compute_correlation_matrix(days=90)

            if corr_matrix.empty:
                return {
                    "check": "correlation",
                    "passed": False,
                    "status": "FAIL",
                    "reason": "No correlation data available"
                }

            high_corr_pairs = 0
            total_pairs = 0

            for i, col in enumerate(corr_matrix.columns):
                for j, idx in enumerate(corr_matrix.index):
                    if i < j:
                        corr_val = abs(corr_matrix.loc[idx, col])
                        total_pairs += 1
                        if corr_val > self.MAX_CORRELATION:
                            high_corr_pairs += 1

            ratio = 1 - (high_corr_pairs / total_pairs) if total_pairs > 0 else 0
            passed = ratio >= 0.70

            return {
                "check": "correlation",
                "high_correlation_pairs": high_corr_pairs,
                "total_pairs": total_pairs,
                "diversity_ratio": round(ratio, 2),
                "threshold": self.MAX_CORRELATION,
                "passed": passed,
                "status": "PASS" if passed else "FAIL"
            }
        except Exception as e:
            return {
                "check": "correlation",
                "passed": False,
                "status": "ERROR",
                "error": str(e)
            }

    def check_effective_count(self) -> Dict[str, Any]:
        """Check effective factor count (redundancy)."""
        result = self.effective_count.compute_effective_count()

        total = result.get("total_factors", 0)
        effective = result.get("effective_count", 0)
        ratio = effective / total if total > 0 else 0

        passed = ratio >= self.MIN_EFFECTIVE_COUNT_RATIO

        return {
            "check": "effective_count",
            "total_factors": total,
            "effective_count": round(effective, 1),
            "efficiency_ratio": round(ratio, 2),
            "threshold": self.MIN_EFFECTIVE_COUNT_RATIO,
            "passed": passed,
            "status": "PASS" if passed else "FAIL"
        }

    def check_history_depth(self) -> Dict[str, Any]:
        """Check historical data depth."""
        accumulation = self.accumulation.estimate_total_effort()

        avg_coverage = accumulation.get("average_coverage_pct", 0)
        passed = avg_coverage >= (self.MIN_HISTORY_DAYS / 504 * 100)

        return {
            "check": "history_depth",
            "average_coverage_pct": avg_coverage,
            "minimum_days": self.MIN_HISTORY_DAYS,
            "ideal_days": 504,
            "passed": passed,
            "status": "PASS" if passed else "FAIL"
        }

    def assess_readiness(self) -> Dict[str, Any]:
        """Perform comprehensive readiness assessment."""
        checks = [
            self.check_factor_count(),
            self.check_data_coverage(),
            self.check_discrimination(),
            self.check_correlation(),
            self.check_effective_count(),
            self.check_history_depth()
        ]

        passed_count = sum(1 for c in checks if c.get("passed", False))
        total_checks = len(checks)

        pass_rate = passed_count / total_checks if total_checks > 0 else 0

        if pass_rate >= 0.90:
            level = ReadinessLevel.READY
        elif pass_rate >= 0.70:
            level = ReadinessLevel.APPROACHING
        elif pass_rate >= 0.50:
            level = ReadinessLevel.NOT_READY
        else:
            level = ReadinessLevel.INSUFFICIENT_DATA

        blockers = [c for c in checks if not c.get("passed", False)]

        return {
            "assessment_date": datetime.now().isoformat(),
            "readiness_level": level.value,
            "passed_checks": passed_count,
            "total_checks": total_checks,
            "pass_rate": round(pass_rate, 2),
            "checks": checks,
            "blockers": [{"check": b["check"], "status": b.get("status", "FAIL")} for b in blockers],
            "recommendations": self._generate_recommendations(blockers, level)
        }

    def _generate_recommendations(self, blockers: List[Dict], level: ReadinessLevel) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        for b in blockers:
            check = b.get("check", "")
            if check == "factor_count":
                recommendations.append("Add more factors to increase signal diversity")
            elif check == "data_coverage":
                recommendations.append("Improve data collection to increase coverage")
            elif check == "discrimination":
                recommendations.append("Review factors with low discrimination for retirement")
            elif check == "correlation":
                recommendations.append("Remove highly correlated factors to reduce redundancy")
            elif check == "effective_count":
                recommendations.append("Reduce factor redundancy through consolidation")
            elif check == "history_depth":
                recommendations.append("Continue historical data accumulation")

        if level == ReadinessLevel.READY:
            recommendations.insert(0, "System is ready for alpha signal generation")
        elif level == ReadinessLevel.APPROACHING:
            recommendations.insert(0, "Address remaining blockers to reach full readiness")

        return recommendations

    def generate_readiness_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive readiness report."""
        assessment = self.assess_readiness()

        report = {
            "report_date": datetime.now().isoformat(),
            "alpha_readiness": assessment
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

        return report

    def print_readiness_summary(self):
        """Print readiness summary."""
        assessment = self.assess_readiness()

        print("\nAlpha Readiness Assessment")
        print("=" * 70)
        print(f"Readiness Level: {assessment['readiness_level']}")
        print(f"Passed Checks: {assessment['passed_checks']}/{assessment['total_checks']}")
        print(f"Pass Rate: {assessment['pass_rate'] * 100:.0f}%")
        print("-" * 70)

        print("\nCheck Results:")
        for check in assessment["checks"]:
            status = "PASS" if check.get("passed", False) else "FAIL"
            print(f"  [{'✓' if check.get('passed', False) else '✗'}] {check['check']:<20} {status}")

        if assessment["blockers"]:
            print("\nBlockers:")
            for b in assessment["blockers"]:
                print(f"  - {b['check']}: {b['status']}")

        if assessment["recommendations"]:
            print("\nRecommendations:")
            for r in assessment["recommendations"]:
                print(f"  - {r}")