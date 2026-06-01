"""Factor Lifecycle Management.

Manages factor lifecycle stages: NEW -> ACTIVE -> MONITORING -> DEPRECATED -> RETIRED.
Tracks factor graduation and retirement decisions.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from enum import Enum
import json

from src.factors import registry
from src.research.stability import FactorStabilityAnalyzer
from src.research.discrimination import FactorDiscriminationAnalyzer
from src.research.coverage import FactorCoverageAnalyzer


class FactorStage(str, Enum):
    """Factor lifecycle stages."""
    NEW = "NEW"
    INCUBATING = "INCUBATING"
    ACTIVE = "ACTIVE"
    MONITORING = "MONITORING"
    DEPRECATED = "DEPRECATED"
    RETIRED = "RETIRED"


class FactorLifecycleManager:
    """Manages factor lifecycle transitions."""

    INCUBATION_DAYS = 30
    GRADUATION_THRESHOLD = 70.0
    MONITORING_THRESHOLD = 50.0
    DEPRECATION_THRESHOLD = 30.0

    STAGE_ORDER = [
        FactorStage.NEW,
        FactorStage.INCUBATING,
        FactorStage.ACTIVE,
        FactorStage.MONITORING,
        FactorStage.DEPRECATED,
        FactorStage.RETIRED
    ]

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.stability = FactorStabilityAnalyzer(store_dir)
        self.discrimination = FactorDiscriminationAnalyzer(store_dir)
        self.coverage = FactorCoverageAnalyzer(store_dir)
        registry.discover_factors()
        self._factor_stages: Dict[str, FactorStage] = {}
        self._load_stages()

    def _load_stages(self) -> None:
        """Load factor stages from registry."""
        for name in registry._factors.keys():
            self._factor_stages[name] = self._factor_stages.get(name, FactorStage.NEW)

    def compute_health_score(self, factor_name: str, days: int = 30) -> float:
        """Compute factor health score (0-100)."""
        stability = self.stability.analyze_factor_health(factor_name, days=days)
        disc = self.discrimination.analyze_factor_discrimination(factor_name, days=days)
        cov = self.coverage.compute_coverage(factor_name, days=days)

        stability_score = stability.get("health_score", 50)
        entropy = disc.get("entropy", 0)
        disc_score = min(100, entropy * 30)
        coverage_score = cov.get("coverage_pct", 0)

        return round(
            stability_score * 0.4 +
            disc_score * 0.3 +
            coverage_score * 0.3,
            1
        )

    def determine_stage(self, factor_name: str, days: int = 30) -> FactorStage:
        """Determine appropriate stage for a factor."""
        health = self.compute_health_score(factor_name, days=days)
        current = self._factor_stages.get(factor_name, FactorStage.NEW)

        history = self.stability.store.get_factor_history(factor_name, days=90)
        data_age = len(history)

        if health >= self.GRADUATION_THRESHOLD:
            if data_age < self.INCUBATION_DAYS:
                return FactorStage.INCUBATING
            return FactorStage.ACTIVE
        elif health >= self.MONITORING_THRESHOLD:
            if current == FactorStage.ACTIVE:
                return FactorStage.MONITORING
            return current
        elif health >= self.DEPRECATION_THRESHOLD:
            if current in [FactorStage.ACTIVE, FactorStage.MONITORING]:
                return FactorStage.DEPRECATED
            return current
        else:
            return FactorStage.RETIRED

    def get_stage_transition(self, factor_name: str) -> Dict[str, Any]:
        """Get stage transition recommendation for a factor."""
        current = self._factor_stages.get(factor_name, FactorStage.NEW)
        recommended = self.determine_stage(factor_name)
        health = self.compute_health_score(factor_name)

        transition_needed = current != recommended

        return {
            "factor_name": factor_name,
            "current_stage": current.value,
            "recommended_stage": recommended.value,
            "health_score": health,
            "transition_needed": transition_needed,
            "action": self._get_action(current, recommended)
        }

    def _get_action(self, current: FactorStage, recommended: FactorStage) -> str:
        """Get action description for transition."""
        if current == recommended:
            return "No action needed"

        transitions = {
            (FactorStage.NEW, FactorStage.INCUBATING): "Begin incubation period",
            (FactorStage.INCUBATING, FactorStage.ACTIVE): "Graduate to active status",
            (FactorStage.ACTIVE, FactorStage.MONITORING): "Move to monitoring due to declining health",
            (FactorStage.MONITORING, FactorStage.DEPRECATED): "Deprecate due to poor performance",
            (FactorStage.DEPRECATED, FactorStage.RETIRED): "Retire factor completely",
            (FactorStage.INCUBATING, FactorStage.RETIRED): "Failed incubation - retire",
        }

        return transitions.get(
            (current, recommended),
            f"Transition from {current.value} to {recommended.value}"
        )

    def update_stage(self, factor_name: str, new_stage: FactorStage) -> None:
        """Update factor stage manually."""
        self._factor_stages[factor_name] = new_stage

    def analyze_all_factors(self, days: int = 30) -> List[Dict[str, Any]]:
        """Analyze lifecycle status for all factors."""
        results = []
        for name in registry._factors.keys():
            try:
                transition = self.get_stage_transition(name)
                results.append(transition)
            except Exception as e:
                results.append({
                    "factor_name": name,
                    "error": str(e),
                    "current_stage": "ERROR"
                })

        return sorted(results, key=lambda x: -x.get("health_score", 0))

    def get_factors_by_stage(self, stage: FactorStage) -> List[str]:
        """Get all factors in a specific stage."""
        return [
            name for name, s in self._factor_stages.items()
            if s == stage
        ]

    def get_graduation_candidates(self) -> List[Dict[str, Any]]:
        """Get factors ready for graduation to ACTIVE status."""
        analysis = self.analyze_all_factors()
        return [
            a for a in analysis
            if a.get("recommended_stage") == FactorStage.ACTIVE.value
            and a.get("current_stage") in [FactorStage.INCUBATING.value, FactorStage.NEW.value]
        ]

    def get_retirement_candidates(self) -> List[Dict[str, Any]]:
        """Get factors candidates for retirement."""
        analysis = self.analyze_all_factors()
        return [
            a for a in analysis
            if a.get("recommended_stage") == FactorStage.RETIRED.value
        ]

    def apply_transitions(self, auto: bool = False) -> Dict[str, List[str]]:
        """Apply all pending stage transitions."""
        analysis = self.analyze_all_factors()

        transitions = {"graduated": [], "deprecated": [], "retired": [], "unchanged": []}

        for a in analysis:
            if "error" in a:
                continue

            factor_name = a["factor_name"]
            current = FactorStage(a["current_stage"])
            recommended = FactorStage(a["recommended_stage"])

            if current != recommended:
                if auto:
                    self.update_stage(factor_name, recommended)

                if recommended == FactorStage.ACTIVE:
                    transitions["graduated"].append(factor_name)
                elif recommended == FactorStage.DEPRECATED:
                    transitions["deprecated"].append(factor_name)
                elif recommended == FactorStage.RETIRED:
                    transitions["retired"].append(factor_name)
            else:
                transitions["unchanged"].append(factor_name)

        return transitions

    def generate_lifecycle_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """Generate comprehensive lifecycle report."""
        analysis = self.analyze_all_factors()

        stage_counts = {stage.value: 0 for stage in FactorStage}
        for a in analysis:
            if "error" not in a:
                stage = a.get("current_stage", "NEW")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1

        graduation = self.get_graduation_candidates()
        retirement = self.get_retirement_candidates()

        report = {
            "report_date": datetime.now().isoformat(),
            "summary": {
                "total_factors": len(analysis),
                "stage_distribution": stage_counts,
                "graduation_candidates": len(graduation),
                "retirement_candidates": len(retirement)
            },
            "graduation_candidates": [g["factor_name"] for g in graduation],
            "retirement_candidates": [r["factor_name"] for r in retirement],
            "analysis": analysis
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2, default=str)

        return report

    def print_lifecycle_summary(self):
        """Print lifecycle summary table."""
        analysis = self.analyze_all_factors()

        print("\nFactor Lifecycle Summary")
        print("=" * 70)

        stage_groups = {stage.value: [] for stage in FactorStage}
        for a in analysis:
            if "error" not in a:
                stage = a.get("current_stage", "NEW")
                stage_groups[stage].append(a)

        for stage in self.STAGE_ORDER:
            factors = stage_groups.get(stage.value, [])
            if factors:
                print(f"\n{stage.value}:")
                print("-" * 40)
                for f in factors[:10]:
                    print(f"  {f['factor_name']:<30} health={f['health_score']:<5.1f}")