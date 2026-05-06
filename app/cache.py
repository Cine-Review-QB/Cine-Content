from __future__ import annotations

import json
import os
from typing import Any

import redis

_redis_client: redis.Redis | None = None


def _build_redis_url(config: dict[str, Any] | None = None) -> str:
    if config:
        redis_url = config.get("REDIS_URL")
        if redis_url:
            return redis_url
        redis_host = config.get("REDIS_HOST") or "localhost"
        redis_port = int(config.get("REDIS_PORT") or 6379)
        redis_db = int(config.get("REDIS_DB") or 0)
    else:
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            return redis_url
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        redis_db = int(os.environ.get("REDIS_DB", "0"))

    return f"redis://{redis_host}:{redis_port}/{redis_db}"


def init_redis(config: dict[str, Any] | None = None) -> None:
    global _redis_client
    _redis_client = redis.Redis.from_url(
        _build_redis_url(config),
        decode_responses=True,
    )


def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        _redis_client.close()
        _redis_client = None


def get_redis_client() -> redis.Redis:
    if _redis_client is None:
        raise RuntimeError("Redis não inicializado.")
    return _redis_client


class RedisCache:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def get_json(self, key: str) -> Any | None:
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def setex_json(self, key: str, ttl: int, value: Any) -> None:
        self._client.setex(key, ttl, json.dumps(value))

    def delete(self, *keys: str) -> int:
        return int(self._client.delete(*keys))

    def zincrby(self, key: str, amount: float, member: str) -> float:
        return float(self._client.zincrby(key, amount, member))

    def zrevrange(
        self, key: str, start: int, stop: int, withscores: bool = False
    ) -> list:
        return self._client.zrevrange(key, start, stop, withscores=withscores)

    def expire(self, key: str, ttl: int) -> bool:
        return bool(self._client.expire(key, ttl))

    def publish(self, channel: str, message: Any) -> int:
        payload = json.dumps(message) if not isinstance(message, str) else message
        return int(self._client.publish(channel, payload))


def get_cache() -> RedisCache:
    return RedisCache(get_redis_client())