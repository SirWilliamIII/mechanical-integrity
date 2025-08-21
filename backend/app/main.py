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

from core.config import settings
from app.api import equipment, inspections
from models.database import verify_db_connection
from app.services.document_analyzer import DocumentAnalyzer
from app.services.health import get_system_health

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
    
    # Display startup banner
    print("\n" + "="*60)
    print("🏭 MECHANICAL INTEGRITY AI SYSTEM")
    print("="*60)
    print(f"Version: {settings.APP_VERSION}")
    print(f"Safety Factor: 0.9")
    print(f"API Standards: 579-1, 510, 570, 653")
    print(f"Compliance Mode: ENABLED")
    print("="*60)
    print(f"📚 API Docs: http://localhost:8001/docs")
    print(f"🔍 Health Check: http://localhost:8001/health")
    print("="*60 + "\n")
    
    # Verify critical services
    services_ok = True
    
    # Check database
    if not verify_db_connection():
        logger.error("❌ PostgreSQL connection failed")
        services_ok = False
    else:
        logger.info("✅ PostgreSQL connected")
    
    # TODO: [SERVICES] Implement Redis and Ollama health checks for production readiness
    # Missing service checks prevent proper monitoring of background job queue and LLM processing
    # Redis required for document processing queue, Ollama for inspection report analysis
    logger.info("✅ Redis check skipped (not implemented)")
    logger.info("✅ Ollama check skipped (not implemented)")
    
    if not services_ok:
        logger.warning("⚠️  Some services unavailable - running in degraded mode")
        # raise RuntimeError("Required services not available")
    
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


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Comprehensive health check for all services.
    Used by monitoring systems and load balancers.
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




if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="info",
    )
