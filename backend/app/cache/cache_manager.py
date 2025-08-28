"""
Cache manager for intelligent caching of API 579 calculations and data.

Implements cache strategies optimized for safety-critical mechanical integrity system.
"""
import hashlib
import json
from datetime import timedelta
from typing import Any, Dict, Optional, Callable, TypeVar
from functools import wraps
import logging

from app.cache.redis_client import get_redis
from app.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Cache TTL configurations for different data types
CACHE_TTL_CONFIG = {
    "material_properties": timedelta(days=7),      # Materials don't change often
    "api579_calculations": timedelta(hours=24),     # Calculations can be cached for a day
    "equipment_data": timedelta(hours=4),           # Equipment data changes moderately  
    "inspection_summaries": timedelta(hours=1),     # Inspection data changes frequently
    "user_sessions": timedelta(minutes=30),         # User session data
    "health_checks": timedelta(minutes=5),          # Health check results
    "document_analysis": timedelta(days=1),         # Document analysis results
}


class CacheManager:
    """
    Intelligent cache manager for mechanical integrity system.
    """
    
    def __init__(self):
        self.prefix = "mechanical_integrity"
    
    def _generate_cache_key(self, namespace: str, *args, **kwargs) -> str:
        """
        Generate a deterministic cache key from function arguments.
        
        Args:
            namespace: Cache namespace (e.g., 'api579', 'materials')
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Create a deterministic representation of arguments
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items()) if kwargs else {}
        }
        
        # Create hash of arguments for consistent key generation
        key_string = json.dumps(key_data, default=str, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{self.prefix}:{namespace}:{key_hash}"
    
    async def get(self, namespace: str, *args, **kwargs) -> Optional[Any]:
        """Get cached value by namespace and arguments."""
        cache_key = self._generate_cache_key(namespace, *args, **kwargs)
        
        try:
            redis = await get_redis()
            value = await redis.get(cache_key)
            
            if value is not None:
                logger.debug(f"Cache HIT for key: {cache_key}")
                # Record cache hit metric
                MetricsCollector.record_cache_operation("hit", namespace)
                return value
            else:
                logger.debug(f"Cache MISS for key: {cache_key}")
                MetricsCollector.record_cache_operation("miss", namespace)
                return None
                
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            MetricsCollector.record_cache_operation("error", namespace)
            return None
    
    async def set(
        self, 
        namespace: str, 
        value: Any, 
        ttl: Optional[timedelta] = None,
        *args, 
        **kwargs
    ) -> bool:
        """Set cached value with optional TTL."""
        cache_key = self._generate_cache_key(namespace, *args, **kwargs)
        
        # Use default TTL if not specified
        if ttl is None:
            ttl = CACHE_TTL_CONFIG.get(namespace, timedelta(hours=1))
        
        try:
            redis = await get_redis()
            success = await redis.set(cache_key, value, ttl=ttl)
            
            if success:
                logger.debug(f"Cache SET for key: {cache_key} (TTL: {ttl})")
                MetricsCollector.record_cache_operation("set", namespace)
            else:
                MetricsCollector.record_cache_operation("error", namespace)
            
            return success
            
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            MetricsCollector.record_cache_operation("error", namespace)
            return False
    
    async def delete(self, namespace: str, *args, **kwargs) -> bool:
        """Delete cached value."""
        cache_key = self._generate_cache_key(namespace, *args, **kwargs)
        
        try:
            redis = await get_redis()
            deleted = await redis.delete(cache_key)
            
            if deleted:
                logger.debug(f"Cache DELETE for key: {cache_key}")
                MetricsCollector.record_cache_operation("delete", namespace)
            
            return bool(deleted)
            
        except Exception as e:
            logger.error(f"Cache DELETE error: {e}")
            MetricsCollector.record_cache_operation("error", namespace)
            return False
    
    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all cache entries for a namespace."""
        pattern = f"{self.prefix}:{namespace}:*"
        
        try:
            redis = await get_redis()
            keys = await redis.keys(pattern)
            
            if keys:
                deleted = await redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries for namespace: {namespace}")
                MetricsCollector.record_cache_operation("invalidate", namespace, count=deleted)
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache invalidation error for namespace '{namespace}': {e}")
            return 0


# Global cache manager instance
cache_manager = CacheManager()


def cached(
    namespace: str,
    ttl: Optional[timedelta] = None,
    serialize_method: str = "json"
):
    """
    Decorator for caching function results.
    
    Args:
        namespace: Cache namespace
        ttl: Time to live for cached result
        serialize_method: Serialization method ('json' or 'pickle')
        
    Returns:
        Decorated function with caching
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Try to get from cache first
            cached_result = await cache_manager.get(namespace, *args, **kwargs)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache the result
            await cache_manager.set(namespace, result, ttl, *args, **kwargs)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For synchronous functions, we need to run in async context
            # This is a simplified approach - in production, consider using asyncio.run()
            # or ensuring all cached functions are async
            result = func(*args, **kwargs)
            
            # Note: Sync caching would need different implementation
            # For now, we'll skip caching for sync functions
            logger.warning(f"Sync function {func.__name__} not cached - use async version")
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Specialized caching functions for common use cases

async def cache_material_properties(material: str, temperature: float, properties: Dict[str, Any]):
    """Cache material properties for fast lookup."""
    await cache_manager.set(
        "material_properties", 
        properties,
        material=material, 
        temperature=temperature
    )


async def get_cached_material_properties(material: str, temperature: float) -> Optional[Dict[str, Any]]:
    """Get cached material properties."""
    return await cache_manager.get(
        "material_properties",
        material=material, 
        temperature=temperature
    )


async def cache_api579_calculation(
    calc_type: str,
    equipment_id: str, 
    inputs: Dict[str, Any],
    result: Dict[str, Any]
):
    """Cache API 579 calculation results."""
    await cache_manager.set(
        "api579_calculations",
        result,
        calc_type=calc_type,
        equipment_id=equipment_id,
        inputs_hash=hashlib.md5(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    )


async def get_cached_api579_calculation(
    calc_type: str,
    equipment_id: str,
    inputs: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Get cached API 579 calculation results."""
    return await cache_manager.get(
        "api579_calculations",
        calc_type=calc_type,
        equipment_id=equipment_id,
        inputs_hash=hashlib.md5(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    )


async def invalidate_equipment_cache(equipment_id: str):
    """Invalidate all cache entries related to specific equipment."""
    # Invalidate API 579 calculations
    await cache_manager.invalidate_namespace("api579_calculations")
    
    # Invalidate equipment data
    await cache_manager.invalidate_namespace("equipment_data")
    
    logger.info(f"Invalidated cache for equipment: {equipment_id}")


async def warm_material_cache():
    """Warm up material properties cache with common materials and temperatures."""
    from models.material_properties import ASMEMaterialDatabase
    
    common_materials = ["SA-516-70", "SA-106-B", "SA-335-P11", "SA-240-304", "SA-240-316"]
    common_temperatures = [70, 200, 400, 600, 800]  # Fahrenheit
    
    logger.info("Warming material properties cache...")
    
    for material in common_materials:
        for temp in common_temperatures:
            try:
                # Get material properties (this will cache them)
                properties, metadata = ASMEMaterialDatabase.get_allowable_stress(
                    material, temp
                )
                
                await cache_material_properties(
                    material, 
                    temp, 
                    {"stress": float(properties), "metadata": metadata}
                )
                
            except Exception as e:
                logger.warning(f"Failed to cache material {material} at {temp}°F: {e}")
    
    logger.info("Material cache warming completed")


# Export commonly used functions
__all__ = [
    'CacheManager',
    'cache_manager', 
    'cached',
    'cache_material_properties',
    'get_cached_material_properties',
    'cache_api579_calculation',
    'get_cached_api579_calculation',
    'invalidate_equipment_cache',
    'warm_material_cache',
]