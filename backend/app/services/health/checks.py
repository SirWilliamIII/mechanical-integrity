"""
Health check implementation for critical services.

Handles verification of PostgreSQL, Redis, and Ollama services
with detailed status reporting for compliance requirements.
"""
import asyncio
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import asyncpg
import redis.asyncio as redis
import httpx

from core.config import settings
import logging

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """Individual service health details."""
    name: str
    status: ServiceStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "status": self.status.value,
            "message": self.message
        }
        if self.details:
            result["details"] = self.details
        if self.response_time_ms is not None:
            result["response_time_ms"] = round(self.response_time_ms, 2)
        return result


class HealthChecker:
    """
    Comprehensive health checker for all critical services.
    
    Performs detailed checks on:
    - PostgreSQL database connectivity and schema
    - Redis cache availability
    - Ollama LLM service status
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(timeout=5.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()
        if self.redis_client:
            # Use aclose() for proper async Redis client cleanup (Redis 5.0.1+)
            await self.redis_client.aclose()
    
    async def check_all_services(self) -> Dict[str, Any]:
        """
        Run all health checks and return comprehensive status.
        
        Returns:
            Dict with overall status and individual service statuses
        """
        start_time = datetime.utcnow()
        
        # Run all checks concurrently
        results = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_ollama(),
            return_exceptions=True
        )
        
        # Process results
        services = {}
        checks_passed = 0
        checks_total = len(results)
        overall_status = ServiceStatus.HEALTHY
        
        for result in results:
            if isinstance(result, Exception):
                # Handle any unexpected errors
                service_name = "unknown"
                health = ServiceHealth(
                    name=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message=f"Check failed: {str(result)}"
                )
            else:
                health = result
            
            services[health.name] = health.to_dict()
            
            if health.status == ServiceStatus.HEALTHY:
                checks_passed += 1
            elif health.status == ServiceStatus.DEGRADED and overall_status == ServiceStatus.HEALTHY:
                overall_status = ServiceStatus.DEGRADED
            elif health.status == ServiceStatus.UNHEALTHY:
                overall_status = ServiceStatus.UNHEALTHY
        
        # Calculate total response time
        total_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "status": overall_status.value,
            "timestamp": start_time.isoformat(),
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
            "services": services,
            "checks_passed": checks_passed,
            "checks_total": checks_total,
            "total_response_time_ms": round(total_time_ms, 2)
        }
    
    async def check_database(self) -> ServiceHealth:
        """
        Check PostgreSQL database connectivity and schema.
        
        Validates:
        - Connection establishment
        - Query execution
        - Schema presence (equipment table)
        """
        start = datetime.utcnow()
        
        try:
            # Test direct connection with asyncpg
            conn = await asyncpg.connect(
                host=settings.POSTGRES_SERVER,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                timeout=5.0
            )
            
            # Verify we can query
            version = await conn.fetchval("SELECT version()")
            
            # Check for critical tables in the mechanical integrity schema
            table_count = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('equipment', 'inspection_records', 'thickness_readings', 'api579_calculations')
            """)
            
            await conn.close()
            
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            if table_count >= 4:
                return ServiceHealth(
                    name="postgresql",
                    status=ServiceStatus.HEALTHY,
                    message="Database connected and schema verified",
                    details={
                        "version": version.split()[0] + " " + version.split()[1],
                        "tables_found": int(table_count)
                    },
                    response_time_ms=response_time
                )
            else:
                return ServiceHealth(
                    name="postgresql",
                    status=ServiceStatus.DEGRADED,
                    message="Database connected but schema incomplete",
                    details={
                        "tables_found": int(table_count),
                        "required_tables": [
                            "equipment", 
                            "inspection_records", 
                            "thickness_readings", 
                            "api579_calculations"
                        ],
                        "expected_total": 4
                    },
                    response_time_ms=response_time
                )
                
        except asyncpg.exceptions.PostgresError as e:
            logger.error(f"PostgreSQL check failed: {e}")
            return ServiceHealth(
                name="postgresql",
                status=ServiceStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            return ServiceHealth(
                name="postgresql",
                status=ServiceStatus.UNHEALTHY,
                message=f"Connection failed: {str(e)}",
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )

    # TODO: [MONITORING] Add comprehensive monitoring and alerting system
    # - Integrate with Prometheus/Grafana for metrics collection and visualization
    # - Add custom metrics for safety-critical calculation performance and accuracy
    # - Implement automated alerting for RSF < 0.9 and remaining life < 2 years
    # - Add database query performance monitoring with slow query alerts
    # - Implement service degradation detection and automatic failover mechanisms
    
    async def check_redis(self) -> ServiceHealth:
        """
        Check Redis cache availability.
        
        Validates:
        - Connection establishment
        - Basic operations (ping/set/get)
        """
        start = datetime.utcnow()
        
        try:
            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
            
            # Test basic operations
            await self.redis_client.ping()
            
            # Test set/get
            test_key = "health_check_test"
            test_value = f"health_check_{datetime.utcnow().isoformat()}"
            await self.redis_client.set(test_key, test_value, ex=10)
            retrieved = await self.redis_client.get(test_key)
            
            # Get Redis info
            info = await self.redis_client.info()
            
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            if retrieved == test_value:
                return ServiceHealth(
                    name="redis",
                    status=ServiceStatus.HEALTHY,
                    message="Redis operational",
                    details={
                        "version": info.get("redis_version", "unknown"),
                        "used_memory_human": info.get("used_memory_human", "unknown"),
                        "connected_clients": info.get("connected_clients", 0)
                    },
                    response_time_ms=response_time
                )
            else:
                return ServiceHealth(
                    name="redis",
                    status=ServiceStatus.DEGRADED,
                    message="Redis connected but operations failing",
                    response_time_ms=response_time
                )
                
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            return ServiceHealth(
                name="redis",
                status=ServiceStatus.UNHEALTHY,
                message="Redis connection failed",
                details={"error": str(e)},
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )
        except Exception as e:
            logger.error(f"Unexpected Redis error: {e}")
            return ServiceHealth(
                name="redis",
                status=ServiceStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}",
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )
    
    async def check_ollama(self) -> ServiceHealth:
        """
        Check Ollama LLM service availability.
        
        Validates:
        - API endpoint accessibility
        - Model availability
        """
        start = datetime.utcnow()
        
        if not self.http_client:
            self.http_client = httpx.AsyncClient(timeout=5.0)
        
        try:
            # Check Ollama API
            response = await self.http_client.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags"
            )
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            # Check if our required model is available
            model_names = [m.get("name", "") for m in models]
            has_required_model = any(
                settings.OLLAMA_MODEL in name 
                for name in model_names
            )
            
            if models and has_required_model:
                return ServiceHealth(
                    name="ollama",
                    status=ServiceStatus.HEALTHY,
                    message="Ollama service operational with required model",
                    details={
                        "models_available": len(models),
                        "required_model": settings.OLLAMA_MODEL,
                        "model_found": has_required_model,
                        "available_models": model_names[:5]  # First 5 models
                    },
                    response_time_ms=response_time
                )
            elif models:
                return ServiceHealth(
                    name="ollama",
                    status=ServiceStatus.DEGRADED,
                    message=f"Ollama running but model '{settings.OLLAMA_MODEL}' not found",
                    details={
                        "models_available": len(models),
                        "required_model": settings.OLLAMA_MODEL,
                        "available_models": model_names[:5]
                    },
                    response_time_ms=response_time
                )
            else:
                return ServiceHealth(
                    name="ollama",
                    status=ServiceStatus.DEGRADED,
                    message="Ollama running but no models loaded",
                    response_time_ms=response_time
                )
                
        except httpx.ConnectError:
            logger.error("Ollama service not reachable")
            return ServiceHealth(
                name="ollama",
                status=ServiceStatus.UNHEALTHY,
                message="Ollama service not reachable",
                details={
                    "url": settings.OLLAMA_BASE_URL,
                    "hint": "Run 'ollama serve' in a separate terminal"
                },
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )
        except Exception as e:
            logger.error(f"Unexpected Ollama error: {e}")
            return ServiceHealth(
                name="ollama",
                status=ServiceStatus.UNHEALTHY,
                message=f"Ollama error: {str(e)}",
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )


# Convenience function for quick health checks
async def get_system_health() -> Dict[str, Any]:
    """
    Get complete system health status.
    
    Returns:
        Dictionary with health status of all services
    """
    async with HealthChecker() as checker:
        return await checker.check_all_services()
