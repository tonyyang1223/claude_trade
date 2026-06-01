"""Factor Engineering System.

This module provides a systematic approach to factor computation, normalization,
and historical storage for cryptocurrency evaluation.

Key components:
- FactorRegistry: Central registry for auto-discovering factors
- register_factor: Decorator for registering new factors
- FactorStore: Historical factor storage (parquet/JSON)
- NormalizationPipeline: Transform raw values to scores
- FactorCategory/FactorSource: Enums for classification
- FactorMetadata/FactorValue: Data models for factor documentation

Example:
    >>> from src.factors import registry, FactorStore, NormalizationPipeline
    >>> registry.discover_factors()
    >>> store = FactorStore()
    >>> pipeline = NormalizationPipeline()
"""

from src.factors.models import (
    FactorMetadata,
    FactorValue,
    FactorCategory,
    FactorSource
)
from src.factors.registry import (
    FactorRegistry,
    registry,
    register_factor
)
from src.factors.store import FactorStore
from src.factors.normalization import NormalizationPipeline
from src.factors.engine import FactorEngine

__all__ = [
    "FactorRegistry",
    "registry",
    "register_factor",
    "FactorStore",
    "NormalizationPipeline",
    "FactorMetadata",
    "FactorValue",
    "FactorCategory",
    "FactorSource",
    "FactorEngine",
]