from __future__ import annotations

import time
from datetime import timedelta

"""
Provides high-performance distributed caching mechanics using Redis.
Designed primarily for state-tracking, such as alert deduplication,
to prevent alert fatigue in high-volume, multi-node environments.
"""


class RedisAlertCache:
    """
    Distributed locking/caching mechanism for alerting signals.
    Includes an in-memory fallback strategy if Redis is unreachable.
    """

    def __init__(self, redis_url: str) -> None:
        """
        Initializes the cache layer.
        
        Args:
            redis_url (str): The connection string (e.g., redis://localhost:6379/0).
        """
        self.redis_url = redis_url
        self._memory: dict[str, float] = {}
        self._redis_client = None

    def _client(self):
        """
        Singleton-pattern lazy loader for the Redis connection pool.
        """
        if self._redis_client is not None:
            return self._redis_client
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis package is required for Redis integration") from exc
        self._redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis_client

    def has_alert(self, key: str) -> bool:
        """
        Verifies if a specific alert has already been fired within the deduplication window.
        Fails open to an in-memory dict if Redis experiences a transient failure.
        
        Args:
            key (str): The unique identifier for the anomaly.
            
        Returns:
            bool: True if the alert exists (do not refire), False otherwise.
        """
        try:
            return bool(self._client().exists(key))
        except Exception:
            expiry = self._memory.get(key)
            if expiry is not None and time.time() < expiry:
                return True
            if expiry is not None:
                del self._memory[key]
            return False

    def set_alert(self, key: str, ttl: timedelta) -> None:
        """
        Records the occurrence of an alert into the cache, securing the deduplication lock.
        
        Args:
            key (str): The unique identifier.
            ttl (timedelta): The duration for which the lock remains valid.
        """
        try:
            self._client().set(name=key, value="1", ex=int(ttl.total_seconds()))
        except Exception:
            self._memory[key] = time.time() + ttl.total_seconds()
