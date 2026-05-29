"""Factor Registry System for auto-discovery and management of factors."""
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Callable
from functools import wraps

from src.factors.models import FactorMetadata, FactorCategory, FactorSource


class FactorRegistry:
    """Central registry for all factors.

    Supports auto-discovery of factors from the factors/ directory.
    Each factor is registered with its metadata and computation function.

    Example:
        >>> registry = FactorRegistry()
        >>> registry.discover_factors()
        >>> all_factors = registry.list_factors()
        >>> funding_rate = registry.get_factor('funding_rate')
    """

    _instance: Optional['FactorRegistry'] = None

    def __init__(self):
        self._factors: Dict[str, FactorMetadata] = {}
        self._compute_funcs: Dict[str, Callable] = {}
        self._normalize_funcs: Dict[str, Callable] = {}

    @classmethod
    def get_instance(cls) -> 'FactorRegistry':
        """Get singleton instance of registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        name: str,
        display_name: str,
        category: FactorCategory,
        source: FactorSource,
        description: str = "",
        confidence: float = 0.9,
        version: str = "1.0.0",
        tags: List[str] = None,
        higher_is_better: bool = True,
        typical_range: tuple = (0.0, 1.0)
    ) -> Callable:
        """Decorator to register a factor.

        Args:
            name: Unique factor identifier
            display_name: Human readable name
            category: Factor category
            source: Data source
            description: What this factor measures
            confidence: Default confidence (0.0-1.0)
            version: Factor version
            tags: Additional tags
            higher_is_better: Whether higher values are positive
            typical_range: Expected value range

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            metadata = FactorMetadata(
                name=name,
                display_name=display_name,
                category=category,
                source=source,
                description=description,
                confidence=confidence,
                version=version,
                tags=tags or [],
                higher_is_better=higher_is_better,
                typical_range=typical_range
            )

            self._factors[name] = metadata
            self._compute_funcs[name] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper._factor_metadata = metadata
            return wrapper

        return decorator

    def register_normalizer(self, factor_name: str) -> Callable:
        """Decorator to register a custom normalizer for a factor."""
        def decorator(func: Callable) -> Callable:
            self._normalize_funcs[factor_name] = func
            return func
        return decorator

    def get_factor(self, name: str) -> Optional[FactorMetadata]:
        """Get factor metadata by name."""
        return self._factors.get(name)

    def get_compute_func(self, name: str) -> Optional[Callable]:
        """Get compute function for a factor."""
        return self._compute_funcs.get(name)

    def get_normalizer(self, name: str) -> Optional[Callable]:
        """Get normalizer function for a factor."""
        return self._normalize_funcs.get(name)

    def list_factors(
        self,
        category: Optional[FactorCategory] = None,
        source: Optional[FactorSource] = None,
        tags: Optional[List[str]] = None
    ) -> List[FactorMetadata]:
        """List all registered factors, optionally filtered."""
        factors = list(self._factors.values())

        if category:
            factors = [f for f in factors if f.category == category]

        if source:
            factors = [f for f in factors if f.source == source]

        if tags:
            factors = [f for f in factors if any(t in f.tags for t in tags)]

        return factors

    def list_categories(self) -> List[str]:
        """List all available factor categories."""
        return [c.value for c in FactorCategory]

    def list_sources(self) -> List[str]:
        """List all available data sources."""
        return [s.value for s in FactorSource]

    def discover_factors(self) -> int:
        """Auto-discover factors from src/factors/ directory.

        Returns:
            Number of factors discovered
        """
        factors_dir = Path(__file__).parent
        initial_count = len(self._factors)

        for module_path in factors_dir.glob("*.py"):
            if module_path.name.startswith("_"):
                continue

            module_name = module_path.stem
            try:
                importlib.import_module(f"src.factors.{module_name}")
            except ImportError as e:
                print(f"Warning: Failed to import {module_name}: {e}")

        return len(self._factors) - initial_count

    def to_dict(self) -> Dict[str, Any]:
        """Export registry to dictionary."""
        return {
            "factors": {name: meta.to_dict() for name, meta in self._factors.items()},
            "count": len(self._factors)
        }

    def __len__(self) -> int:
        return len(self._factors)

    def __contains__(self, name: str) -> bool:
        return name in self._factors


# Global registry instance
registry = FactorRegistry.get_instance()


def register_factor(
    name: str,
    display_name: str,
    category: FactorCategory,
    source: FactorSource,
    **kwargs
) -> Callable:
    """Convenience decorator for registering factors.

    Example:
        from src.factors import register_factor, FactorCategory, FactorSource

        @register_factor(
            name="funding_rate",
            display_name="Funding Rate",
            category=FactorCategory.DERIVATIVES,
            source=FactorSource.BINANCE,
            description="Perpetual futures funding rate"
        )
        def compute_funding_rate(coin_id: str) -> float:
            ...
    """
    return registry.register(
        name=name,
        display_name=display_name,
        category=category,
        source=source,
        **kwargs
    )
