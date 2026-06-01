"""Research Data Accumulation Plan.

Plans and schedules data accumulation for factor research.
Ensures continuous data collection for alpha research readiness.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from enum import Enum
import json

from src.factors import registry
from src.factors.store import FactorStore


class DataPriority(str, Enum):
    """Data accumulation priority levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DataAccumulationPlanner:
    """Plans research data accumulation."""

    MIN_HISTORY_DAYS = 252  # ~1 year of trading days
    IDEAL_HISTORY_DAYS = 504  # ~2 years
    TARGET_COVERAGE = 0.95

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        registry.discover_factors()

    def assess_data_gap(self, factor_name: str) -> Dict[str, Any]:
        """Assess data gap for a factor."""
        history = self.store.get_factor_history(factor_name, days=365)
        current_days = len(history)

        gap_to_min = max(0, self.MIN_HISTORY_DAYS - current_days)
        gap_to_ideal = max(0, self.IDEAL_HISTORY_DAYS - current_days)

        if current_days >= self.IDEAL_HISTORY_DAYS:
            status = "SUFFICIENT"
            priority = DataPriority.LOW
        elif current_days >= self.MIN_HISTORY_DAYS:
            status = "ADEQUATE"
            priority = DataPriority.MEDIUM
        elif current_days >= self.MIN_HISTORY_DAYS * 0.5:
            status = "INSUFFICIENT"
            priority = DataPriority.HIGH
        else:
            status = "CRITICAL"
            priority = DataPriority.CRITICAL

        return {
            "factor_name": factor_name,
            "current_days": current_days,
            "min_required": self.MIN_HISTORY_DAYS,
            "ideal_target": self.IDEAL_HISTORY_DAYS,
            "gap_to_min": gap_to_min,
            "gap_to_ideal": gap_to_ideal,
            "status": status,
            "priority": priority.value,
            "coverage_pct": round(current_days / self.IDEAL_HISTORY_DAYS * 100, 1)
        }

    def compute_accumulation_schedule(self, factor_name: str) -> Dict[str, Any]:
        """Compute accumulation schedule for a factor."""
        gap = self.assess_data_gap(factor_name)

        priority = DataPriority(gap["priority"])
        days_needed = gap["gap_to_ideal"]

        if priority == DataPriority.CRITICAL:
            collection_frequency = "daily"
            target_completion_days = days_needed
        elif priority == DataPriority.HIGH:
            collection_frequency = "daily"
            target_completion_days = days_needed
        elif priority == DataPriority.MEDIUM:
            collection_frequency = "daily"
            target_completion_days = days_needed
        else:
            collection_frequency = "weekly"
            target_completion_days = days_needed * 7

        estimated_completion = datetime.now() + timedelta(days=target_completion_days)

        return {
            **gap,
            "collection_frequency": collection_frequency,
            "estimated_completion_date": estimated_completion.strftime("%Y-%m-%d"),
            "daily_collections_needed": days_needed
        }

    def plan_all_factors(self) -> List[Dict[str, Any]]:
        """Plan accumulation for all factors."""
        results = []
        for name in registry._factors.keys():
            try:
                schedule = self.compute_accumulation_schedule(name)
                results.append(schedule)
            except Exception as e:
                results.append({
                    "factor_name": name,
                    "error": str(e),
                    "status": "ERROR"
                })

        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return sorted(results, key=lambda x: priority_order.get(x.get("priority", "LOW"), 3))

    def get_critical_gaps(self) -> List[Dict[str, Any]]:
        """Get factors with critical data gaps."""
        plan = self.plan_all_factors()
        return [p for p in plan if p.get("priority") in ["CRITICAL", "HIGH"]]

    def estimate_total_effort(self) -> Dict[str, Any]:
        """Estimate total accumulation effort."""
        plan = self.plan_all_factors()

        total_days_needed = sum(p.get("gap_to_ideal", 0) for p in plan)
        critical_count = len([p for p in plan if p.get("priority") == "CRITICAL"])
        high_count = len([p for p in plan if p.get("priority") == "HIGH"])

        avg_coverage = sum(p.get("coverage_pct", 0) for p in plan) / len(plan) if plan else 0

        return {
            "total_factors": len(plan),
            "total_collection_days_needed": total_days_needed,
            "critical_priority": critical_count,
            "high_priority": high_count,
            "average_coverage_pct": round(avg_coverage, 1),
            "estimated_completion_date": self._estimate_project_completion(plan)
        }

    def _estimate_project_completion(self, plan: List[Dict]) -> str:
        """Estimate overall project completion date."""
        max_days = max(p.get("gap_to_ideal", 0) for p in plan) if plan else 0
        completion = datetime.now() + timedelta(days=max_days)
        return completion.strftime("%Y-%m-%d")

    def generate_accumulation_plan(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive accumulation plan."""
        plan = self.plan_all_factors()
        effort = self.estimate_total_effort()
        critical = self.get_critical_gaps()

        by_priority = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for p in plan:
            priority = p.get("priority", "LOW")
            if priority in by_priority:
                by_priority[priority].append(p["factor_name"])

        report = {
            "report_date": datetime.now().isoformat(),
            "target_coverage_days": self.IDEAL_HISTORY_DAYS,
            "minimum_coverage_days": self.MIN_HISTORY_DAYS,
            "summary": effort,
            "by_priority": by_priority,
            "critical_gaps": [{"name": c["factor_name"], "gap": c["gap_to_ideal"]} for c in critical],
            "plan": plan
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

        return report

    def print_accumulation_summary(self):
        """Print accumulation summary."""
        plan = self.plan_all_factors()
        effort = self.estimate_total_effort()

        print("\nResearch Data Accumulation Plan")
        print("=" * 70)
        print(f"Total Factors: {effort['total_factors']}")
        print(f"Average Coverage: {effort['average_coverage_pct']:.1f}%")
        print(f"Critical Priority: {effort['critical_priority']}")
        print(f"High Priority: {effort['high_priority']}")
        print(f"Estimated Completion: {effort['estimated_completion_date']}")
        print("-" * 70)

        for item in plan[:15]:
            days = item.get("current_days", 0)
            status = item.get("status", "UNKNOWN")
            priority = item.get("priority", "LOW")
            print(f"{item['factor_name']:<30} {days:>4} days [{priority:<8}] {status}")
