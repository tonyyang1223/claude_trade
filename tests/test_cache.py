"""Tests for cache system."""
import pytest
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from src.data.cache import DataCache


class TestDataCache:
    """Tests for DataCache class."""

    def test_cache_initialization(self, tmp_path):
        """Test cache initializes with correct directory."""
        cache = DataCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path
        assert tmp_path.exists()

    def test_save_and_load_data(self, tmp_path):
        """Test saving and loading data."""
        cache = DataCache(cache_dir=tmp_path)
        test_data = {"key": "value", "number": 123}

        cache.save("test_key", test_data)
        loaded = cache.load("test_key")

        assert loaded == test_data

    def test_cache_key_generates_filename(self, tmp_path):
        """Test that cache key generates proper filename."""
        cache = DataCache(cache_dir=tmp_path)
        filename = cache._get_cache_path("bitcoin_market")

        assert filename.suffix == ".json"
        assert "bitcoin_market" in str(filename)

    def test_cache_expiry(self, tmp_path):
        """Test that expired cache returns None."""
        cache = DataCache(cache_dir=tmp_path, expire_hours=1)
        test_data = {"key": "value"}

        # Save data
        cache.save("test_key", test_data)

        # Modify file time to simulate expiry
        cache_path = cache._get_cache_path("test_key")
        old_time = datetime.now() - timedelta(hours=2)
        os.utime(cache_path, (old_time.timestamp(), old_time.timestamp()))

        # Should return None for expired cache
        loaded = cache.load("test_key")
        assert loaded is None

    def test_cache_not_expired(self, tmp_path):
        """Test that fresh cache returns data."""
        cache = DataCache(cache_dir=tmp_path, expire_hours=24)
        test_data = {"key": "value"}

        cache.save("test_key", test_data)
        loaded = cache.load("test_key")

        assert loaded == test_data

    def test_clear_cache(self, tmp_path):
        """Test clearing cache."""
        cache = DataCache(cache_dir=tmp_path)
        cache.save("key1", {"a": 1})
        cache.save("key2", {"b": 2})

        cache.clear()

        assert cache.load("key1") is None
        assert cache.load("key2") is None

    def test_cache_missing_file(self, tmp_path):
        """Test loading non-existent cache returns None."""
        cache = DataCache(cache_dir=tmp_path)
        loaded = cache.load("nonexistent")
        assert loaded is None