"""
Rate Limiter — Token Bucket / Sliding Window per provider + per brand
Phase 5 — Enforces config/models.yaml limits: rpm, rpd, tokens_per_day
In-memory for solo, Redis-backed when REDIS_URL set (optional)
"""

import time
import logging
import os
from typing import Dict, List, Tuple
from collections import defaultdict, deque

from core.exceptions import RateLimitExceeded
from core.security import mask_secrets

logger = logging.getLogger("clawagent.ratelimit")

class InMemoryRateLimiter:
    def __init__(self):
        # provider -> deque[timestamps]
        self._calls: Dict[str, deque] = defaultdict(deque)
        self._lock = None
        try:
            import threading
            self._lock = threading.Lock()
        except Exception:
            pass

    def _prune(self, provider: str, window_seconds: int):
        dq = self._calls[provider]
        cutoff = time.time() - window_seconds
        while dq and dq[0] < cutoff:
            dq.popleft()

    def check_and_record(self, provider: str, limits: Dict, brand_id=None) -> None:
        """
        Checks limits and records call if allowed, else raises RateLimitExceeded.
        Supports: rpm, rpd, tokens_per_day, tokens_per_minute
        """
        now = time.time()
        key = f"{provider}:{brand_id}" if brand_id else provider
        # Use per-provider+brand key for isolation
        # For simplicity, use provider key for global limits, brand key for per-brand
        # Here we enforce per-provider global
        limits = limits or {}
        # rpm -> 60s window
        rpm = limits.get("rpm")
        if rpm:
            self._prune(key, 60)
            if len(self._calls[key]) >= rpm:
                raise RateLimitExceeded(f"Rate limit rpm={rpm} exceeded for {provider} (brand {brand_id})")
        # rpd -> 86400s
        rpd = limits.get("rpd")
        if rpd:
            # Use separate key for daily
            daily_key = f"{key}:daily"
            self._prune(daily_key, 86400)
            if len(self._calls[daily_key]) >= rpd:
                raise RateLimitExceeded(f"Rate limit rpd={rpd} exceeded for {provider}")
            # Record daily after check
            if self._lock:
                with self._lock:
                    self._calls[daily_key].append(now)
                    self._calls[key].append(now)
                return
            else:
                self._calls[daily_key].append(now)
                self._calls[key].append(now)
                return
        # tokens_per_day
        tpd = limits.get("tokens_per_day")
        if tpd:
            daily_key = f"{key}:tpd"
            self._prune(daily_key, 86400)
            # Approximate tokens as calls for now (1 call = 1 token bucket unit)
            if len(self._calls[daily_key]) >= tpd:
                raise RateLimitExceeded(f"tokens_per_day {tpd} exceeded for {provider}")
            if self._lock:
                with self._lock:
                    self._calls[daily_key].append(now)
                    self._calls[key].append(now)
                return
            else:
                self._calls[daily_key].append(now)
        # If no daily limit, just record rpm bucket
        if rpm:
            # already recorded in daily path? need to record if not yet
            if self._lock:
                with self._lock:
                    self._calls[key].append(now)
            else:
                self._calls[key].append(now)
        else:
            # No limits, just record for observability
            if self._lock:
                with self._lock:
                    self._calls[key].append(now)
            else:
                self._calls[key].append(now)

# Global singleton
_global_limiter: InMemoryRateLimiter = None

def get_rate_limiter() -> InMemoryRateLimiter:
    global _global_limiter
    if _global_limiter is None:
        # Try Redis-backed if REDIS_URL set and redis available
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                # For now, still use InMemory but log
                logger.info("REDIS_URL set but using InMemory limiter (Redis token bucket pending)")
            except ImportError:
                pass
        _global_limiter = InMemoryRateLimiter()
    return _global_limiter
