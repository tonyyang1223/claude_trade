"""Factor Research Module.

Provides:
- Factor Classification System
- Correlation Analysis
- Redundancy Detection
- Hierarchical Weighting
"""
from src.research.classification import FactorClassifier, classify_all_factors
from src.research.correlation import FactorCorrelationAnalyzer
from src.research.redundancy import RedundancyDetector
from src.research.weighting import HierarchicalWeighting

__all__ = [
    "FactorClassifier",
    "classify_all_factors",
    "FactorCorrelationAnalyzer",
    "RedundancyDetector",
    "HierarchicalWeighting"
]
