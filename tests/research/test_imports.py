"""Smoke test: the entire src.research package and its public classes import cleanly.

src.research has no tests of its own; this guards against import-time breakage
(e.g. a missing optional dependency) across all 17 submodules.
"""
import src.research
from src.research import (
    AlphaReadinessAssessor,
    DataAccumulationPlanner,
    EffectiveFactorCountAnalyzer,
    FactorClassifier,
    FactorCorrelationAnalyzer,
    FactorCoverageAnalyzer,
    FactorDatabase,
    FactorDiscriminationAnalyzer,
    FactorDriftAnalyzer,
    FactorHealthDashboard,
    FactorLifecycleManager,
    FactorMissingRateAnalyzer,
    FactorRanking,
    FactorRetirementAdvisor,
    FactorStabilityAnalyzer,
    HierarchicalWeighting,
    RedundancyDetector,
)
from src.research.classification import FactorClassification


def test_package_and_classes_importable():
    assert src.research is not None
    assert FactorClassifier is not None
    assert FactorClassification is not None
    assert RedundancyDetector is not None
    assert FactorStabilityAnalyzer is not None
    assert FactorMissingRateAnalyzer is not None
    assert FactorCorrelationAnalyzer is not None
    assert FactorCoverageAnalyzer is not None
    assert FactorDiscriminationAnalyzer is not None
    assert EffectiveFactorCountAnalyzer is not None
    assert HierarchicalWeighting is not None
    assert FactorDriftAnalyzer is not None
    assert FactorHealthDashboard is not None
    assert FactorRetirementAdvisor is not None
    assert AlphaReadinessAssessor is not None
    assert FactorLifecycleManager is not None
    assert DataAccumulationPlanner is not None
    assert FactorRanking is not None
    assert FactorDatabase is not None
