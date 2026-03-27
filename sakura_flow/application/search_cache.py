import time
from typing import Any, Dict, Optional


class SearchCache:
    def __init__(self, ttl: int = 300):
        self.cache = {}
        self.ttl = ttl

    def set(self, key: str, query: str, results: Dict[str, Any]):
        self.cache[key] = {
            "query": query,
            "results": results,
            "timestamp": time.time(),
        }

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self.cache.get(key)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > self.ttl:
            del self.cache[key]
            return None
        return entry
