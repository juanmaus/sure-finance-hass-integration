"""Cache management (integration copy)."""

import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, cache_dir: Optional[Union[str, Path]] = None, redis_url: Optional[str] = None,
                 default_ttl: int = 3600):
        # Ensure cache_dir is always a Path object, regardless of input type
        if cache_dir is None:
            self.cache_dir = Path(".cache")
        elif isinstance(cache_dir, str):
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.redis_url = redis_url
        self._redis: Optional[Redis] = None
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    async def connect_redis(self):
        if self.redis_url and not self._redis:
            try:
                self._redis = Redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
                try:
                    await self._redis.ping()
                except Exception:
                    pass
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self._redis = None

    async def close(self):
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _get_cache_key(self, key: str, namespace: str = "default") -> str:
        return f"sure_finance:{namespace}:{key}"

    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        full_key = self._get_cache_key(key, namespace)
        if full_key in self._memory_cache:
            entry = self._memory_cache[full_key]
            if datetime.utcnow() < entry["expires_at"]:
                return entry["value"]
            else:
                del self._memory_cache[full_key]
        if self._redis:
            try:
                value = await self._redis.get(full_key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        cache_file = self.cache_dir / f"{full_key}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                    if datetime.utcnow() < data["expires_at"]:
                        return data["value"]
                    else:
                        cache_file.unlink()
            except Exception as e:
                logger.error(f"File cache read error: {e}")
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "default"):
        full_key = self._get_cache_key(key, namespace)
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        self._memory_cache[full_key] = {"value": value, "expires_at": expires_at}
        if self._redis:
            try:
                await self._redis.setex(full_key, ttl, json.dumps(value, default=str))
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        try:
            cache_file = self.cache_dir / f"{full_key}.cache"
            with open(cache_file, "wb") as f:
                pickle.dump({"value": value, "expires_at": expires_at}, f)
        except Exception as e:
            logger.error(f"File cache write error: {e}")

    async def delete(self, key: str, namespace: str = "default"):
        full_key = self._get_cache_key(key, namespace)
        self._memory_cache.pop(full_key, None)
        if self._redis:
            try:
                await self._redis.delete(full_key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        cache_file = self.cache_dir / f"{full_key}.cache"
        if cache_file.exists():
            try:
                cache_file.unlink()
            except Exception as e:
                logger.error(f"File cache delete error: {e}")

    async def clear_namespace(self, namespace: str):
        prefix = f"sure_finance:{namespace}:"
        keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._memory_cache[key]
        if self._redis:
            try:
                async for key in self._redis.scan_iter(match=f"{prefix}*"):
                    await self._redis.delete(key)
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        for cache_file in self.cache_dir.glob(f"{prefix}*.cache"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.error(f"File cache clear error: {e}")

    async def get_or_set(self, key: str, factory, ttl: Optional[int] = None, namespace: str = "default") -> Any:
        value = await self.get(key, namespace)
        if value is not None:
            return value
        value = await factory()
        await self.set(key, value, ttl, namespace)
        return value

    def cleanup_expired(self):
        now = datetime.utcnow()
        expired_keys = [k for k, v in self._memory_cache.items() if now >= v["expires_at"]]
        for key in expired_keys:
            del self._memory_cache[key]
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                    if now >= data["expires_at"]:
                        cache_file.unlink()
            except Exception:
                try:
                    cache_file.unlink()
                except Exception:
                    pass
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def account_key(self, account_id: Optional[str] = None) -> str:
        if account_id:
            return f"account:{account_id}"
        return "accounts:all"

    def transaction_key(self, account_id: Optional[str] = None, page: Optional[int] = None) -> str:
        parts = ["transactions"]
        if account_id:
            parts.append(f"account:{account_id}")
        if page:
            parts.append(f"page:{page}")
        return ":".join(parts)

    def summary_key(self, period: Optional[str] = None) -> str:
        if period:
            return f"summary:{period}"
        return "summary:current"

    def cashflow_key(self, year: int, month: int) -> str:
        return f"cashflow:{year:04d}-{month:02d}"
