"""Factor Redundancy Detection.

Detects highly correlated factors that may provide redundant information.
Threshold: abs(corr) > 0.85 = high redundancy
Threshold: abs(corr) > 0.95 = near-duplicate
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json

from src.factors import registry
from src.research.correlation import FactorCorrelationAnalyzer
from src.research.classification import FactorClassifier


class RedundancyDetector:
    """Detects redundant factors based on correlation analysis."""

    HIGH_REDUNDANCY_THRESHOLD = 0.85
    NEAR_DUPLICATE_THRESHOLD = 0.95

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.correlation_analyzer = FactorCorrelationAnalyzer(store_dir)
        self.classifier = FactorClassifier()

    def detect_redundancy(self, threshold: float = 0.85, days: int = 30) -> Dict[str, Any]:
        """Detect redundant factors."""
        high_corr = self.correlation_analyzer.find_high_correlations(threshold=threshold, days=days)

        redundant_pairs = []
        for pair in high_corr:
            f1, f2 = pair["factor1"], pair["factor2"]
            corr = pair["correlation"]

            c1 = self.classifier.get_classification(f1)
            c2 = self.classifier.get_classification(f2)

            redundancy_type = self._classify_redundancy_type(corr, c1, c2)
            m1 = registry.get_factor(f1)
            m2 = registry.get_factor(f2)
            keep, reason = self._determine_keep_factor(f1, f2, m1, m2, c1, c2)

            redundant_pairs.append({
                "factor1": f1,
                "factor2": f2,
                "correlation": corr,
                "redundancy_type": redundancy_type,
                "recommendation": {"keep": keep, "remove": f2 if keep == f1 else f1, "reason": reason}
            })

        summary = {
            "total_pairs": len(redundant_pairs),
            "high_redundancy": len([p for p in redundant_pairs if p["redundancy_type"] == "high_redundancy"]),
            "near_duplicate": len([p for p in redundant_pairs if p["redundancy_type"] == "near_duplicate"]),
            "factors_flagged": len(set([p["recommendation"]["remove"] for p in redundant_pairs]))
        }

        return {
            "report_date": datetime.now().isoformat(),
            "threshold": threshold,
            "summary": summary,
            "redundant_pairs": redundant_pairs
        }

    def _classify_redundancy_type(self, correlation: float, c1: Any, c2: Any) -> str:
        abs_corr = abs(correlation)
        if abs_corr >= self.NEAR_DUPLICATE_THRESHOLD:
            return "near_duplicate"
        if c1 and c2 and c1.subcategory == c2.subcategory:
            return "intra_subcategory"
        if abs_corr >= self.HIGH_REDUNDANCY_THRESHOLD:
            return "high_redundancy"
        return "moderate_redundancy"

    def _determine_keep_factor(self, f1: str, f2: str, m1: Any, m2: Any, c1: Any, c2: Any) -> Tuple[str, str]:
        conf1 = m1.confidence if m1 else 0.5
        conf2 = m2.confidence if m2 else 0.5

        if conf1 > conf2:
            return f1, f"Higher confidence ({conf1:.2f})"
        elif conf2 > conf1:
            return f2, f"Higher confidence ({conf2:.2f})"

        freq_order = {"realtime": 4, "hourly": 3, "daily": 2, "weekly": 1}
        freq1 = freq_order.get(c1.data_frequency if c1 else "daily", 2)
        freq2 = freq_order.get(c2.data_frequency if c2 else "daily", 2)

        if freq1 > freq2:
            return f1, f"More frequent updates"
        elif freq2 > freq1:
            return f2, f"More frequent updates"

        return f1, "Alphabetical order"

    def generate_removal_recommendations(self, threshold: float = 0.85) -> List[Dict[str, Any]]:
        """Generate factor removal recommendations."""
        report = self.detect_redundancy(threshold=threshold)

        to_remove = {}
        for pair in report["redundant_pairs"]:
            remove_factor = pair["recommendation"]["remove"]
            if remove_factor not in to_remove:
                to_remove[remove_factor] = {"factor": remove_factor, "redundant_with": []}
            to_remove[remove_factor]["redundant_with"].append(pair["recommendation"]["keep"])

        return sorted(list(to_remove.values()), key=lambda x: -len(x["redundant_with"]))

    def export_report(self, output_path: Path = None, threshold: float = 0.85) -> Dict[str, Any]:
        """Export full redundancy report."""
        report = self.detect_redundancy(threshold=threshold)
        report["removal_recommendations"] = self.generate_removal_recommendations(threshold)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

        return report
