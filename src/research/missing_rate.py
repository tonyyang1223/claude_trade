"""Factor Missing Rate Analysis.

Analyzes data availability and missing rate patterns.
Detects systematic data quality issues.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict
import numpy as np

from src.factors import registry
from src.factors.store import FactorStore


class FactorMissingRateAnalyzer:
    """Analyzes factor data missing rate patterns."""

    MISSING_RATE_LOW = 0.05
    MISSING_RATE_MEDIUM = 0.15
    MISSING_RATE_HIGH = 0.30

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        registry.discover_factors()

    def compute_missing_rate(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        """Compute missing rate for a factor."""
        history = self.store.get_factor_history(factor_name, days=days)
        expected = days
        actual = len(history)
        missing = expected - actual
        missing_rate = missing / expected if expected > 0 else 0

        if missing_rate < self.MISSING_RATE_LOW:
            status = "EXCELLENT"
        elif missing_rate < self.MISSING_RATE_MEDIUM:
            status = "GOOD"
        elif missing_rate < self.MISSING_RATE_HIGH:
            status = "MODERATE"
        else:
            status = "POOR"

        return {
            "factor_name": factor_name,
            "expected_days": expected,
            "actual_days": actual,
            "missing_days": missing,
            "missing_rate": round(missing_rate, 4),
            "availability_rate": round(1 - missing_rate, 4),
            "status": status
        }

    def compute_missing_pattern(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        """Analyze missing data pattern (random vs systematic)."""
        history = self.store.get_factor_history(factor_name, days=days)

        if len(history) < 5:
            return {"pattern": "INSUFFICIENT_DATA", "consecutive_gaps": 0, "max_gap": 0}

        dates = sorted([h.get("date", "") for h in history])

        if len(dates) < 2:
            return {"pattern": "INSUFFICIENT_DATA", "consecutive_gaps": 0, "max_gap": 0}

        gaps = []
        for i in range(1, len(dates)):
            try:
                d1 = datetime.strptime(dates[i-1], "%Y-%m-%d")
                d2 = datetime.strptime(dates[i], "%Y-%m-%d")
                gap = (d2 - d1).days - 1
                if gap > 0:
                    gaps.append(gap)
            except ValueError:
                continue

        if not gaps:
            return {"pattern": "CONTINUOUS", "consecutive_gaps": 0, "max_gap": 0}

        max_gap = max(gaps)
        avg_gap = np.mean(gaps)
        total_gaps = len(gaps)

        if max_gap <= 1 and total_gaps <= days * 0.1:
            pattern = "RANDOM"
        elif max_gap > 7:
            pattern = "SYSTEMATIC_LONG_GAP"
        elif total_gaps > days * 0.3:
            pattern = "SYSTEMATIC_FREQUENT"
        else:
            pattern = "MIXED"

        return {
            "pattern": pattern,
            "total_gaps": total_gaps,
            "max_gap": max_gap,
            "avg_gap": round(avg_gap, 2),
            "gap_sizes": gaps[:10]
        }

    def compute_weekday_missing_pattern(self, factor_name: str, days: int = 90) -> Dict[str, int]:
        """Analyze missing rate by weekday."""
        history = self.store.get_factor_history(factor_name, days=days)

        weekday_counts = defaultdict(int)
        weekday_expected = defaultdict(int)

        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)
            weekday = date.weekday()
            weekday_expected[weekday] += 1

        for h in history:
            try:
                date_str = h.get("date", "")
                date = datetime.strptime(date_str, "%Y-%m-%d")
                weekday_counts[date.weekday()] += 1
            except (ValueError, TypeError):
                continue

        weekday_missing = {}
        for wd in range(7):
            expected = weekday_expected.get(wd, 0)
            actual = weekday_counts.get(wd, 0)
            missing = expected - actual
            weekday_missing[wd] = {
                "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][wd],
                "expected": expected,
                "actual": actual,
                "missing_rate": round(missing / expected, 4) if expected > 0 else 0
            }

        return weekday_missing

    def analyze_factor_missing(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        """Complete missing rate analysis for a factor."""
        missing_rate = self.compute_missing_rate(factor_name, days=days)
        pattern = self.compute_missing_pattern(factor_name, days=days)
        weekday_pattern = self.compute_weekday_missing_pattern(factor_name, days=days * 3)

        weekday_issue = any(
            wd["missing_rate"] > self.MISSING_RATE_HIGH
            for wd in weekday_pattern.values()
        )

        return {
            **missing_rate,
            "missing_pattern": pattern["pattern"],
            "max_gap": pattern.get("max_gap", 0),
            "total_gaps": pattern.get("total_gaps", 0),
            "weekday_issue": weekday_issue,
            "data_quality_score": self._compute_quality_score(missing_rate, pattern)
        }

    def _compute_quality_score(self, missing_rate: Dict, pattern: Dict) -> float:
        """Compute data quality score (0-100)."""
        availability = missing_rate.get("availability_rate", 0)

        pattern_penalty = 0
        if pattern.get("pattern") == "SYSTEMATIC_LONG_GAP":
            pattern_penalty = 20
        elif pattern.get("pattern") == "SYSTEMATIC_FREQUENT":
            pattern_penalty = 15
        elif pattern.get("pattern") == "MIXED":
            pattern_penalty = 5

        gap_penalty = min(pattern.get("max_gap", 0) * 2, 20)

        score = availability * 100 - pattern_penalty - gap_penalty
        return max(0, round(score, 1))

    def analyze_all_factors(self, days: int = 30) -> List[Dict[str, Any]]:
        """Analyze missing rate for all factors."""
        results = []
        for name in registry._factors.keys():
            try:
                analysis = self.analyze_factor_missing(name, days=days)
                results.append(analysis)
            except Exception as e:
                results.append({
                    "factor_name": name,
                    "error": str(e),
                    "status": "ERROR"
                })

        return sorted(results, key=lambda x: x.get("missing_rate", 0))

    def get_problematic_factors(self, threshold: str = "MODERATE") -> List[str]:
        """Get factors with high missing rate."""
        analysis = self.analyze_all_factors()
        threshold_map = {"GOOD": 0.15, "MODERATE": 0.30, "POOR": 1.0}
        rate_threshold = threshold_map.get(threshold, 0.30)

        return [
            a["factor_name"] for a in analysis
            if a.get("missing_rate", 0) >= rate_threshold
        ]

    def generate_missing_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive missing rate report."""
        analysis = self.analyze_all_factors()

        excellent = [a for a in analysis if a.get("status") == "EXCELLENT"]
        good = [a for a in analysis if a.get("status") == "GOOD"]
        moderate = [a for a in analysis if a.get("status") == "MODERATE"]
        poor = [a for a in analysis if a.get("status") == "POOR"]

        systematic_issues = [
            a for a in analysis
            if "SYSTEMATIC" in a.get("missing_pattern", "")
        ]

        report = {
            "report_date": datetime.now().isoformat(),
            "summary": {
                "total_factors": len(analysis),
                "excellent": len(excellent),
                "good": len(good),
                "moderate": len(moderate),
                "poor": len(poor),
                "systematic_issues": len(systematic_issues)
            },
            "problematic_factors": [a["factor_name"] for a in poor],
            "systematic_issue_factors": [a["factor_name"] for a in systematic_issues],
            "analysis": analysis
        }

        if output_path:
            import json
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

        return report

    def print_missing_summary(self, days: int = 30):
        """Print missing rate summary table."""
        analysis = self.analyze_all_factors(days=days)

        print(f"\nFactor Missing Rate Analysis ({days} days)")
        print("=" * 70)

        for item in analysis[:20]:
            if "error" in item:
                print(f"{item['factor_name']:<30} ERROR: {item['error']}")
                continue

            rate = item.get("missing_rate", 0)
            status = item.get("status", "UNKNOWN")
            pattern = item.get("missing_pattern", "UNKNOWN")

            print(f"{item['factor_name']:<30} {rate*100:>5.1f}% missing [{status}] ({pattern})")
