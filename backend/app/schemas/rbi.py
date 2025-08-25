"""
Risk-Based Inspection (RBI) API schemas per API 580/581 standards.
Safety-critical schemas for inspection interval optimization.
"""

from typing import Dict, Any, Optional, Literal
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


class RiskFactors(BaseModel):
    """Risk factors for RBI interval calculation per API 580."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    # Probability of Failure factors
    process_criticality: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ...,
        description="Process criticality level per API 580"
    )
    
    corrosion_environment: Literal["SEVERE", "MODERATE", "MILD"] = Field(
        ...,
        description="Corrosive environment assessment"
    )
    
    inspection_effectiveness: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ...,
        description="Historical inspection effectiveness rating"
    )
    
    # Optional advanced factors
    material_susceptibility: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = Field(
        None,
        description="Material susceptibility to active damage mechanisms"
    )
    
    operating_conditions_severity: Optional[Literal["SEVERE", "MODERATE", "MILD"]] = Field(
        None,
        description="Operating conditions severity assessment"
    )
    
    previous_failures: Optional[int] = Field(
        None,
        ge=0,
        le=10,
        description="Number of previous failures or significant findings"
    )
    
    redundancy_factor: Optional[Literal["HIGH", "MEDIUM", "LOW", "NONE"]] = Field(
        None,
        description="Equipment redundancy and backup systems availability"
    )


class IntervalCalculationRequest(BaseModel):
    """Request schema for RBI interval calculation."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    equipment_id: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Equipment tag number or ID"
    )
    
    calculation_id: UUID = Field(
        ...,
        description="Associated API 579 calculation ID"
    )
    
    risk_factors: RiskFactors = Field(
        ...,
        description="Risk assessment factors per API 580"
    )
    
    # Optional parameters
    regulatory_requirements: Optional[Dict[str, Any]] = Field(
        None,
        description="Specific regulatory requirements or constraints"
    )
    
    business_constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="Business or operational constraints"
    )

    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format."""
        if not v or v.isspace():
            raise ValueError("Equipment ID cannot be empty")
        return v.upper().strip()


class RiskJustification(BaseModel):
    """Detailed risk justification for inspection interval."""
    
    probability_of_failure_category: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ...,
        description="POF category per API 580 risk matrix"
    )
    
    consequence_of_failure_category: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        ...,
        description="COF category per API 580 risk matrix"
    )
    
    overall_risk_ranking: Literal["LOW", "MEDIUM-LOW", "MEDIUM", "MEDIUM-HIGH", "HIGH"] = Field(
        ...,
        description="Overall risk ranking from API 580 risk matrix"
    )
    
    remaining_strength_factor: Decimal = Field(
        ...,
        ge=Decimal('0'),
        le=Decimal('2.0'),
        decimal_places=3,
        description="Current RSF from API 579 calculation"
    )
    
    corrosion_rate_trend: Literal["INCREASING", "STABLE", "DECREASING"] = Field(
        ...,
        description="Trend in corrosion rate from analysis"
    )
    
    key_factors: list[str] = Field(
        ...,
        min_length=1,
        description="Key factors influencing the risk assessment"
    )
    
    mitigation_measures: Optional[list[str]] = Field(
        None,
        description="Recommended risk mitigation measures"
    )

    @field_validator('remaining_strength_factor')
    @classmethod
    def validate_rsf(cls, v: Decimal) -> Decimal:
        """Validate RSF is within reasonable bounds."""
        if v < Decimal('0.5'):
            # Very low RSF - should trigger immediate action
            pass  # Allow but will be flagged in business logic
        elif v > Decimal('1.5'):
            # RSF > 1.5 is unusual but possible for new equipment
            pass
        return v


class InspectionIntervalResponse(BaseModel):
    """Response schema for RBI interval calculation."""
    
    model_config = ConfigDict(
        str_to_lower=False,
        validate_assignment=True
    )
    
    equipment_id: str = Field(..., description="Equipment analyzed")
    calculation_id: UUID = Field(..., description="Associated API 579 calculation")
    
    # Recommended intervals
    recommended_interval_years: Decimal = Field(
        ...,
        ge=Decimal('0.5'),
        le=Decimal('20.0'),
        decimal_places=1,
        description="Recommended inspection interval in years"
    )
    
    maximum_interval_years: Decimal = Field(
        ...,
        ge=Decimal('0.5'),
        le=Decimal('20.0'),
        decimal_places=1,
        description="Maximum allowable interval per regulations"
    )
    
    minimum_interval_years: Optional[Decimal] = Field(
        None,
        ge=Decimal('0.1'),
        le=Decimal('10.0'),
        decimal_places=1,
        description="Minimum interval for high-risk situations"
    )
    
    # Risk assessment details
    risk_justification: RiskJustification = Field(
        ...,
        description="Detailed risk assessment and justification"
    )
    
    # Next inspection details
    next_inspection_due_date: Optional[datetime] = Field(
        None,
        description="Calculated next inspection due date"
    )
    
    inspection_scope_recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended inspection scope and methods"
    )
    
    # Regulatory compliance
    regulatory_compliance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Regulatory compliance status and requirements"
    )
    
    # Audit trail
    calculation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Calculation assumptions and methodology"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this RBI analysis was performed"
    )
    
    created_by: Optional[str] = Field(
        None,
        description="Engineer or system that performed the analysis"
    )

    @field_validator('recommended_interval_years')
    @classmethod 
    def validate_recommended_interval(cls, v: Decimal) -> Decimal:
        """Validate recommended interval is reasonable."""
        if v > Decimal('10.0'):
            # Intervals > 10 years are unusual for process equipment
            pass  # Allow but will generate warnings
        elif v < Decimal('1.0'):
            # Intervals < 1 year indicate high risk situations
            pass  # Allow but will trigger notifications
        return v

    @field_validator('maximum_interval_years')
    @classmethod
    def validate_maximum_interval(cls, v: Decimal) -> Decimal:
        """Validate maximum interval against regulatory limits."""
        if v > Decimal('15.0'):
            # Most jurisdictions limit intervals to 15 years max
            pass  # Allow but generate regulatory compliance warnings
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation."""
        # Ensure recommended <= maximum
        if self.recommended_interval_years > self.maximum_interval_years:
            raise ValueError("Recommended interval cannot exceed maximum interval")
        
        # Ensure minimum <= recommended (if minimum is specified)
        if (self.minimum_interval_years is not None and 
            self.minimum_interval_years > self.recommended_interval_years):
            raise ValueError("Minimum interval cannot exceed recommended interval")


class RBICalculationSummary(BaseModel):
    """Summary of RBI calculations for reporting."""
    
    equipment_count: int = Field(..., ge=0, description="Number of equipment items analyzed")
    high_risk_equipment: int = Field(..., ge=0, description="Equipment in high risk category")
    overdue_inspections: int = Field(..., ge=0, description="Equipment with overdue inspections")
    
    average_interval_years: Decimal = Field(
        ...,
        ge=Decimal('0'),
        decimal_places=1,
        description="Average recommended interval"
    )
    
    total_risk_reduction: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        le=Decimal('100'),
        description="Estimated risk reduction percentage from RBI program"
    )