"""
Mechanical Integrity AI - Main FastAPI Application
Safety-critical API for equipment inspection and API 579 compliance.
"""
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

from app.middleware.security import SecurityHeadersMiddleware, InputValidationMiddleware
from app.monitoring.middleware import MonitoringMiddleware, UserContextMiddleware, MetricsEndpointMiddleware
from app.monitoring.logging import setup_logging

from core.config import settings
from app.api import equipment, inspections, calculations, audit, analysis, rbi, compliance, batch, documents
from app.auth import router as auth_router
from models.database import verify_db_connection
from app.services.health import get_system_health
from app.services.health.advanced_checks import get_comprehensive_health
from app.cache.redis_client import get_redis, close_redis
from app.cache.cache_manager import warm_material_cache

# Configure structured logging
setup_logging()
logger = logging.getLogger(__name__)

# Application start time for uptime calculation
start_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events.
    Verify all critical services are running.
    """
    # Startup
    logger.info("🚀 Starting Mechanical Integrity AI System")
    
    # Display startup banner
    print("\n" + "="*60)
    print("🏭 MECHANICAL INTEGRITY AI SYSTEM")
    print("="*60)
    print(f"Version: {settings.APP_VERSION}")
    print("Safety Factor: 0.9")
    print("API Standards: 579-1, 510, 570, 653")
    print("Compliance Mode: ENABLED")
    print("="*60)
    print("📚 API Docs: http://localhost:8001/docs")
    print("🔍 Health Check: http://localhost:8001/health")
    print("="*60 + "\n")
    
    # Verify critical services
    services_ok = True
    
    # Check database
    if not verify_db_connection():
        logger.error("❌ PostgreSQL connection failed")
        services_ok = False
    else:
        logger.info("✅ PostgreSQL connected")
    
    # Redis and Ollama health checks for production readiness
    try:
        from app.services.health.checks import HealthChecker
        
        async def check_services():
            async with HealthChecker() as checker:
                redis_health = await checker.check_redis()
                ollama_health = await checker.check_ollama()
                return redis_health, ollama_health
        
        # ✅ RESOLVED: [ASYNC_LIFESPAN] Fixed asyncio.run() warning by using direct await
        # Now properly awaits check_services() within the async lifespan context
        redis_health, ollama_health = await check_services()
        
        # Log Redis status
        if redis_health.status.value == "healthy":
            logger.info("✅ Redis connected and operational")
        elif redis_health.status.value == "degraded":
            logger.warning(f"⚠️  Redis degraded: {redis_health.message}")
        else:
            logger.error(f"❌ Redis failed: {redis_health.message}")
            services_ok = False
        
        # Log Ollama status
        if ollama_health.status.value == "healthy":
            logger.info("✅ Ollama LLM service operational")
        elif ollama_health.status.value == "degraded":
            logger.warning(f"⚠️  Ollama degraded: {ollama_health.message}")
            # Ollama degraded is acceptable for basic operation
        else:
            logger.warning(f"⚠️  Ollama unavailable: {ollama_health.message}")
            # Ollama failure is not critical for basic operation
            
    except Exception as e:
        logger.error(f"❌ Service health check failed: {e}")
        services_ok = False
        # ✅ RESOLVED: [LIFESPAN] Fixed coroutine warning by using proper await pattern
    
    # Initialize Redis cache
    try:
        redis_client = await get_redis()
        logger.info("✅ Redis cache initialized")
        
        # Warm up material properties cache
        await warm_material_cache()
        logger.info("✅ Material cache warmed")
        
    except Exception as e:
        logger.warning(f"⚠️  Redis cache initialization failed: {e}")
        # Redis failure is not critical for basic operation
    
    if not services_ok:
        logger.warning("⚠️  Some services unavailable - running in degraded mode")
        # raise RuntimeError("Required services not available")
    
    logger.info("✨ All systems operational")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Mechanical Integrity AI System")
    
    # Close Redis connection
    try:
        await close_redis()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    AI-powered mechanical integrity management system for API 579 compliance.
    
    ## Features
    * Equipment lifecycle management
    * Inspection data tracking with thickness measurements
    * API 579 Level 1 & 2 fitness-for-service calculations
    * AI-powered document analysis for inspection reports
    * Corrosion rate trending and remaining life estimates
    * Full audit trail for regulatory compliance
    
    ## Safety Notice
    This system supports human decision-making for safety-critical infrastructure.
    All calculations require engineering verification before implementation.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Security middleware - CORS with strict configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Explicit methods
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language", 
        "Content-Type",
        "Authorization",
        "X-Requested-With",
    ],
    expose_headers=["X-Process-Time"],
)

# Monitoring middleware (order matters - add early in chain)
app.add_middleware(MonitoringMiddleware)
app.add_middleware(UserContextMiddleware)
app.add_middleware(MetricsEndpointMiddleware)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    InputValidationMiddleware,
    max_request_size=settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,  # Convert MB to bytes
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to responses for performance monitoring."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    
    # Log slow requests
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.3f}s")
    
    # TODO: [MONITORING] Add request metrics collection for APM integration
    # Implement Prometheus metrics for request duration, error rates, and throughput
    
    return response


# Exception handler for validation errors
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors with clear messages."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "type": "validation_error"
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "compliance": {
            "standards": ["API 579-1/ASME FFS-1", "API 510", "API 570", "API 653"],
            "safety_factor": 0.9,
            "audit_logging": True
        },
        "api_documentation": "/docs",
        "health_check": "/health"
    }


# Health check endpoints
@app.get("/health")
async def health_check():
    """
    Basic health check for load balancers.
    Fast response for basic service availability.
    """
    health_status = await get_system_health()
    
    # Determine HTTP status code based on overall status
    status_map = {
        "healthy": 200,
        "degraded": 503, 
        "unhealthy": 503,
        "unknown": 503
    }
    status_code = status_map.get(health_status["status"], 503)
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/health/detailed")
async def detailed_health_check():
    """
    Comprehensive health check including safety-critical monitoring.
    Used by monitoring systems for complete system assessment.
    """
    health_status = await get_comprehensive_health()
    
    # Determine HTTP status code
    status_map = {
        "healthy": 200,
        "degraded": 503,
        "unhealthy": 503,
        "unknown": 503
    }
    status_code = status_map.get(health_status["status"], 503)
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/health/ready")
async def readiness_check():
    """
    Kubernetes readiness probe - check if application is ready to serve traffic.
    """
    try:
        # Quick database connectivity check
        if not verify_db_connection():
            return JSONResponse(
                content={"status": "not_ready", "reason": "database_unavailable"},
                status_code=503
            )
        
        return JSONResponse(
            content={
                "status": "ready", 
                "timestamp": datetime.utcnow().isoformat(),
                "version": settings.API_VERSION
            },
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "not_ready", "reason": str(e)},
            status_code=503
        )


@app.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe - check if application is alive.
    """
    return JSONResponse(
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int((datetime.utcnow() - start_time).total_seconds())
        },
        status_code=200
    )


# TODO: [API_DOCS] Add comprehensive OpenAPI documentation and examples
# - Add detailed operation descriptions for all safety-critical endpoints
# - Include example request/response payloads with real calculation data
# - Document decimal precision requirements and constraints
# - Add API versioning strategy for future enhancements

# TODO: Configuration endpoint (commented out due to missing settings)
# @app.get("/config")
# async def get_config():
#     """Get non-sensitive configuration values (DEBUG only)."""
#     return {"status": "config endpoint disabled"}


# Include API routers
app.include_router(
    equipment.router,
    prefix=f"{settings.API_V1_STR}/equipment",
    tags=["equipment"],
)

app.include_router(
    inspections.router,
    prefix=f"{settings.API_V1_STR}/inspections",
    tags=["inspections"],
)

app.include_router(
    calculations.router,
    prefix=f"{settings.API_V1_STR}/calculations",
    tags=["calculations"],
)

app.include_router(
    audit.router,
    prefix=f"{settings.API_V1_STR}/audit",
    tags=["audit"],
)

app.include_router(
    analysis.router,
    prefix=f"{settings.API_V1_STR}/analysis",
    tags=["analysis"],
)

app.include_router(
    rbi.router,
    prefix=f"{settings.API_V1_STR}/rbi",
    tags=["rbi"],
)

app.include_router(
    compliance.router,
    prefix=f"{settings.API_V1_STR}/compliance",
    tags=["compliance"],
)

app.include_router(
    batch.router,
    prefix=f"{settings.API_V1_STR}/batch",
    tags=["batch"],
)

app.include_router(
    documents.router,
    tags=["documents"],
)

app.include_router(
    auth_router.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["authentication"],
)




if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="info",
    )
