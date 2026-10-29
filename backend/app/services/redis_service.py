import os
import time
import json
from typing import Any, Optional

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class InMemoryFallbackRedis:
    """High-performance in-memory fallback for local dev & testing when Redis is absent."""
    def __init__(self):
        self.data: dict[str, Any] = {}
        self.lists: dict[str, list[str]] = {}
        self.expirations: dict[str, float] = {}

    def _cleanup_expired(self, key: str):
        if key in self.expirations and time.time() > self.expirations[key]:
            self.data.pop(key, None)
            self.lists.pop(key, None)
            self.expirations.pop(key, None)

    async def get(self, key: str) -> Optional[str]:
        self._cleanup_expired(key)
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self.data[key] = value
        if ex:
            self.expirations[key] = time.time() + ex
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.data or k in self.lists:
                self.data.pop(k, None)
                self.lists.pop(k, None)
                self.expirations.pop(k, None)
                count += 1
        return count

    async def rpush(self, key: str, *values: str) -> int:
        if key not in self.lists:
            self.lists[key] = []
        for v in values:
            self.lists[key].append(v)
        return len(self.lists[key])

    async def ltrim(self, key: str, start: int, stop: int) -> bool:
        if key in self.lists:
            l = self.lists[key]
            # Handle negative indices
            s = start if start >= 0 else max(0, len(l) + start)
            e = stop + 1 if stop >= 0 else max(0, len(l) + stop + 1)
            self.lists[key] = l[s:e]
        return True

    async def lrange(self, key: str, start: int, stop: int) -> list[str]:
        if key not in self.lists:
            return []
        l = self.lists[key]
        s = start if start >= 0 else max(0, len(l) + start)
        e = stop + 1 if stop >= 0 else max(0, len(l) + stop + 1)
        return l[s:e]

    async def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))

    async def lpush(self, key: str, *values: str) -> int:
        if key not in self.lists:
            self.lists[key] = []
        for v in values:
            self.lists[key].insert(0, v)
        return len(self.lists[key])

    async def rpop(self, key: str) -> Optional[str]:
        if key in self.lists and self.lists[key]:
            return self.lists[key].pop()
        return None

    async def incr(self, key: str) -> int:
        self._cleanup_expired(key)
        val = int(self.data.get(key, 0)) + 1
        self.data[key] = str(val)
        return val

    async def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = time.time() + seconds
        return True


class RedisService:
    def __init__(self):
        self.client = None
        self.fallback = InMemoryFallbackRedis()

    async def get_client(self):
        if self.client is None and aioredis:
            try:
                client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2.0)
                await client.ping()
                self.client = client
            except Exception:
                self.client = None
        return self.client if self.client else self.fallback

    # --------------------------------------------------------------------------
    # 1. Rate Limiting: Token Bucket / Sliding Window Counter
    # --------------------------------------------------------------------------
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """
        Enforces rate limiting per IP or User ID using sliding window counter.
        Returns: (is_allowed, remaining_requests, retry_after_seconds)
        """
        r = await self.get_client()
        current_minute = int(time.time() // window_seconds)
        key = f"bothost:ratelimit:{identifier}:{current_minute}"

        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds + 5)

        if count > limit:
            retry_after = window_seconds - int(time.time() % window_seconds)
            return False, 0, max(1, retry_after)

        return True, max(0, limit - count), 0

    # --------------------------------------------------------------------------
    # 2. Ring Buffer for Logs (Max 1000 lines per bot, strictly in Redis)
    # --------------------------------------------------------------------------
    async def append_bot_log(self, bot_id: str, log_line: str, max_lines: int = 1000):
        """Appends log line to bot's ring buffer and truncates to max_lines."""
        r = await self.get_client()
        key = f"bothost:logs:{bot_id}"
        await r.rpush(key, log_line)
        await r.ltrim(key, -max_lines, -1)

    async def get_bot_logs(self, bot_id: str, tail: int = 150) -> list[str]:
        """Reads the last N log lines from the ring buffer."""
        r = await self.get_client()
        key = f"bothost:logs:{bot_id}"
        return await r.lrange(key, -tail, -1)

    # --------------------------------------------------------------------------
    # 3. Cache Management (Short TTL, Invalidation on Write)
    # --------------------------------------------------------------------------
    async def cache_get(self, key: str) -> Optional[Any]:
        r = await self.get_client()
        val = await r.get(f"bothost:cache:{key}")
        if val:
            try:
                return json.loads(val)
            except Exception:
                return val
        return None

    async def cache_set(self, key: str, value: Any, ttl_seconds: int = 30):
        r = await self.get_client()
        val_str = json.dumps(value) if not isinstance(value, str) else value
        await r.set(f"bothost:cache:{key}", val_str, ex=ttl_seconds)

    async def cache_delete(self, key: str):
        r = await self.get_client()
        await r.delete(f"bothost:cache:{key}")

    # --------------------------------------------------------------------------
    # 4. Job Queue & Task Management
    # --------------------------------------------------------------------------
    async def push_job(self, job_dict: dict) -> str:
        r = await self.get_client()
        job_json = json.dumps(job_dict)
        await r.lpush("bothost:jobs:queue", job_json)
        # Store state
        job_id = job_dict["id"]
        await r.set(f"bothost:job:{job_id}", job_json, ex=86400)
        return job_id

    async def pop_job(self) -> Optional[dict]:
        r = await self.get_client()
        raw = await r.rpop("bothost:jobs:queue")
        if raw:
            return json.loads(raw)
        return None

    async def get_queue_depth(self) -> int:
        r = await self.get_client()
        return await r.llen("bothost:jobs:queue")

    async def update_job_status(self, job_id: str, status: str, progress: int, stage: str, result: Any = None, error: str = None):
        r = await self.get_client()
        state = {
            "id": job_id,
            "status": status,
            "progress_percent": progress,
            "stage_message": stage,
            "result": result,
            "error": error,
            "updated_at": time.time(),
        }
        await r.set(f"bothost:job:{job_id}", json.dumps(state), ex=86400)


redis_service = RedisService()
