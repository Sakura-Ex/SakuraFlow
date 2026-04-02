import time
from typing import Any, Dict, Optional


class SearchCache:
    def __init__(self, ttl: int = 300):
        """Create a simple in-memory search cache.

        Args:
            ttl: Cache lifetime in seconds.
        """
        self.cache = {}
        self.ttl = ttl

    def set(self, key: str, query: str, results: Dict[str, Any]):
        """Store a search result set.

        Args:
            key: Cache key.
            query: Serialized query string.
            results: Search result mapping.
        """
        self.cache[key] = {
            "query": query,
            "results": results,
            "timestamp": time.time(),
        }

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Return a cached entry if it is still valid.

        Args:
            key: Cache key.

        Returns:
            The cached entry dictionary, or None if missing or expired.
        """
        entry = self.cache.get(key)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > self.ttl:
            del self.cache[key]
            return None
        return entry
