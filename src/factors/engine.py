"""Factor Engine: Orchestrates factor computation, normalization, and storage."""
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import inspect
import logging

logger = logging.getLogger(__name__)

from src.factors.registry import registry
from src.factors.store import FactorStore
from src.factors.normalization import NormalizationPipeline
from src.factors.models import FactorValue


class FactorEngine:
    """Orchestrates factor computation pipeline.

    Example:
        >>> engine = FactorEngine()
        >>> engine.discover_factors()
        >>> result = engine.compute_factor('funding_rate', 'bitcoin')
        >>> engine.save_daily_factors('2026-05-29', 'bitcoin')
    """

    def __init__(self, store_dir: Path = Path("data/factors")):
        self.store = FactorStore(store_dir)
        self.pipeline = NormalizationPipeline()
        self._discovered = False

    def discover_factors(self) -> int:
        """Discover all registered factors."""
        if not self._discovered:
            count = registry.discover_factors()
            self._discovered = True
            return count
        return 0

    def compute_factor(
        self,
        factor_name: str,
        *args,
        historical_values: Optional[List[float]] = None,
        **kwargs
    ) -> FactorValue:
        """Compute a single factor with full normalization."""
        metadata = registry.get_factor(factor_name)
        if metadata is None:
            raise ValueError(f"Unknown factor: {factor_name}")

        compute_func = registry.get_compute_func(factor_name)
        if compute_func is None:
            raise ValueError(f"No compute function: {factor_name}")

        # Data quantity check
        if historical_values and (metadata.min_days > 0 or metadata.min_points > 0):
            actual_points = len(historical_values)
            unique_dates = set()
            for v in historical_values:
                if isinstance(v, dict) and v.get('date'):
                    unique_dates.add(v.get('date'))
            actual_days = len(unique_dates)

            # Check min_points
            if metadata.min_points > 0 and actual_points < metadata.min_points:
                logger.debug(f"Insufficient data points for {factor_name}: {actual_points} < {metadata.min_points}")
                return FactorValue(
                    name=factor_name,
                    raw_value=float('nan'),
                    confidence=0,
                    timestamp=datetime.now().isoformat(),
                    metadata={"reason": "insufficient_data_points", "actual": actual_points, "required": metadata.min_points}
                )

            # Check min_days
            if metadata.min_days > 0 and actual_days < metadata.min_days:
                logger.debug(f"Insufficient days for {factor_name}: {actual_days} < {metadata.min_days}")
                return FactorValue(
                    name=factor_name,
                    raw_value=float('nan'),
                    confidence=0,
                    timestamp=datetime.now().isoformat(),
                    metadata={"reason": "insufficient_days", "actual": actual_days, "required": metadata.min_days}
                )

        raw_value = compute_func(*args, **kwargs)

        result = self.pipeline.transform(
            raw_value,
            historical_values=historical_values,
            min_value=metadata.typical_range[0] if metadata.typical_range else None,
            max_value=metadata.typical_range[1] if metadata.typical_range else None
        )

        # Apply custom normalizer if exists
        normalizer = registry.get_normalizer(factor_name)
        if normalizer:
            result["normalized"] = normalizer(raw_value)
            result["score"] = self.pipeline.score(result["normalized"])

        return FactorValue(
            name=factor_name,
            raw_value=result["raw_value"],
            normalized_value=result["normalized"],
            zscore=result["zscore"],
            percentile=result["percentile"],
            score=result["score"],
            confidence=metadata.confidence,
            timestamp=datetime.now().isoformat(),
            metadata={
                "display_name": metadata.display_name,
                "category": metadata.category.value,
                "source": metadata.source.value
            }
        )

    def compute_all_factors(self, coin_id: str) -> Dict[str, FactorValue]:
        """Compute all applicable factors for a coin."""
        results = {}
        for name in registry._factors:
            try:
                func = registry.get_compute_func(name)
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())

                if 'coin_id' in params:
                    results[name] = self.compute_factor(name, coin_id)
                elif len(params) == 0:
                    results[name] = self.compute_factor(name)
            except Exception as e:
                print(f"Warning: {name} failed: {e}")

        return results

    def save_daily_factors(self, date_str: str, coin_id: str, factors: Dict[str, FactorValue] = None) -> None:
        """Save factors to store."""
        if factors is None:
            factors = self.compute_all_factors(coin_id)
        factors_dict = {name: fv.to_dict() for name, fv in factors.items()}
        self.store.save_factors(date_str, factors_dict, coin_id)

    def list_factors(self) -> List[str]:
        return list(registry._factors.keys())
