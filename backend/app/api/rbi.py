"""
Risk-Based Inspection (RBI) API endpoints per API 580/581 standards.
Calculates optimal inspection intervals based on risk assessment and API 579 results.
"""

from typing import Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models.database import get_session_factory
from app.schemas.rbi import (
    IntervalCalculationRequest,
    InspectionIntervalResponse
)
from app.services.rbi_service import RBIService

# Configure logger for audit trail
logger = logging.getLogger("mechanical_integrity.rbi_api")

router = APIRouter(tags=["Risk-Based Inspection"])


# Dependency to get RBI service
def get_rbi_service(session_factory: sessionmaker = Depends(get_session_factory)) -> RBIService:
    """Get RBI service with proper session factory."""
    return RBIService(session_factory)


@router.post("/interval", response_model=InspectionIntervalResponse, status_code=status.HTTP_200_OK)
async def calculate_inspection_interval(
    request: IntervalCalculationRequest,
    rbi_service: RBIService = Depends(get_rbi_service)
) -> InspectionIntervalResponse:
    """
    Calculate optimal inspection interval using Risk-Based Inspection (RBI) methodology.
    
    This endpoint implements API 580/581 RBI methodology to determine:
    - Optimal inspection intervals based on risk assessment
    - Risk justification with POF/COF analysis
    - Inspection scope recommendations
    - Regulatory compliance verification
    
    **Methodology**: Combines API 579 fitness-for-service results with risk factors
    to optimize inspection frequency while maintaining safety and regulatory compliance.
    
    **Risk Assessment**: Uses API 580 risk matrix considering:
    - Probability of Failure (POF): Based on RSF, environment, inspection effectiveness
    - Consequence of Failure (COF): Based on process criticality, equipment size, redundancy
    
    **Safety Critical**: Results directly impact equipment inspection scheduling
    and risk management decisions. All calculations include conservative assumptions.
    
    Args:
        request: RBI calculation request with equipment, calculation, and risk factors
        
    Returns:
        Inspection interval recommendations with detailed risk justification
        
    Raises:
        HTTPException 404: Equipment or API 579 calculation not found
        HTTPException 422: Invalid risk factors or calculation mismatch
        HTTPException 500: Calculation or database errors
    """
    
    # Log request for audit trail
    logger.info(
        f"RBI interval calculation requested for equipment {request.equipment_id}, "
        f"calculation {request.calculation_id}, "
        f"process criticality {request.risk_factors.process_criticality}"
    )
    
    try:
        # Validate request parameters
        if not request.equipment_id or request.equipment_id.isspace():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Equipment ID is required and cannot be empty"
            )
        
        if not request.calculation_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="API 579 calculation ID is required"
            )
        
        # Perform RBI calculation
        result = await rbi_service.calculate_inspection_interval(request)
        
        # Log successful calculation for audit trail
        logger.info(
            f"RBI interval calculation completed for {request.equipment_id}: "
            f"recommended interval {result.recommended_interval_years} years, "
            f"risk level {result.risk_justification.overall_risk_ranking}, "
            f"RSF {result.risk_justification.remaining_strength_factor}"
        )
        
        # Add compliance metadata
        result.calculation_metadata.update({
            "api_version": "v1",
            "compliance_standards": ["API 580", "API 581", "API 579-1/ASME FFS-1"],
            "request_timestamp": datetime.now().isoformat(),
            "conservative_assumptions": True,
            "regulatory_audit_trail": True
        })
        
        return result
        
    except ValueError as e:
        # Business logic errors (equipment not found, calculation mismatch, etc.)
        error_msg = str(e)
        logger.warning(f"RBI validation error for {request.equipment_id}: {error_msg}")
        
        if "not found" in error_msg.lower():
            if "equipment" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Equipment {request.equipment_id} not found in the system"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"API 579 calculation {request.calculation_id} not found"
                )
        elif "not for equipment" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"API 579 calculation {request.calculation_id} is not for equipment {request.equipment_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"RBI validation failed: {error_msg}"
            )
    
    except SQLAlchemyError as e:
        # Database errors
        error_msg = f"Database error during RBI calculation: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during RBI calculation. Please try again later."
        )
    
    except Exception as e:
        # Unexpected errors
        error_msg = f"Unexpected error in RBI calculation: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during RBI calculation. Please contact support."
        )


@router.get("/health")
async def rbi_health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the RBI API.
    
    Returns:
        Health status information including available risk assessment parameters
    """
    return {
        "status": "operational",
        "service": "Risk-Based Inspection API",
        "version": "1.0",
        "methodology": "API 580/581",
        "risk_factors": {
            "process_criticality": ["HIGH", "MEDIUM", "LOW"],
            "corrosion_environment": ["SEVERE", "MODERATE", "MILD"],
            "inspection_effectiveness": ["HIGH", "MEDIUM", "LOW"],
            "material_susceptibility": ["HIGH", "MEDIUM", "LOW"],
            "operating_conditions_severity": ["SEVERE", "MODERATE", "MILD"],
            "redundancy_factor": ["HIGH", "MEDIUM", "LOW", "NONE"]
        },
        "risk_matrix": {
            "probability_of_failure": ["LOW", "MEDIUM", "HIGH"],
            "consequence_of_failure": ["LOW", "MEDIUM", "HIGH"],
            "overall_risk": ["LOW", "MEDIUM-LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"]
        },
        "interval_ranges": {
            "minimum_months": 6,
            "maximum_years": 20,
            "typical_range_years": "1-10"
        },
        "regulatory_compliance": {
            "standards": ["API 580", "API 581", "API 579-1/ASME FFS-1"],
            "risk_based_methodology": True,
            "audit_trail_enabled": True
        },
        "timestamp": datetime.now().isoformat()
    }


# TODO: Future endpoints for Phase 3 implementation
# @router.post("/risk-matrix")
# async def generate_risk_matrix(...):
#     """Generate comprehensive risk matrix for multiple equipment items."""
#     pass

# @router.post("/fleet-analysis") 
# async def perform_fleet_rbi_analysis(...):
#     """Perform RBI analysis for entire equipment fleet."""
#     pass

# @router.get("/risk-ranking/{equipment_id}")
# async def get_equipment_risk_ranking(...):
#     """Get current risk ranking for specific equipment."""
#     pass