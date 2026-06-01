"""Factor Drift Analysis.

Detects factor value drift from historical baseline.
Identifies factors that are deviating from normal behavior.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import numpy as np

from src.factors import registry
from src.factors.store import FactorStore


class FactorDriftAnalyzer:
    """Analyzes factor drift from historical baseline."""

    DRIFT_THRESHOLD_LOW = 0.5
    DRIFT_THRESHOLD_MEDIUM = 1.0
    DRIFT_THRESHOLD_HIGH = 2.0

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        registry.discover_factors()

    def compute_baseline(self, factor_name: str, days: int = 90) -> Dict[str, float]:
        """Compute historical baseline statistics."""
        history = self.store.get_factor_history(factor_name, days=days)
        if not history:
            return {"mean": 0.5, "std": 0.1, "min": 0.0, "max": 1.0}

        values = [h.get("normalized_value", 0.5) for h in history]
        values = [v for v in values if v is not None and not np.isnan(v)]

        if not values:
            return {"mean": 0.5, "std": 0.1, "min": 0.0, "max": 1.0}

        return {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)) if len(values) > 1 else 0.1,
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "count": len(values)
        }

    def compute_drift(self, factor_name: str, days: int = 30, baseline_days: int = 90) -> Dict[str, Any]:
        """Compute factor drift from baseline.

        Drift = (current_mean - baseline_mean) / baseline_std
        """
        baseline = self.compute_baseline(factor_name, days=baseline_days)
        recent = self.compute_baseline(factor_name, days=days)

        baseline_mean = baseline["mean"]
        baseline_std = baseline["std"]
        recent_mean = recent["mean"]

        if baseline_std < 1e-6:
            baseline_std = 0.1

        drift_zscore = (recent_mean - baseline_mean) / baseline_std

        if abs(drift_zscore) < self.DRIFT_THRESHOLD_LOW:
            status = "STABLE"
        elif abs(drift_zscore) < self.DRIFT_THRESHOLD_MEDIUM:
            status = "MINOR_DRIFT"
        elif abs(drift_zscore) < self.DRIFT_THRESHOLD_HIGH:
            status = "MODERATE_DRIFT"
        else:
            status = "SEVERE_DRIFT"

        direction = "UP" if drift_zscore > 0 else "DOWN" if drift_zscore < 0 else "FLAT"

        return {
            "factor_name": factor_name,
            "baseline_mean": round(baseline_mean, 4),
            "recent_mean": round(recent_mean, 4),
            "drift_zscore": round(drift_zscore, 4),
            "drift_direction": direction,
            "drift_status": status,
            "baseline_std": round(baseline_std, 4)
        }

    def compute_trend(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        """Compute factor trend using linear regression."""
        history = self.store.get_factor_history(factor_name, days=days)
        if len(history) < 5:
            return {"trend_slope": 0.0, "trend_r2": 0.0, "trend_direction": "INSUFFICIENT_DATA"}

        values = [h.get("normalized_value", 0.5) for h in history]
        values = [v for v in values if v is not None and not np.isnan(v)]

        if len(values) < 5:
            return {"trend_slope": 0.0, "trend_r2": 0.0, "trend_direction": "INSUFFICIENT_DATA"}

        x = np.arange(len(values))
        y = np.array(values)

        slope, intercept = np.polyfit(x, y, 1)

        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        if abs(slope) < 0.001:
            direction = "FLAT"
        elif slope > 0:
            direction = "UP"
        else:
            direction = "DOWN"

        return {
            "trend_slope": round(slope, 6),
            "trend_r2": round(r2, 4),
            "trend_direction": direction,
            "days_analyzed": len(values)
        }

    def analyze_factor_drift(self, factor_name: str, days: int = 30) -> Dict[str, Any]:
        """Complete drift analysis for a factor."""
        drift = self.compute_drift(factor_name, days=days)
        trend = self.compute_trend(factor_name, days=days)

        combined_status = drift["drift_status"]
        if trend["trend_r2"] > 0.5:
            if trend["trend_direction"] == "UP" and drift["drift_zscore"] > 0:
                combined_status = f"{drift['drift_status']}_TREND_UP"
            elif trend["trend_direction"] == "DOWN" and drift["drift_zscore"] < 0:
                combined_status = f"{drift['drift_status']}_TREND_DOWN"

        return {
            **drift,
            "trend_slope": trend["trend_slope"],
            "trend_r2": trend["trend_r2"],
            "trend_direction": trend["trend_direction"],
            "combined_status": combined_status,
            "alert_level": self._get_alert_level(drift["drift_status"])
        }

    def _get_alert_level(self, status: str) -> str:
        """Convert status to alert level."""
        if "SEVERE" in status:
            return "HIGH"
        elif "MODERATE" in status:
            return "MEDIUM"
        elif "MINOR" in status:
            return "LOW"
        return "NONE"

    def analyze_all_factors(self, days: int = 30) -> List[Dict[str, Any]]:
        """Analyze drift for all factors."""
        results = []
        for name in registry._factors.keys():
            try:
                analysis = self.analyze_factor_drift(name, days=days)
                results.append(analysis)
            except Exception as e:
                results.append({
                    "factor_name": name,
                    "error": str(e),
                    "drift_status": "ERROR"
                })

        return sorted(results, key=lambda x: -abs(x.get("drift_zscore", 0)))

    def get_drifting_factors(self, threshold: str = "MODERATE") -> List[str]:
        """Get factors with significant drift."""
        analysis = self.analyze_all_factors()
        threshold_map = {"MINOR": 1, "MODERATE": 2, "SEVERE": 3}
        level = threshold_map.get(threshold, 2)

        drifting = []
        for a in analysis:
            status = a.get("drift_status", "STABLE")
            severity = 0
            if "SEVERE" in status:
                severity = 3
            elif "MODERATE" in status:
                severity = 2
            elif "MINOR" in status:
                severity = 1

            if severity >= level:
                drifting.append(a["factor_name"])

        return drifting

    def generate_drift_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive drift report."""
        analysis = self.analyze_all_factors()

        severe = [a for a in analysis if "SEVERE" in a.get("drift_status", "")]
        moderate = [a for a in analysis if "MODERATE" in a.get("drift_status", "")]
        minor = [a for a in analysis if "MINOR" in a.get("drift_status", "")]
        stable = [a for a in analysis if a.get("drift_status") == "STABLE"]

        report = {
            "report_date": datetime.now().isoformat(),
            "summary": {
                "total_factors": len(analysis),
                "severe_drift": len(severe),
                "moderate_drift": len(moderate),
                "minor_drift": len(minor),
                "stable": len(stable)
            },
            "severe_drift_factors": [a["factor_name"] for a in severe],
            "moderate_drift_factors": [a["factor_name"] for a in moderate],
            "analysis": analysis
        }

        if output_path:
            import json
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

        return report

    def print_drift_summary(self, days: int = 30):
        """Print drift summary table."""
        analysis = self.analyze_all_factors(days=days)

        print(f"\nFactor Drift Analysis ({days} days)")
        print("=" * 70)

        for item in analysis[:20]:
            if "error" in item:
                print(f"{item['factor_name']:<30} ERROR: {item['error']}")
                continue

            status = item.get("drift_status", "UNKNOWN")
            zscore = item.get("drift_zscore", 0)
            direction = item.get("drift_direction", "FLAT")

            print(f"{item['factor_name']:<30} z={zscore:>6.2f} {direction:<4} {status}")
