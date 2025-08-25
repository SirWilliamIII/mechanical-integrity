"""
Analysis API endpoints for corrosion rate trend analysis and remaining life projections.
Safety-critical API following API 579 compliance requirements with complete audit trail.
"""

from typing import Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models.database import get_session_factory
from app.schemas.analysis import (
    CorrosionRateRequest,
    CorrosionRateResponse
)
from app.services.analysis_service import AnalysisService

# Configure logger for audit trail
logger = logging.getLogger("mechanical_integrity.analysis_api")

router = APIRouter(tags=["Analysis"])


# Dependency to get analysis service
def get_analysis_service(session_factory: sessionmaker = Depends(get_session_factory)) -> AnalysisService:
    """Get analysis service with proper session factory."""
    return AnalysisService(session_factory)


@router.post("/corrosion-rate", response_model=CorrosionRateResponse, status_code=status.HTTP_200_OK)
async def analyze_corrosion_rate(
    request: CorrosionRateRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service)
) -> CorrosionRateResponse:
    """
    Perform comprehensive corrosion rate trend analysis for equipment.
    
    This endpoint analyzes historical thickness measurement data to calculate:
    - Corrosion rates by CML (Corrosion Monitoring Location)
    - Statistical trend analysis with confidence intervals
    - Remaining life projections with safety factors
    
    **Safety Critical**: Results are used for fitness-for-service decisions.
    All calculations include conservative safety factors per API 579 requirements.
    
    **Audit Trail**: Complete calculation metadata and assumptions are logged
    for regulatory compliance and engineering review.
    
    Args:
        request: Analysis request with equipment ID and parameters
        
    Returns:
        Complete corrosion rate analysis with trends and projections
        
    Raises:
        HTTPException 404: Equipment not found
        HTTPException 422: Insufficient data for analysis
        HTTPException 500: Calculation or database errors
    """
    
    # Log request for audit trail
    logger.info(
        f"Corrosion rate analysis requested for equipment {request.equipment_id} "
        f"by analysis type {request.analysis_type}, confidence level {request.confidence_level}"
    )
    
    try:
        # Validate request parameters
        if not request.equipment_id or request.equipment_id.isspace():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Equipment ID is required and cannot be empty"
            )
        
        # Perform analysis
        result = await analysis_service.analyze_corrosion_rates(request)
        
        # Log successful analysis for audit trail
        logger.info(
            f"Corrosion rate analysis completed for {request.equipment_id}: "
            f"{len(result.corrosion_rates)} CMLs analyzed, "
            f"average rate {result.trend_analysis.average_rate_inches_per_year} in/yr, "
            f"remaining life {result.remaining_life_projection.conservative_years} years"
        )
        
        # Add compliance metadata
        result.audit_trail.update({
            "api_version": "v1",
            "compliance_standard": "API 579-1/ASME FFS-1",
            "request_timestamp": datetime.now().isoformat(),
            "safety_factors_applied": True,
            "regulatory_audit_trail": True
        })
        
        return result
        
    except ValueError as e:
        # Business logic errors (equipment not found, insufficient data)
        error_msg = str(e)
        logger.warning(f"Analysis validation error for {request.equipment_id}: {error_msg}")
        
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment {request.equipment_id} not found in the system"
            )
        elif "insufficient" in error_msg.lower() or "no thickness" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Insufficient thickness measurement data for analysis: {error_msg}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Analysis validation failed: {error_msg}"
            )
    
    except SQLAlchemyError as e:
        # Database errors
        error_msg = f"Database error during corrosion rate analysis: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during analysis. Please try again later."
        )
    
    except Exception as e:
        # Unexpected errors
        error_msg = f"Unexpected error in corrosion rate analysis: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during analysis. Please contact support."
        )


@router.get("/health")
async def analysis_health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the Analysis API.
    
    Returns:
        Health status information including available analysis types
    """
    return {
        "status": "operational",
        "service": "Analysis API",
        "version": "1.0",
        "available_analysis_types": [
            "corrosion_rate_trend",
            "statistical", 
            "linear",
            "exponential"
        ],
        "confidence_levels": [
            "conservative",
            "nominal", 
            "optimistic"
        ],
        "regulatory_compliance": {
            "standards": ["API 579-1/ASME FFS-1"],
            "safety_factors_applied": True,
            "audit_trail_enabled": True
        },
        "timestamp": datetime.now().isoformat()
    }


# TODO: Future endpoints for Phase 3 implementation
# @router.post("/level-2-assessment")
# async def perform_level_2_assessment(...):
#     """Advanced API 579 Level 2 assessment with detailed stress analysis."""
#     pass

# @router.post("/monte-carlo-analysis") 
# async def perform_monte_carlo_analysis(...):
#     """Monte Carlo uncertainty analysis for remaining life projections."""
#     pass

# @router.post("/batch-analysis")
# async def perform_batch_analysis(...):
#     """Batch analysis for multiple equipment items."""
#     pass