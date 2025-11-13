"""
Caching skill for storing and retrieving parsed documents and LLM responses.

This skill provides file-based caching with TTL support and hash-based keys.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Any, Optional
import logging


class CachingSkill:
    """
    Skill for caching data with TTL support.

    Uses file-based storage with content hashing for cache keys.
    Useful for caching parsed PDFs and LLM responses.

    Example:
        >>> cache = CachingSkill(cache_dir=".cache")
        >>> cache.set(Path("doc.pdf"), parsed_doc)
        >>> cached = cache.get(Path("doc.pdf"))
    """

    def __init__(
        self,
        cache_dir: Path = Path(".cache"),
        ttl_seconds: int = 86400  # 24 hours
    ):
        """
        Initialize the caching skill.

        Args:
            cache_dir: Directory for cache files
            ttl_seconds: Time-to-live for cache entries (default: 24 hours)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds
        self.logger = logging.getLogger(self.__class__.__name__)

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: Path) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key (usually file path)

        Returns:
            Cached value or None if not found/expired
        """
        cache_key = self._generate_cache_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            self.logger.debug(f"Cache miss: {key}")
            return None

        try:
            # Read cache entry
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)

            # Check TTL
            if self.ttl_seconds > 0:
                cache_time = cache_entry.get('timestamp', 0)
                age = time.time() - cache_time

                if age > self.ttl_seconds:
                    self.logger.debug(f"Cache expired: {key} (age: {age:.0f}s)")
                    cache_file.unlink()  # Delete expired cache
                    return None

            self.logger.debug(f"Cache hit: {key}")
            return cache_entry.get('data')

        except Exception as e:
            self.logger.warning(f"Failed to read cache for {key}: {e}")
            return None

    def set(self, key: Path, value: Any) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key (usually file path)
            value: Value to cache (must be JSON-serializable)
        """
        cache_key = self._generate_cache_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            cache_entry = {
                'key': str(key),
                'timestamp': time.time(),
                'data': value
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, default=str)

            self.logger.debug(f"Cached: {key}")

        except Exception as e:
            self.logger.warning(f"Failed to cache {key}: {e}")

    def delete(self, key: Path) -> bool:
        """
        Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        cache_key = self._generate_cache_key(key)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            cache_file.unlink()
            self.logger.debug(f"Deleted cache: {key}")
            return True

        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1

        self.logger.info(f"Cleared {count} cache entries")
        return count

    def clear_expired(self) -> int:
        """
        Clear expired cache entries.

        Returns:
            Number of expired entries deleted
        """
        count = 0
        current_time = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)

                cache_time = cache_entry.get('timestamp', 0)
                age = current_time - cache_time

                if age > self.ttl_seconds:
                    cache_file.unlink()
                    count += 1

            except Exception as e:
                self.logger.warning(f"Failed to check {cache_file}: {e}")
                # Delete corrupted cache files
                cache_file.unlink()
                count += 1

        self.logger.info(f"Cleared {count} expired cache entries")
        return count

    def _generate_cache_key(self, key: Path) -> str:
        """
        Generate cache key from file path.

        Uses combination of file path and modification time for uniqueness.

        Args:
            key: Original key (file path)

        Returns:
            Hash string for cache key
        """
        # Include file path and mtime (if file exists)
        key_str = str(key.absolute())

        if key.exists():
            mtime = key.stat().st_mtime
            key_str += f"_{mtime}"

        # Generate SHA256 hash
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_entries = len(cache_files)

        expired_entries = 0
        total_size = 0
        current_time = time.time()

        for cache_file in cache_files:
            total_size += cache_file.stat().st_size

            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)

                cache_time = cache_entry.get('timestamp', 0)
                age = current_time - cache_time

                if age > self.ttl_seconds:
                    expired_entries += 1

            except Exception:
                expired_entries += 1

        return {
            'total_entries': total_entries,
            'expired_entries': expired_entries,
            'valid_entries': total_entries - expired_entries,
            'total_size_mb': total_size / 1024 / 1024,
            'cache_dir': str(self.cache_dir)
        }
