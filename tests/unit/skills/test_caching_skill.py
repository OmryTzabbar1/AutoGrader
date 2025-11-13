"""
Unit tests for CachingSkill.
"""

import pytest
from pathlib import Path
import time
import json

from skills.caching_skill import CachingSkill


@pytest.fixture
def cache_dir(tmp_path):
    """Create temporary cache directory."""
    return tmp_path / "cache"


@pytest.fixture
def caching_skill(cache_dir):
    """Create CachingSkill instance."""
    return CachingSkill(cache_dir=cache_dir, ttl_seconds=3600)


class TestCachingSkill:
    """Test suite for CachingSkill."""

    def test_set_and_get(self, caching_skill, tmp_path):
        """Test basic set and get operations."""
        key = tmp_path / "test_key.txt"
        data = {"test": "data", "value": 123}

        # Set cache
        caching_skill.set(key, data)

        # Get cache
        cached = caching_skill.get(key)

        assert cached == data

    def test_get_nonexistent_returns_none(self, caching_skill, tmp_path):
        """Test getting nonexistent key returns None."""
        key = tmp_path / "nonexistent.txt"

        result = caching_skill.get(key)

        assert result is None

    def test_ttl_expiration(self, cache_dir, tmp_path):
        """Test cache expiration with TTL."""
        # Create cache with 1 second TTL
        short_ttl_cache = CachingSkill(cache_dir=cache_dir, ttl_seconds=1)

        key = tmp_path / "expiring_key.txt"
        data = {"expires": "soon"}

        # Set cache
        short_ttl_cache.set(key, data)

        # Should be available immediately
        assert short_ttl_cache.get(key) == data

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert short_ttl_cache.get(key) is None

    def test_cache_key_generation(self, caching_skill, tmp_path):
        """Test cache key generation is consistent."""
        key1 = tmp_path / "file.txt"
        key2 = tmp_path / "file.txt"  # Same path

        # Set with first key
        caching_skill.set(key1, {"data": 1})

        # Get with second key (same path)
        cached = caching_skill.get(key2)

        assert cached == {"data": 1}

    def test_different_keys_different_cache(self, caching_skill, tmp_path):
        """Test different keys have different cache entries."""
        key1 = tmp_path / "file1.txt"
        key2 = tmp_path / "file2.txt"

        data1 = {"file": 1}
        data2 = {"file": 2}

        # Set different data for different keys
        caching_skill.set(key1, data1)
        caching_skill.set(key2, data2)

        # Verify separation
        assert caching_skill.get(key1) == data1
        assert caching_skill.get(key2) == data2

    def test_clear_single_key(self, caching_skill, tmp_path):
        """Test clearing single cache entry."""
        key = tmp_path / "clear_me.txt"
        data = {"will": "clear"}

        # Set and verify
        caching_skill.set(key, data)
        assert caching_skill.get(key) == data

        # Clear
        caching_skill.clear(key)

        # Should be gone
        assert caching_skill.get(key) is None

    def test_cache_directory_creation(self, tmp_path):
        """Test cache directory is created if it doesn't exist."""
        cache_dir = tmp_path / "new_cache"
        cache = CachingSkill(cache_dir=cache_dir)

        key = tmp_path / "test.txt"
        cache.set(key, {"test": "data"})

        # Cache directory should exist
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_complex_data_structures(self, caching_skill, tmp_path):
        """Test caching complex nested data structures."""
        key = tmp_path / "complex.txt"
        data = {
            "nested": {
                "list": [1, 2, 3],
                "dict": {"a": "b"},
                "null": None,
                "bool": True
            },
            "array": [{"id": 1}, {"id": 2}]
        }

        caching_skill.set(key, data)
        cached = caching_skill.get(key)

        assert cached == data

    def test_cache_metadata_stored(self, caching_skill, cache_dir, tmp_path):
        """Test cache metadata is stored correctly."""
        key = tmp_path / "metadata_test.txt"
        data = {"test": "data"}

        caching_skill.set(key, data)

        # Check cache file exists
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) > 0

        # Check metadata in cache file
        cache_file = cache_files[0]
        with open(cache_file, 'r') as f:
            cache_content = json.load(f)

        assert "timestamp" in cache_content
        assert "data" in cache_content
        assert cache_content["data"] == data

    def test_multiple_cache_instances_share_data(self, cache_dir, tmp_path):
        """Test multiple cache instances with same dir share data."""
        cache1 = CachingSkill(cache_dir=cache_dir)
        cache2 = CachingSkill(cache_dir=cache_dir)

        key = tmp_path / "shared.txt"
        data = {"shared": True}

        # Set with cache1
        cache1.set(key, data)

        # Get with cache2
        cached = cache2.get(key)

        assert cached == data
