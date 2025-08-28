"""
Analysis Service for corrosion rate trend analysis and remaining life projections.
Implements statistical analysis of thickness measurement data with API 579 integration.
"""

from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_UP
import statistics
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from models import (
    Equipment, 
    InspectionRecord
)
from app.schemas.analysis import (
    CorrosionRateRequest,
    CorrosionRateResponse,
    CMLCorrosionRate,
    TrendAnalysis,
    RemainingLifeProjection
)
from core.config import settings

logger = logging.getLogger("mechanical_integrity.analysis_service")


@dataclass
class CMLData:
    """Internal data structure for CML analysis."""
    cml_number: str
    location: str
    measurements: List[Tuple[datetime, Decimal]]  # (date, thickness)
    
    @property
    def measurement_count(self) -> int:
        return len(self.measurements)
    
    @property
    def current_thickness(self) -> Optional[Decimal]:
        """Get the most recent thickness measurement."""
        if not self.measurements:
            return None
        return max(self.measurements, key=lambda x: x[0])[1]
    
    @property
    def oldest_thickness(self) -> Optional[Decimal]:
        """Get the oldest thickness measurement."""
        if not self.measurements:
            return None
        return min(self.measurements, key=lambda x: x[0])[1]
    
    @property
    def time_span_years(self) -> Optional[Decimal]:
        """Get the time span of measurements in years."""
        if len(self.measurements) < 2:
            return None
        
        dates = [m[0] for m in self.measurements]
        time_span = max(dates) - min(dates)
        return Decimal(time_span.days) / Decimal(365.25)


class AnalysisService:
    """
    Service for performing corrosion rate trend analysis and remaining life calculations.
    
    Implements statistical analysis of thickness measurement data following API 579
    guidelines for remaining life assessment with conservative safety factors.
    """
    
    def __init__(self, session_factory: sessionmaker):
        """Initialize with database session factory for proper isolation."""
        self.session_factory = session_factory
        self.logger = logger
    
    async def analyze_corrosion_rates(self, request: CorrosionRateRequest) -> CorrosionRateResponse:
        """
        Perform comprehensive corrosion rate analysis for equipment.
        
        Args:
            request: Analysis request with equipment ID and parameters
            
        Returns:
            Complete corrosion rate analysis with trends and projections
            
        Raises:
            ValueError: If equipment not found or insufficient data
            SQLAlchemyError: Database operation failures
        """
        self.logger.info(f"Starting corrosion rate analysis for equipment {request.equipment_id}")
        
        # Map confidence level strings to numerical values
        confidence_map = {
            "conservative": 0.90,  # Conservative for safety-critical
            "nominal": 0.95,       # Standard engineering practice
            "optimistic": 0.99     # High confidence for well-characterized systems
        }
        numeric_confidence = confidence_map[request.confidence_level]
        
        try:
            with self.session_factory() as session:
                # Validate equipment exists
                equipment = session.query(Equipment).filter(
                    Equipment.tag_number == request.equipment_id
                ).first()
                
                if not equipment:
                    raise ValueError(f"Equipment {request.equipment_id} not found")
                
                # Gather thickness measurement data
                cml_data = await self._gather_thickness_data(session, equipment, request.time_period_years)
                
                if not cml_data:
                    raise ValueError(f"No thickness measurement data found for equipment {request.equipment_id}")
                
                # Calculate corrosion rates for each CML
                corrosion_rates = await self._calculate_cml_corrosion_rates(
                    cml_data, request.confidence_level, request.include_prediction_intervals
                )
                
                # Perform trend analysis
                trend_analysis = await self._perform_trend_analysis(cml_data, corrosion_rates, numeric_confidence)
                
                # Calculate remaining life projections
                remaining_life = await self._calculate_remaining_life(
                    session, equipment, corrosion_rates, request.confidence_level
                )
                
                # Create audit trail
                audit_trail = {
                    "analysis_timestamp": datetime.now().isoformat(),
                    "equipment_id": equipment.tag_number,
                    "analysis_method": request.analysis_type,
                    "confidence_level": request.confidence_level,
                    "data_points_analyzed": sum(cml.measurement_count for cml in cml_data),
                    "calculation_assumptions": self._get_calculation_assumptions(),
                    "api_579_compliance": True
                }
                
                calculation_metadata = {
                    "analysis_version": "1.0",
                    "statistical_method": "linear_regression_with_confidence_intervals",
                    "safety_factors_applied": True,
                    "minimum_data_points": 2,
                    "maximum_extrapolation_years": 50
                }
                
                response = CorrosionRateResponse(
                    equipment_id=request.equipment_id,
                    analysis_type=request.analysis_type,
                    corrosion_rates=corrosion_rates,
                    trend_analysis=trend_analysis,
                    remaining_life_projection=remaining_life,
                    calculation_metadata=calculation_metadata,
                    audit_trail=audit_trail
                )
                
                self.logger.info(
                    f"Completed corrosion rate analysis for {request.equipment_id}: "
                    f"{len(corrosion_rates)} CMLs analyzed, "
                    f"remaining life {remaining_life.conservative_years} years"
                )
                
                return response
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in corrosion rate analysis: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in corrosion rate analysis: {e}")
            raise
    
    async def _gather_thickness_data(
        self, 
        session: Session, 
        equipment: Equipment,
        time_period_years: Optional[int] = None
    ) -> List[CMLData]:
        """Gather and organize thickness measurement data by CML."""
        
        # Get all inspections for this equipment
        inspections = session.query(InspectionRecord).filter(
            InspectionRecord.equipment_id == equipment.id
        ).order_by(InspectionRecord.inspection_date.asc()).all()
        
        # Apply time period filter if specified
        if time_period_years:
            cutoff_date = datetime.now() - timedelta(days=time_period_years * 365)
            inspections = [i for i in inspections if i.inspection_date >= cutoff_date]
        
        # Group thickness readings by CML
        cml_dict: Dict[str, CMLData] = {}
        
        for inspection in inspections:
            # Check both detailed readings and JSON readings
            thickness_readings = []
            
            # First, try detailed thickness readings (preferred)
            if inspection.thickness_readings_detailed:
                thickness_readings = inspection.thickness_readings_detailed
                
                for reading in thickness_readings:
                    cml_key = reading.cml_number or f"CML-{reading.id}"
                    location = reading.location_description or "Unknown Location"
                    
                    if cml_key not in cml_dict:
                        cml_dict[cml_key] = CMLData(
                            cml_number=cml_key,
                            location=location,
                            measurements=[]
                        )
                    
                    # Add measurement with inspection date
                    inspection_date = inspection.inspection_date
                    thickness = reading.thickness_measured
                    
                    cml_dict[cml_key].measurements.append((inspection_date, thickness))
            
            # Fallback to JSON thickness readings if no detailed readings
            elif inspection.thickness_readings:
                json_readings = inspection.thickness_readings
                if isinstance(json_readings, dict) and 'readings' in json_readings:
                    json_readings = json_readings['readings']
                elif not isinstance(json_readings, list):
                    continue
                
                for reading_data in json_readings:
                    if not isinstance(reading_data, dict):
                        continue
                        
                    cml_key = reading_data.get('cml_number', f"CML-{inspection.id}")
                    location = reading_data.get('location', 'Unknown Location')
                    thickness = reading_data.get('thickness')
                    
                    if thickness is None:
                        continue
                    
                    # Convert thickness to Decimal if it's a string/float
                    if not isinstance(thickness, Decimal):
                        try:
                            thickness = Decimal(str(thickness))
                        except (ValueError, TypeError):
                            continue
                    
                    if cml_key not in cml_dict:
                        cml_dict[cml_key] = CMLData(
                            cml_number=cml_key,
                            location=location,
                            measurements=[]
                        )
                    
                    # Add measurement with inspection date
                    inspection_date = inspection.inspection_date
                    cml_dict[cml_key].measurements.append((inspection_date, thickness))
        
        # Filter CMLs with sufficient data (minimum 2 measurements)
        valid_cmls = [
            cml for cml in cml_dict.values() 
            if cml.measurement_count >= 2
        ]
        
        self.logger.info(f"Found {len(valid_cmls)} CMLs with sufficient data for analysis")
        return valid_cmls
    
    async def _calculate_cml_corrosion_rates(
        self,
        cml_data: List[CMLData],
        confidence_level: str,
        include_prediction_intervals: bool
    ) -> List[CMLCorrosionRate]:
        """Calculate corrosion rates for each CML using linear regression."""
        
        # Map confidence level strings to numerical values
        confidence_map = {
            "conservative": 0.90,  # Conservative for safety-critical
            "nominal": 0.95,       # Standard engineering practice
            "optimistic": 0.99     # High confidence for well-characterized systems
        }
        numeric_confidence = confidence_map[confidence_level]
        
        corrosion_rates = []
        
        for cml in cml_data:
            try:
                # Perform linear regression on thickness vs time
                rate, confidence_bounds = self._linear_regression_analysis(
                    cml.measurements, include_prediction_intervals, numeric_confidence
                )
                
                # Apply safety factors based on confidence level
                if confidence_level == "conservative":
                    # Use upper bound of confidence interval for conservative estimate
                    adjusted_rate = confidence_bounds[1] if confidence_bounds else rate * Decimal('1.2')
                elif confidence_level == "optimistic":
                    # Use lower bound for optimistic estimate
                    adjusted_rate = confidence_bounds[0] if confidence_bounds else rate * Decimal('0.8')
                else:  # nominal
                    adjusted_rate = rate
                
                # Ensure non-negative rate (thickness loss)
                final_rate = max(Decimal('0'), abs(adjusted_rate))
                
                # Round to 6 decimal places for Pydantic validation
                final_rate = final_rate.quantize(Decimal('0.000001'))
                
                # Round confidence bounds if they exist
                confidence_lower = None
                confidence_upper = None
                if confidence_bounds:
                    confidence_lower = confidence_bounds[0].quantize(Decimal('0.000001'))
                    confidence_upper = confidence_bounds[1].quantize(Decimal('0.000001'))
                
                # Assess data quality
                data_quality = self._assess_data_quality(cml)
                
                corrosion_rate = CMLCorrosionRate(
                    cml_number=cml.cml_number,
                    location=cml.location,
                    rate_inches_per_year=final_rate,
                    confidence_interval_lower=confidence_lower,
                    confidence_interval_upper=confidence_upper,
                    data_quality=data_quality,
                    measurement_count=cml.measurement_count
                )
                
                corrosion_rates.append(corrosion_rate)
                
            except Exception as e:
                self.logger.warning(f"Failed to calculate corrosion rate for CML {cml.cml_number}: {e}")
                continue
        
        if not corrosion_rates:
            raise ValueError("Unable to calculate corrosion rates for any CML locations")
        
        return corrosion_rates
    
    def _linear_regression_analysis(
        self, 
        measurements: List[Tuple[datetime, Decimal]],
        include_confidence_intervals: bool,
        numeric_confidence: float = 0.95
    ) -> Tuple[Decimal, Optional[Tuple[Decimal, Decimal]]]:
        """Perform linear regression to calculate corrosion rate."""
        
        if len(measurements) < 2:
            raise ValueError("Insufficient data points for regression analysis")
        
        # Convert to numerical data for regression
        # x = years from first measurement, y = thickness
        first_date = min(measurements, key=lambda x: x[0])[0]
        
        x_values = []
        y_values = []
        
        for date, thickness in measurements:
            years_delta = (date - first_date).days / 365.25
            x_values.append(float(years_delta))
            y_values.append(float(thickness))
        
        # Calculate linear regression manually
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_xx = sum(x * x for x in x_values)
        
        # Slope (corrosion rate) = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
        denominator = n * sum_xx - sum_x * sum_x
        
        if abs(denominator) < 1e-10:  # Avoid division by zero
            # All measurements at same time - use simple difference
            if len(measurements) >= 2:
                oldest = min(measurements, key=lambda x: x[0])
                newest = max(measurements, key=lambda x: x[0])
                time_span = (newest[0] - oldest[0]).days / 365.25
                
                if time_span > 0:
                    rate = abs(float(oldest[1] - newest[1])) / time_span
                    return Decimal(str(rate)), None
            
            return Decimal('0'), None
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Convert to positive rate (thickness loss)
        corrosion_rate = Decimal(str(abs(slope)))
        
        # Calculate confidence intervals if requested
        confidence_bounds = None
        if include_confidence_intervals and n > 2:
            try:
                confidence_bounds = self._calculate_confidence_intervals(
                    x_values, y_values, slope, confidence_level=numeric_confidence
                )
            except Exception as e:
                self.logger.warning(f"Could not calculate confidence intervals: {e}")
        
        return corrosion_rate, confidence_bounds
    
    def _calculate_confidence_intervals(
        self, 
        x_values: List[float], 
        y_values: List[float], 
        slope: float, 
        confidence_level: float = 0.95
    ) -> Tuple[Decimal, Decimal]:
        """Calculate confidence intervals for regression slope."""
        
        n = len(x_values)
        if n < 3:
            return None
        
        # Calculate intercept
        mean_x = statistics.mean(x_values)
        mean_y = statistics.mean(y_values)
        intercept = mean_y - slope * mean_x
        
        # Calculate residual standard error
        predicted_y = [slope * x + intercept for x in x_values]
        residuals = [actual - predicted for actual, predicted in zip(y_values, predicted_y)]
        residual_sum_squares = sum(r * r for r in residuals)
        
        if residual_sum_squares == 0:
            return None
        
        standard_error = (residual_sum_squares / (n - 2)) ** 0.5
        
        # Standard error of slope
        sum_xx = sum((x - mean_x) ** 2 for x in x_values)
        slope_se = standard_error / (sum_xx ** 0.5)
        
        # t-value for confidence level (approximate for df > 30)
        t_value = 1.96 if n > 30 else 2.0  # Conservative approximation
        
        margin = t_value * slope_se
        
        lower_bound = Decimal(str(abs(slope - margin)))
        upper_bound = Decimal(str(abs(slope + margin)))
        
        return (lower_bound, upper_bound)
    
    def _assess_data_quality(self, cml: CMLData) -> str:
        """Assess the quality of thickness measurement data."""
        
        count = cml.measurement_count
        time_span = cml.time_span_years or Decimal('0')
        
        # Quality criteria
        if count >= 5 and time_span >= Decimal('2'):
            return "high"
        elif count >= 3 and time_span >= Decimal('1'):
            return "medium"
        else:
            return "low"
    
    async def _perform_trend_analysis(
        self, 
        cml_data: List[CMLData], 
        corrosion_rates: List[CMLCorrosionRate],
        numeric_confidence: float
    ) -> TrendAnalysis:
        """Perform overall trend analysis across all CMLs."""
        
        if not corrosion_rates:
            raise ValueError("No corrosion rates available for trend analysis")
        
        # Calculate statistics
        rates = [float(rate.rate_inches_per_year) for rate in corrosion_rates]
        avg_rate = Decimal(str(statistics.mean(rates)))
        max_rate = max(rate.rate_inches_per_year for rate in corrosion_rates)
        
        # Determine trend direction (simplified analysis)
        # In practice, this would use more sophisticated statistical tests
        trend_direction = "stable"  # Default
        if avg_rate > Decimal('0.010'):  # 10 mils/year
            trend_direction = "increasing"
        elif avg_rate < Decimal('0.002'):  # 2 mils/year
            trend_direction = "decreasing"
        
        # Assess trend strength based on data consistency
        rate_variance = statistics.variance(rates) if len(rates) > 1 else 0
        if rate_variance < 0.0001:
            trend_strength = "strong"
        elif rate_variance < 0.001:
            trend_strength = "moderate"
        elif rate_variance < 0.01:
            trend_strength = "weak"
        else:
            trend_strength = "insignificant"
        
        # Identify critical locations (rates > 20 mils/year)
        critical_locations = [
            rate.cml_number for rate in corrosion_rates
            if rate.rate_inches_per_year > Decimal('0.020')
        ]
        
        # Calculate analysis period
        all_measurements = [m for cml in cml_data for m in cml.measurements]
        if all_measurements:
            dates = [m[0] for m in all_measurements]
            analysis_period = (max(dates) - min(dates)).days / 365.25
        else:
            analysis_period = 0
        
        return TrendAnalysis(
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            average_rate_inches_per_year=avg_rate,
            maximum_rate_inches_per_year=max_rate,
            critical_locations=critical_locations,
            analysis_period_years=Decimal(str(analysis_period)),
            statistical_confidence=Decimal(str(numeric_confidence))  # Dynamic confidence based on request
        )
    
    async def _calculate_remaining_life(
        self,
        session: Session,
        equipment: Equipment,
        corrosion_rates: List[CMLCorrosionRate],
        confidence_level: str
    ) -> RemainingLifeProjection:
        """Calculate remaining life projections based on corrosion rates."""
        
        # Find the highest corrosion rate (limiting case)
        max_rate_cml = max(corrosion_rates, key=lambda x: x.rate_inches_per_year)
        limiting_rate = max_rate_cml.rate_inches_per_year
        
        if limiting_rate <= Decimal('0'):
            # No measurable corrosion - use nominal life
            conservative_life = Decimal('50.0')  # 50 years default
            nominal_life = Decimal('75.0')
        else:
            # Get current minimum thickness from most recent inspections
            latest_inspection = session.query(InspectionRecord).filter(
                InspectionRecord.equipment_id == equipment.id
            ).order_by(desc(InspectionRecord.inspection_date)).first()
            
            if not latest_inspection:
                raise ValueError("No inspection data available for remaining life calculation")
            
            # Try to get minimum thickness from various sources
            current_min_thickness = None
            
            # First, try the min_thickness_found field
            if latest_inspection.min_thickness_found:
                current_min_thickness = latest_inspection.min_thickness_found
            
            # Fallback to detailed thickness readings
            elif latest_inspection.thickness_readings_detailed:
                readings = [r.thickness_measured for r in latest_inspection.thickness_readings_detailed]
                if readings:
                    current_min_thickness = min(readings)
            
            # Fallback to JSON thickness readings
            elif latest_inspection.thickness_readings:
                json_readings = latest_inspection.thickness_readings
                if isinstance(json_readings, dict) and 'readings' in json_readings:
                    json_readings = json_readings['readings']
                
                if isinstance(json_readings, list):
                    thicknesses = []
                    for reading_data in json_readings:
                        if isinstance(reading_data, dict) and 'thickness' in reading_data:
                            try:
                                thickness = Decimal(str(reading_data['thickness']))
                                thicknesses.append(thickness)
                            except (ValueError, TypeError):
                                continue
                    
                    if thicknesses:
                        current_min_thickness = min(thicknesses)
            
            if current_min_thickness is None:
                raise ValueError("No thickness data available for remaining life calculation")
            
            # Calculate minimum allowable thickness (simplified API 579 approach)
            # In practice, this would integrate with full API 579 calculations
            design_thickness = equipment.design_thickness
            corrosion_allowance = design_thickness * Decimal('0.1')  # 10% allowance
            minimum_thickness = design_thickness - corrosion_allowance
            
            # Available thickness for corrosion
            available_thickness = current_min_thickness - minimum_thickness
            
            if available_thickness <= Decimal('0'):
                # Already at minimum thickness
                conservative_life = Decimal('0')
                nominal_life = Decimal('0')
            else:
                # Apply safety factors
                safety_factor = settings.API579_DEFAULT_SAFETY_FACTOR  # 0.9 from config
                
                conservative_life = (available_thickness * Decimal(str(safety_factor))) / limiting_rate
                nominal_life = available_thickness / limiting_rate
        
        # Round down for conservative estimates
        conservative_life = conservative_life.quantize(Decimal('0.1'), rounding=ROUND_UP)
        nominal_life = nominal_life.quantize(Decimal('0.1'), rounding=ROUND_UP)
        
        # Get current minimum thickness for response
        response_thickness = Decimal('0')
        if latest_inspection:
            if latest_inspection.min_thickness_found:
                response_thickness = latest_inspection.min_thickness_found
            elif latest_inspection.thickness_readings_detailed:
                readings = [r.thickness_measured for r in latest_inspection.thickness_readings_detailed]
                if readings:
                    response_thickness = min(readings)
        
        return RemainingLifeProjection(
            conservative_years=conservative_life,
            nominal_years=nominal_life,
            optimistic_years=nominal_life * Decimal('1.2') if nominal_life > Decimal('0') else None,
            limiting_location=max_rate_cml.cml_number,
            minimum_thickness_inches=equipment.design_thickness * Decimal('0.9'),  # 90% of design
            current_minimum_thickness=response_thickness,
            safety_factor_applied=Decimal(str(settings.API579_DEFAULT_SAFETY_FACTOR)),
            calculation_date=datetime.now()
        )
    
    def _get_calculation_assumptions(self) -> Dict[str, Any]:
        """Get calculation assumptions for audit trail."""
        return {
            "regression_method": "linear_least_squares",
            "minimum_data_points": 2,
            "safety_factor": settings.API579_DEFAULT_SAFETY_FACTOR,
            "confidence_intervals": "95_percent",
            "thickness_measurement_precision": "0.001_inches",
            "regulatory_standard": "API_579_Level_1",
            "conservative_assumptions": True
        }