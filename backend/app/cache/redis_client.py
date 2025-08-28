"""
Redis client configuration and connection management.
"""
import json
import pickle
from typing import Any, Optional, Union, Dict
from datetime import timedelta
import logging

import redis.asyncio as redis
from redis.asyncio import Redis

from core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client with connection pooling and error handling.
    """
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Initialize Redis connection with connection pooling."""
        try:
            # TODO: [CACHE_OPTIMIZATION] Implement intelligent cache warming for material properties
            # Gap: Cold cache on startup causes delays for first API 579 calculations
            # Implementation: Pre-load ASME material database on service startup
            # Performance impact: First calculation 2-5s delay -> <100ms response
            
            # TODO: [CACHE_STRATEGY] Add cache TTL based on data criticality
            # Current: Generic expiry for all cached data
            # Need: Equipment specs (24h), material properties (7d), calculations (1h)
            # Safety: Never cache safety-critical calculation results longer than 1 hour
            
            self._connection_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )
            
            self._redis = Redis(
                connection_pool=self._connection_pool,
                decode_responses=False,  # Handle encoding manually for flexibility
            )
            
            # Test connection
            await self._redis.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._redis = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._redis is not None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[Union[int, timedelta]] = None,
        serialize_method: str = "json"
    ) -> bool:
        """
        Set a value in Redis with optional TTL.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live (seconds or timedelta)
            serialize_method: Serialization method ('json' or 'pickle')
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            # Serialize value
            if serialize_method == "json":
                serialized_value = json.dumps(value, default=str)
            elif serialize_method == "pickle":
                serialized_value = pickle.dumps(value)
            else:
                raise ValueError(f"Unsupported serialization method: {serialize_method}")
            
            # Set value with TTL
            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                await self._redis.setex(key, ttl, serialized_value)
            else:
                await self._redis.set(key, serialized_value)
            
            return True
            
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False
    
    async def get(
        self, 
        key: str, 
        serialize_method: str = "json"
    ) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: Cache key
            serialize_method: Deserialization method ('json' or 'pickle')
            
        Returns:
            Cached value or None if not found
        """
        if not self.is_connected:
            return None
        
        try:
            value = await self._redis.get(key)
            if value is None:
                return None
            
            # Deserialize value
            if serialize_method == "json":
                return json.loads(value)
            elif serialize_method == "pickle":
                return pickle.loads(value)
            else:
                raise ValueError(f"Unsupported serialization method: {serialize_method}")
            
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None
    
    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from Redis.
        
        Args:
            keys: Keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not self.is_connected or not keys:
            return 0
        
        try:
            return await self._redis.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self.is_connected:
            return False
        
        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False
    
    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Set TTL for an existing key."""
        if not self.is_connected:
            return False
        
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            return bool(await self._redis.expire(key, ttl))
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get TTL for a key (-1 if no TTL, -2 if key doesn't exist)."""
        if not self.is_connected:
            return -2
        
        try:
            return await self._redis.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return -2
    
    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern."""
        if not self.is_connected:
            return []
        
        try:
            keys = await self._redis.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Redis KEYS error for pattern '{pattern}': {e}")
            return []
    
    async def flushdb(self) -> bool:
        """Flush current database (use with caution!)."""
        if not self.is_connected:
            return False
        
        try:
            await self._redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False
    
    async def info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        if not self.is_connected:
            return {}
        
        try:
            info = await self._redis.info()
            return info
        except Exception as e:
            logger.error(f"Redis INFO error: {e}")
            return {}
    
    async def pipeline(self):
        """Create Redis pipeline for batch operations."""
        if not self.is_connected:
            return None
        
        return self._redis.pipeline()


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Get Redis client instance."""
    if not redis_client.is_connected:
        await redis_client.connect()
    return redis_client


async def close_redis():
    """Close Redis connection."""
    await redis_client.disconnect()