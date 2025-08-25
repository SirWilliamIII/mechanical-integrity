"""
Analysis API schemas for corrosion rate trend analysis and remaining life projections.
Safety-critical schemas with full validation for API 579 compliance.
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, ConfigDict


class CorrosionRateRequest(BaseModel):
    """Request schema for corrosion rate trend analysis."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    equipment_id: str = Field(
        ..., 
        min_length=1, 
        max_length=50,
        description="Equipment tag number or ID for analysis"
    )
    
    analysis_type: Literal["corrosion_rate_trend", "statistical", "linear", "exponential"] = Field(
        default="corrosion_rate_trend",
        description="Type of corrosion rate analysis to perform"
    )
    
    confidence_level: Literal["conservative", "nominal", "optimistic"] = Field(
        default="conservative",
        description="Conservative for safety-critical calculations"
    )
    
    # Optional parameters for advanced analysis
    time_period_years: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Analysis time period in years (default: all available data)"
    )
    
    include_prediction_intervals: bool = Field(
        default=True,
        description="Include statistical prediction intervals in results"
    )

    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format for safety-critical systems."""
        if not v or v.isspace():
            raise ValueError("Equipment ID cannot be empty")
        
        # Basic format validation for common tag formats
        if not any(char.isalnum() or char in ['-', '_'] for char in v):
            raise ValueError("Equipment ID contains invalid characters")
            
        return v.upper().strip()


class CMLCorrosionRate(BaseModel):
    """Corrosion rate data for a specific CML location."""
    
    model_config = ConfigDict(str_to_lower=False)
    
    cml_number: str = Field(..., description="Corrosion Monitoring Location identifier")
    location: str = Field(..., description="Physical location description")
    rate_inches_per_year: Decimal = Field(
        ..., 
        ge=Decimal('0'),
        le=Decimal('1.0'),  # 1 inch/year is extremely high
        decimal_places=6,
        description="Corrosion rate in inches per year"
    )
    confidence_interval_lower: Optional[Decimal] = Field(
        None,
        decimal_places=6,
        description="Lower bound of 95% confidence interval"
    )
    confidence_interval_upper: Optional[Decimal] = Field(
        None,
        decimal_places=6,
        description="Upper bound of 95% confidence interval"
    )
    data_quality: Literal["high", "medium", "low"] = Field(
        ...,
        description="Quality assessment of underlying data"
    )
    measurement_count: int = Field(
        ...,
        ge=2,
        description="Number of thickness measurements used in calculation"
    )

    @field_validator('rate_inches_per_year')
    @classmethod
    def validate_corrosion_rate(cls, v: Decimal) -> Decimal:
        """Validate corrosion rate is within realistic bounds."""
        if v > Decimal('0.100'):  # 0.1 inch/year is very aggressive
            raise ValueError(f"Corrosion rate {v} inches/year exceeds realistic maximum")
        return v


class TrendAnalysis(BaseModel):
    """Statistical trend analysis of corrosion data."""
    
    trend_direction: Literal["increasing", "decreasing", "stable"] = Field(
        ...,
        description="Overall trend direction of corrosion rates"
    )
    
    trend_strength: Literal["strong", "moderate", "weak", "insignificant"] = Field(
        ...,
        description="Statistical significance of the trend"
    )
    
    average_rate_inches_per_year: Decimal = Field(
        ...,
        decimal_places=6,
        description="Average corrosion rate across all CMLs"
    )
    
    maximum_rate_inches_per_year: Decimal = Field(
        ...,
        decimal_places=6,
        description="Highest corrosion rate found"
    )
    
    critical_locations: List[str] = Field(
        default_factory=list,
        description="CML locations with concerning corrosion rates"
    )
    
    analysis_period_years: Decimal = Field(
        ...,
        ge=Decimal('0.1'),
        decimal_places=1,
        description="Time period covered by the analysis"
    )
    
    statistical_confidence: Decimal = Field(
        ...,
        ge=Decimal('0.50'),
        le=Decimal('0.99'),
        decimal_places=3,
        description="Statistical confidence level (0.95 = 95%)"
    )


class RemainingLifeProjection(BaseModel):
    """Remaining life projection based on corrosion analysis."""
    
    conservative_years: Decimal = Field(
        ...,
        ge=Decimal('0'),
        decimal_places=1,
        description="Conservative remaining life estimate (years)"
    )
    
    nominal_years: Decimal = Field(
        ...,
        ge=Decimal('0'),
        decimal_places=1,
        description="Nominal remaining life estimate (years)"
    )
    
    optimistic_years: Optional[Decimal] = Field(
        None,
        ge=Decimal('0'),
        decimal_places=1,
        description="Optimistic remaining life estimate (years)"
    )
    
    limiting_location: str = Field(
        ...,
        description="CML location that determines remaining life"
    )
    
    minimum_thickness_inches: Decimal = Field(
        ...,
        ge=Decimal('0'),
        decimal_places=4,
        description="Minimum allowable thickness per API 579"
    )
    
    current_minimum_thickness: Decimal = Field(
        ...,
        ge=Decimal('0'),
        decimal_places=4,
        description="Current minimum measured thickness"
    )
    
    safety_factor_applied: Decimal = Field(
        ...,
        ge=Decimal('0.1'),
        le=Decimal('1.0'),
        decimal_places=2,
        description="Safety factor applied to calculations"
    )
    
    calculation_date: datetime = Field(
        default_factory=datetime.now,
        description="When this projection was calculated"
    )

    @field_validator('conservative_years')
    @classmethod
    def validate_remaining_life(cls, v: Decimal) -> Decimal:
        """Validate remaining life is reasonable."""
        if v > Decimal('100'):  # 100 years is extremely long for industrial equipment
            raise ValueError(f"Remaining life {v} years exceeds reasonable maximum")
        return v


class CorrosionRateResponse(BaseModel):
    """Complete response for corrosion rate analysis."""
    
    model_config = ConfigDict(
        str_to_lower=False,
        validate_assignment=True
    )
    
    equipment_id: str = Field(..., description="Equipment analyzed")
    analysis_type: str = Field(..., description="Type of analysis performed")
    
    corrosion_rates: List[CMLCorrosionRate] = Field(
        ...,
        description="Corrosion rates by CML location"
    )
    
    trend_analysis: TrendAnalysis = Field(
        ...,
        description="Overall trend analysis results"
    )
    
    remaining_life_projection: RemainingLifeProjection = Field(
        ...,
        description="Remaining life projections"
    )
    
    calculation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional calculation details and assumptions"
    )
    
    audit_trail: Dict[str, Any] = Field(
        default_factory=dict,
        description="Audit information for regulatory compliance"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this analysis was performed"
    )

    @field_validator('corrosion_rates')
    @classmethod
    def validate_non_empty_rates(cls, v: List[CMLCorrosionRate]) -> List[CMLCorrosionRate]:
        """Ensure at least one corrosion rate is provided."""
        if not v:
            raise ValueError("At least one CML corrosion rate must be provided")
        return v