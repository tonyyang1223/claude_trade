"""Factor models and metadata definitions."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class FactorCategory(str, Enum):
    """Factor category classification."""
    MARKET = "market"
    TECHNICAL = "technical"
    ONCHAIN = "onchain"
    SENTIMENT = "sentiment"
    SOCIAL = "social"
    DEVELOPER = "developer"
    DERIVATIVES = "derivatives"
    FUNDAMENTAL = "fundamental"
    WHALE = "whale"


class FactorSource(str, Enum):
    """Data source for factor calculation."""
    COINGECKO = "coingecko"
    BINANCE = "binance"
    DEFILLAMA = "defillama"
    GITHUB = "github"
    REDDIT = "reddit"
    FEAR_GREED = "fear_greed"
    BLOCKCHAIN = "blockchain"
    WHALE_ALERT = "whale_alert"


@dataclass
class FactorMetadata:
    """Metadata for a factor.

    Attributes:
        name: Unique factor identifier (e.g., 'funding_rate')
        display_name: Human readable name (e.g., 'Funding Rate')
        category: Factor category
        source: Data source
        description: What this factor measures
        confidence: Default confidence score (0.0-1.0)
        version: Factor version for tracking changes
        tags: Additional tags for filtering
        higher_is_better: Whether higher values indicate positive signal
        typical_range: Expected value range (min, max)
    """
    name: str
    display_name: str
    category: FactorCategory
    source: FactorSource
    description: str = ""
    confidence: float = 0.9
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    higher_is_better: bool = True
    typical_range: tuple = (0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category.value,
            "source": self.source.value,
            "description": self.description,
            "confidence": self.confidence,
            "version": self.version,
            "tags": self.tags,
            "higher_is_better": self.higher_is_better,
            "typical_range": self.typical_range
        }


@dataclass
class FactorValue:
    """A computed factor value with full context.

    Attributes:
        name: Factor name
        raw_value: Raw computed value
        normalized_value: Normalized value (0-1)
        zscore: Z-score relative to historical distribution
        percentile: Percentile rank
        score: Final score (1-5)
        confidence: Data confidence for this specific value
        timestamp: When this value was computed
        metadata: Additional context
    """
    name: str
    raw_value: float
    normalized_value: Optional[float] = None
    zscore: Optional[float] = None
    percentile: Optional[float] = None
    score: Optional[int] = None
    confidence: float = 0.9
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "zscore": self.zscore,
            "percentile": self.percentile,
            "score": self.score,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @property
    def contribution_explanation(self) -> str:
        """Generate human-readable explanation of factor contribution."""
        parts = [f"Factor: {self.name}"]
        parts.append(f"  Raw value: {self.raw_value:.4f}")
        if self.normalized_value is not None:
            parts.append(f"  Normalized: {self.normalized_value:.4f}")
        if self.zscore is not None:
            parts.append(f"  Z-score: {self.zscore:.2f}")
        if self.percentile is not None:
            parts.append(f"  Percentile: {self.percentile:.1f}%")
        if self.score is not None:
            parts.append(f"  Final score: {self.score}/5")
        parts.append(f"  Confidence: {self.confidence:.0%}")
        return "\n".join(parts)
