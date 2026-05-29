"""Cache system for market data.

Version Control:
- All cached data includes a '_version' field
- When data structure changes, increment CACHE_VERSION
- Old caches will be automatically invalidated
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


# Increment this when data structure changes significantly
CACHE_VERSION = "1.0"


class DataCache:
    """Manages local file-based cache for market data.

    Attributes:
        cache_dir: Directory to store cache files
        expire_hours: Hours before cache expires

    Example:
        >>> cache = DataCache(Path("data/cache"), expire_hours=24)
        >>> cache.save("btc_price", {"price": 50000})
        >>> data = cache.load("btc_price")
    """

    def __init__(
        self,
        cache_dir: Path = Path("data/cache"),
        expire_hours: int = 24
    ):
        """Initialize cache system.

        Args:
            cache_dir: Directory to store cache files
            expire_hours: Hours before cache is considered stale
        """
        self.cache_dir = Path(cache_dir)
        self.expire_hours = expire_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for a cache key.

        Args:
            key: Cache key identifier

        Returns:
            Path to cache file
        """
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_key}.json"

    def save(self, key: str, data: Any) -> None:
        """Save data to cache with version.

        Args:
            key: Cache key identifier
            data: Data to cache (must be JSON serializable)
        """
        cache_path = self._get_cache_path(key)

        # Add version to data
        if isinstance(data, dict):
            data_with_version = {**data, "_version": CACHE_VERSION}
        else:
            # For non-dict data, wrap in dict
            data_with_version = {"data": data, "_version": CACHE_VERSION}

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data_with_version, f, ensure_ascii=False, indent=2)

    def load(self, key: str) -> Optional[Any]:
        """Load data from cache with version check.

        Args:
            key: Cache key identifier

        Returns:
            Cached data if valid and version matches, None otherwise
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        # Check if cache is expired
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=self.expire_hours):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check version
            if isinstance(data, dict):
                cached_version = data.get("_version")
                if cached_version != CACHE_VERSION:
                    # Version mismatch - invalidate cache
                    return None
                # Return data without version field
                result = {k: v for k, v in data.items() if k != "_version"}
                return result if result else None
            else:
                # Legacy cache without version - consider invalid
                return None
        except (json.JSONDecodeError, KeyError):
            # Corrupted cache
            return None

    def clear(self) -> None:
        """Clear all cached data."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()