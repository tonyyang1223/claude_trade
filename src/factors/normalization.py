"""Factor Normalization Pipeline.

Transforms raw factor values through:
    raw_value → clean → winsorize → normalize → zscore → percentile → score

Each stage is independently callable for debugging.
"""
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from scipy import stats


class NormalizationPipeline:
    """Pipeline for normalizing factor values.

    Example:
        >>> pipeline = NormalizationPipeline()
        >>> # Stage by stage
        >>> cleaned = pipeline.clean(raw_value)
        >>> winsorized = pipeline.winsorize(cleaned, history)
        >>> # Full pipeline
        >>> result = pipeline.transform(0.01, historical_values=[...])
    """

    def __init__(
        self,
        winsorize_limits: Tuple[float, float] = (0.05, 0.05),
        score_thresholds: Tuple[float, float, float, float] = (0.2, 0.4, 0.6, 0.8)
    ):
        self.winsorize_limits = winsorize_limits
        self.score_thresholds = score_thresholds

    def clean(self, raw_value: float) -> float:
        """Stage 1: Clean raw value. Handles None/NaN/Inf."""
        if raw_value is None:
            return 0.0
        if isinstance(raw_value, float) and np.isnan(raw_value):
            return 0.0
        if np.isinf(raw_value):
            return 1e9 if raw_value > 0 else -1e9
        return float(raw_value)

    def winsorize(self, value: float, history: Optional[List[float]] = None) -> float:
        """Stage 2: Clip outliers at percentiles."""
        if history is None or len(history) < 10:
            return value
        clean_history = [self.clean(v) for v in history]
        lower = np.percentile(clean_history, self.winsorize_limits[0] * 100)
        upper = np.percentile(clean_history, (1 - self.winsorize_limits[1]) * 100)
        return max(lower, min(upper, value))

    def normalize(
        self,
        value: float,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        history: Optional[List[float]] = None
    ) -> float:
        """Stage 3: Normalize to 0-1 scale."""
        if min_val is not None and max_val is not None:
            if max_val == min_val:
                return 0.5
            return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
        if history and len(history) >= 2:
            clean_history = [self.clean(v) for v in history]
            h_min, h_max = min(clean_history), max(clean_history)
            if h_max == h_min:
                return 0.5
            return max(0.0, min(1.0, (value - h_min) / (h_max - h_min)))
        return value

    def zscore(self, value: float, history: Optional[List[float]] = None) -> float:
        """Stage 4: Compute Z-score."""
        if history is None or len(history) < 5:
            return 0.0
        clean_history = [self.clean(v) for v in history]
        mean, std = np.mean(clean_history), np.std(clean_history)
        if std == 0:
            return 0.0
        return (value - mean) / std

    def percentile(self, value: float, history: Optional[List[float]] = None) -> float:
        """Stage 5: Compute percentile rank."""
        if history is None or len(history) < 5:
            return 50.0
        clean_history = [self.clean(v) for v in history]
        return float(stats.percentileofscore(clean_history, value))

    def score(self, normalized: float) -> int:
        """Stage 6: Convert normalized to 1-5 score."""
        t1, t2, t3, t4 = self.score_thresholds
        if normalized < t1: return 1
        elif normalized < t2: return 2
        elif normalized < t3: return 3
        elif normalized < t4: return 4
        else: return 5

    def transform(
        self,
        raw_value: float,
        historical_values: Optional[List[float]] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Full normalization pipeline returning all stages."""
        cleaned = self.clean(raw_value)
        winsorized = self.winsorize(cleaned, historical_values)
        normalized = self.normalize(winsorized, min_value, max_value, historical_values)
        zs = self.zscore(winsorized, historical_values)
        pct = self.percentile(winsorized, historical_values)
        final_score = self.score(normalized)

        return {
            "raw_value": raw_value,
            "cleaned": cleaned,
            "winsorized": winsorized,
            "normalized": normalized,
            "zscore": zs,
            "percentile": pct,
            "score": final_score
        }