"""
Mechanical Integrity AI - Main FastAPI Application
Safety-critical API for equipment inspection and API 579 compliance.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from decimal import Decimal

from backend.core.config import settings
from backend.app.api.v1 import equipment, inspections, analysis
from backend.models.database import verify_db_connection
from backend.utils.redis_client import verify_redis_connection
from backend.services.ollama_client import verify_ollama_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events.
    Verify all critical services are running.
    """
    # Startup
    logger.info("🚀 Starting Mechanical Integrity AI System")
    
    # Verify critical services
    services_ok = True
    
    # Check database
    if not verify_db_connection():
        logger.error("❌ PostgreSQL connection failed")
        services_ok = False
    else:
        logger.info("✅ PostgreSQL connected")
    
    # Check Redis
    if not verify_redis_connection():
        logger.error("❌ Redis connection failed")
        services_ok = False
    else:
        logger.info("✅ Redis connected")
    
    # Check Ollama
    if not verify_ollama_connection():
        logger.warning("⚠️ Ollama not available - AI features disabled")
    else:
        logger.info("✅ Ollama connected")
    
    if not services_ok:
        logger.error("❌ Critical services unavailable - startup aborted")
        raise RuntimeError("Required services not available")
    
    logger.info("✨ All systems operational")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Mechanical Integrity AI System")


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

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vue/React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            "safety_factor": float(settings.SAFETY_FACTOR),
            "audit_logging": settings.ENABLE_AUDIT_LOG
        },
        "api_documentation": "/docs",
        "health_check": "/health"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Comprehensive health check for all services.
    Used by monitoring systems and load balancers.
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.APP_VERSION,
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "ollama": "unknown"
        },
        "checks_passed": 0,
        "checks_total": 3
    }
    
    # Check database
    try:
        if verify_db_connection():
            health_status["services"]["database"] = "healthy"
            health_status["checks_passed"] += 1
        else:
            health_status["services"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        if verify_redis_connection():
            health_status["services"]["redis"] = "healthy"
            health_status["checks_passed"] += 1
        else:
            health_status["services"]["redis"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Ollama (optional service)
    try:
        if verify_ollama_connection():
            health_status["services"]["ollama"] = "healthy"
            health_status["checks_passed"] += 1
        else:
            health_status["services"]["ollama"] = "not available"
    except Exception as e:
        health_status["services"]["ollama"] = f"error: {str(e)}"
    
    # Determine HTTP status code
    if health_status["status"] == "healthy":
        status_code = 200
    elif health_status["status"] == "degraded":
        status_code = 503  # Service Unavailable
    else:
        status_code = 503
    
    return JSONResponse(content=health_status, status_code=status_code)


# Configuration endpoint (only in debug mode)
if settings.DEBUG:
    @app.get("/config")
    async def get_config():
        """Get non-sensitive configuration values (DEBUG only)."""
        return {
            "app_name": settings.APP_NAME,
            "api_version": settings.API_V1_STR,
            "safety_factor": float(settings.SAFETY_FACTOR),
            "default_corrosion_rate": float(settings.DEFAULT_CORROSION_RATE),
            "calculation_precision": {
                "thickness": settings.THICKNESS_PRECISION,
                "pressure": settings.PRESSURE_PRECISION,
                "stress": settings.STRESS_PRECISION
            },
            "escalation_thresholds": {
                "min_remaining_life_years": float(settings.MIN_REMAINING_LIFE_YEARS),
                "min_rsf": float(settings.MIN_RSF_THRESHOLD)
            },
            "compliance_settings": {
                "audit_log_enabled": settings.ENABLE_AUDIT_LOG,
                "human_verification_required": settings.REQUIRE_HUMAN_VERIFICATION,
                "log_calculation_steps": settings.LOG_CALCULATION_STEPS
            }
        }


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
    analysis.router,
    prefix=f"{settings.API_V1_STR}/analysis",
    tags=["analysis"],
)


# Startup message
@app.on_event("startup")
async def startup_message():
    """Display startup banner."""
    print("\n" + "="*60)
    print("🏭 MECHANICAL INTEGRITY AI SYSTEM")
    print("="*60)
    print(f"Version: {settings.APP_VERSION}")
    print(f"Safety Factor: {settings.SAFETY_FACTOR}")
    print(f"API Standards: 579-1, 510, 570, 653")
    print(f"Compliance Mode: {'ENABLED' if settings.REQUIRE_HUMAN_VERIFICATION else 'DISABLED'}")
    print("="*60)
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🔍 Health Check: http://localhost:8000/health")
    print("="*60 + "\n")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
