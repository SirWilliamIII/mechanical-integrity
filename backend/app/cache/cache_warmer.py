"""
Cache warming service for mechanical integrity system.

Pre-loads frequently accessed data to improve performance:
- ASME material properties database
- Equipment specifications
- Common calculation parameters
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from decimal import Decimal

from app.cache.redis_client import get_redis
from app.calculations.constants import API579Constants, MATERIAL_PROPERTIES
from models.equipment import Equipment
from models.inspection import API579Calculation
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CacheWarmingService:
    """
    Service for warming up frequently accessed data in Redis cache.
    
    Improves performance by pre-loading:
    - Material properties for common steel grades
    - Equipment specifications for active equipment
    - Calculation parameters for recent assessments
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.redis = None
        
        # Cache TTL strategies based on data criticality
        self.MATERIAL_PROPERTIES_TTL = 7 * 24 * 3600  # 7 days - rarely change
        self.EQUIPMENT_SPECS_TTL = 24 * 3600          # 24 hours - may be updated
        self.CALCULATION_CACHE_TTL = 3600             # 1 hour - safety-critical, short TTL
        
        # Material properties that should be warmed up
        self.COMMON_MATERIALS = [
            'SA-516-70', 'SA-106-B', 'SA-333-6', 'SA-312-316L',
            'SA-240-316L', 'SA-105', 'SA-350-LF2', 'SA-537-1'
        ]

    async def initialize(self):
        """Initialize Redis connection for cache warming."""
        self.redis = await get_redis()
        if not self.redis:
            logger.error("Failed to connect to Redis for cache warming")
            return False
        
        logger.info("Cache warming service initialized")
        return True

    async def warm_all_caches(self) -> Dict[str, bool]:
        """
        Warm all cache types.
        
        Returns:
            Dictionary of cache warming results
        """
        if not self.redis:
            await self.initialize()
        
        results = {}
        
        try:
            # Warm material properties cache
            results['material_properties'] = await self._warm_material_properties()
            
            # Warm equipment specifications cache
            results['equipment_specs'] = await self._warm_equipment_specifications()
            
            # Warm calculation parameters cache
            results['calculation_params'] = await self._warm_calculation_parameters()
            
            # Warm pressure-temperature rating charts
            results['pt_ratings'] = await self._warm_pressure_temperature_ratings()
            
            logger.info(f"Cache warming completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error during cache warming: {e}")
            results['error'] = str(e)
            return results

    async def _warm_material_properties(self) -> bool:
        """Warm material properties cache for common steel grades."""
        try:
            constants = API579Constants()
            warmed_count = 0
            
            for material in self.COMMON_MATERIALS:
                for temp_f in range(70, 1001, 50):  # Common temperature range
                    cache_key = f"material:{material}:temp:{temp_f}"
                    
                    # Check if already cached
                    if await self.redis.exists(cache_key):
                        continue
                    
                    try:
                        # Get material properties
                        material_data = constants.get_material_properties(material, Decimal(str(temp_f)))
                        
                        if material_data:
                            # Cache the material properties
                            await self.redis.setex(
                                cache_key,
                                self.MATERIAL_PROPERTIES_TTL,
                                str(material_data)  # Convert to string for Redis storage
                            )
                            warmed_count += 1
                            
                    except Exception as e:
                        logger.warning(f"Failed to cache material {material} at {temp_f}°F: {e}")
                        continue
            
            logger.info(f"Warmed {warmed_count} material property entries")
            return True
            
        except Exception as e:
            logger.error(f"Error warming material properties cache: {e}")
            return False

    async def _warm_equipment_specifications(self) -> bool:
        """Warm equipment specifications cache for active equipment."""
        try:
            # Get equipment that has been inspected recently (likely to be accessed)
            recent_equipment = self.db.query(Equipment).filter(
                Equipment.last_inspection_date > datetime.utcnow() - timedelta(days=365)
            ).all()
            
            warmed_count = 0
            
            for equipment in recent_equipment:
                cache_key = f"equipment:specs:{equipment.id}"
                
                # Check if already cached
                if await self.redis.exists(cache_key):
                    continue
                
                # Prepare equipment specifications for caching
                equipment_specs = {
                    'id': str(equipment.id),
                    'tag_number': equipment.tag_number,
                    'design_pressure': float(equipment.design_pressure),
                    'design_temperature': float(equipment.design_temperature),
                    'design_thickness': float(equipment.design_thickness),
                    'material_specification': equipment.material_specification,
                    'corrosion_allowance': float(equipment.corrosion_allowance),
                    'equipment_type': equipment.equipment_type.value,
                    'criticality': equipment.criticality.value
                }
                
                # Cache equipment specifications
                import json
                await self.redis.setex(
                    cache_key,
                    self.EQUIPMENT_SPECS_TTL,
                    json.dumps(equipment_specs)
                )
                warmed_count += 1
            
            logger.info(f"Warmed {warmed_count} equipment specification entries")
            return True
            
        except Exception as e:
            logger.error(f"Error warming equipment specifications cache: {e}")
            return False

    async def _warm_calculation_parameters(self) -> bool:
        """Warm calculation parameters cache for recent assessments."""
        try:
            # Get calculation parameters from recent API 579 assessments
            recent_calculations = self.db.query(API579Calculation).filter(
                API579Calculation.created_at > datetime.utcnow() - timedelta(days=30)
            ).limit(100).all()
            
            warmed_count = 0
            
            for calc in recent_calculations:
                if calc.input_parameters:
                    # Extract common parameter combinations for caching
                    try:
                        import json
                        params = json.loads(calc.input_parameters) if isinstance(calc.input_parameters, str) else calc.input_parameters
                        
                        # Create cache keys for common parameter combinations
                        material = params.get('material_specification')
                        pressure = params.get('design_pressure')
                        temperature = params.get('design_temperature')
                        
                        if material and pressure and temperature:
                            cache_key = f"calc_params:{material}:{pressure}:{temperature}"
                            
                            if not await self.redis.exists(cache_key):
                                # Cache the calculation parameters
                                await self.redis.setex(
                                    cache_key,
                                    self.CALCULATION_CACHE_TTL,
                                    json.dumps(params)
                                )
                                warmed_count += 1
                    
                    except Exception as e:
                        logger.warning(f"Failed to cache calculation parameters: {e}")
                        continue
            
            logger.info(f"Warmed {warmed_count} calculation parameter entries")
            return True
            
        except Exception as e:
            logger.error(f"Error warming calculation parameters cache: {e}")
            return False

    async def _warm_pressure_temperature_ratings(self) -> bool:
        """Warm pressure-temperature rating charts for common materials."""
        try:
            warmed_count = 0
            
            # Common pressure ratings (ASME B16.5)
            pressure_ratings = [150, 300, 600, 900, 1500, 2500]
            
            for material in self.COMMON_MATERIALS:
                for rating in pressure_ratings:
                    cache_key = f"pt_rating:{material}:{rating}"
                    
                    if await self.redis.exists(cache_key):
                        continue
                    
                    # Generate pressure-temperature rating data
                    # This would normally come from ASME tables
                    pt_data = self._generate_pt_rating_data(material, rating)
                    
                    if pt_data:
                        import json
                        await self.redis.setex(
                            cache_key,
                            self.MATERIAL_PROPERTIES_TTL,
                            json.dumps(pt_data)
                        )
                        warmed_count += 1
            
            logger.info(f"Warmed {warmed_count} pressure-temperature rating entries")
            return True
            
        except Exception as e:
            logger.error(f"Error warming pressure-temperature ratings cache: {e}")
            return False

    def _generate_pt_rating_data(self, material: str, rating: int) -> Dict[str, Any]:
        """Generate pressure-temperature rating data for caching."""
        # Simplified PT rating generation
        # In production, this would reference ASME B16.5 tables
        
        base_pressures = {
            150: 285,   # psi at 100°F for Class 150
            300: 570,   # psi at 100°F for Class 300
            600: 1140,  # psi at 100°F for Class 600
            900: 1710,  # psi at 100°F for Class 900
            1500: 2850, # psi at 100°F for Class 1500
            2500: 4750  # psi at 100°F for Class 2500
        }
        
        if rating not in base_pressures:
            return None
        
        base_pressure = base_pressures[rating]
        
        # Generate temperature derating factors (simplified)
        pt_ratings = []
        for temp_f in range(100, 1001, 50):
            # Simplified derating - in production use actual ASME tables
            if temp_f <= 200:
                factor = 1.0
            elif temp_f <= 400:
                factor = 0.95
            elif temp_f <= 600:
                factor = 0.85
            elif temp_f <= 800:
                factor = 0.70
            else:
                factor = 0.50
            
            allowable_pressure = base_pressure * factor
            pt_ratings.append({
                'temperature_f': temp_f,
                'allowable_pressure_psi': allowable_pressure
            })
        
        return {
            'material': material,
            'rating_class': rating,
            'pt_ratings': pt_ratings,
            'cached_at': datetime.utcnow().isoformat()
        }

    async def schedule_periodic_warming(self, interval_hours: int = 24):
        """Schedule periodic cache warming."""
        logger.info(f"Starting periodic cache warming every {interval_hours} hours")
        
        while True:
            try:
                await self.warm_all_caches()
                await asyncio.sleep(interval_hours * 3600)  # Convert to seconds
            except Exception as e:
                logger.error(f"Error in periodic cache warming: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry

    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        try:
            if not self.redis:
                return 0
            
            # Find keys matching pattern
            keys = await self.redis.keys(pattern)
            
            if keys:
                # Delete matching keys
                deleted = await self.redis.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health information."""
        try:
            if not self.redis:
                return {'error': 'Redis not connected'}
            
            info = await self.redis.info()
            
            # Count keys by pattern
            material_keys = len(await self.redis.keys("material:*"))
            equipment_keys = len(await self.redis.keys("equipment:*"))
            calc_keys = len(await self.redis.keys("calc_params:*"))
            pt_keys = len(await self.redis.keys("pt_rating:*"))
            
            return {
                'redis_info': {
                    'used_memory': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'keyspace_hits': info.get('keyspace_hits'),
                    'keyspace_misses': info.get('keyspace_misses'),
                },
                'cache_counts': {
                    'material_properties': material_keys,
                    'equipment_specs': equipment_keys,
                    'calculation_params': calc_keys,
                    'pt_ratings': pt_keys,
                    'total': material_keys + equipment_keys + calc_keys + pt_keys
                },
                'cache_hit_rate': info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'error': str(e)}