"""Cache system for market data.

Version Control:
- All cached data includes a '_version' field
- When data structure changes, increment CACHE_VERSION
- Old caches will be automatically invalidated
- Version history:
  - 1.0: Initial version
  - 1.1: Added proper list unwrapping support
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


# Increment this when data structure changes significantly
CACHE_VERSION = "1.1"


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
        elif isinstance(data, list):
            # Mark list data so load() can unwrap it correctly
            data_with_version = {
                "data": data,
                "_version": CACHE_VERSION,
                "_wrapped_list": True
            }
        else:
            # For other types (str, int, etc.), wrap in dict
            data_with_version = {"data": data, "_version": CACHE_VERSION}

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data_with_version, f, ensure_ascii=False, indent=2)

    def load(self, key: str) -> Optional[Any]:
        """Load data from cache with version check.

        Args:
            key: Cache key identifier

        Returns:
            Cached data if valid and version matches, None otherwise.
            Returns the original data type (dict, list, etc.)
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

                # Check if this is a wrapped list (saved from non-dict data)
                if "_wrapped_list" in data:
                    return data.get("data")

                # Return dict data without version field
                result = {k: v for k, v in data.items() if k.startswith("_") is False}
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

    def clear_expired(self) -> int:
        """Clear expired cache files.

        Returns:
            Number of files cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime > timedelta(hours=self.expire_hours):
                cache_file.unlink()
                count += 1
        return count

    def clear_by_pattern(self, pattern: str) -> int:
        """Clear cache files matching a pattern.

        Args:
            pattern: Glob pattern to match (e.g., "v2ex_*")

        Returns:
            Number of files cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob(f"{pattern}.json"):
            cache_file.unlink()
            count += 1
        return count

    def clear_version_mismatch(self) -> int:
        """Clear all cache files with mismatched version.

        Returns:
            Number of files cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cached_version = data.get("_version")
                    if cached_version != CACHE_VERSION:
                        cache_file.unlink()
                        count += 1
            except (json.JSONDecodeError, KeyError):
                # Corrupted cache - clear it
                cache_file.unlink()
                count += 1
        return count

    def stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)

        expired = 0
        valid = 0
        mismatched = 0

        for f in files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if datetime.now() - mtime > timedelta(hours=self.expire_hours):
                expired += 1
            else:
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        data = json.load(file)
                    if isinstance(data, dict):
                        if data.get("_version") == CACHE_VERSION:
                            valid += 1
                        else:
                            mismatched += 1
                except:
                    mismatched += 1

        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "valid": valid,
            "expired": expired,
            "version_mismatched": mismatched,
            "cache_version": CACHE_VERSION,
        }