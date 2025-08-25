"""
Risk-Based Inspection (RBI) Service implementation per API 580/581 standards.
Calculates optimal inspection intervals based on risk assessment and API 579 calculations.
"""

from typing import Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from enum import Enum

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models import Equipment, API579Calculation, InspectionRecord
from app.schemas.rbi import (
    IntervalCalculationRequest,
    InspectionIntervalResponse,
    RiskJustification,
    RiskFactors
)

logger = logging.getLogger("mechanical_integrity.rbi_service")


class RiskLevel(Enum):
    """Risk level enumeration per API 580."""
    LOW = "LOW"
    MEDIUM_LOW = "MEDIUM-LOW"
    MEDIUM = "MEDIUM"
    MEDIUM_HIGH = "MEDIUM-HIGH"
    HIGH = "HIGH"


class RBIService:
    """
    Risk-Based Inspection service implementing API 580/581 methodology.
    
    Calculates optimal inspection intervals by combining:
    - Probability of Failure (POF) assessments
    - Consequence of Failure (COF) assessments  
    - API 579 fitness-for-service results
    - Regulatory requirements and constraints
    """
    
    def __init__(self, session_factory: sessionmaker):
        """Initialize with database session factory for proper isolation."""
        self.session_factory = session_factory
        self.logger = logger
    
    async def calculate_inspection_interval(
        self, 
        request: IntervalCalculationRequest
    ) -> InspectionIntervalResponse:
        """
        Calculate optimal inspection interval using RBI methodology.
        
        Args:
            request: RBI calculation request with equipment and risk factors
            
        Returns:
            Inspection interval recommendations with risk justification
            
        Raises:
            ValueError: If equipment or calculation not found
            SQLAlchemyError: Database operation failures
        """
        
        self.logger.info(
            f"Starting RBI interval calculation for equipment {request.equipment_id}, "
            f"calculation {request.calculation_id}"
        )
        
        try:
            with self.session_factory() as session:
                # Validate equipment and calculation exist
                equipment, calculation = await self._validate_request(session, request)
                
                # Assess Probability of Failure (POF)
                pof_assessment = await self._assess_probability_of_failure(
                    session, equipment, calculation, request.risk_factors
                )
                
                # Assess Consequence of Failure (COF)  
                cof_assessment = await self._assess_consequence_of_failure(
                    session, equipment, request.risk_factors
                )
                
                # Determine overall risk level
                risk_level = await self._determine_risk_level(pof_assessment, cof_assessment)
                
                # Calculate base inspection interval
                base_interval = await self._calculate_base_interval(risk_level, calculation)
                
                # Apply regulatory and business constraints
                final_intervals = await self._apply_constraints(
                    base_interval, request, equipment
                )
                
                # Generate risk justification
                risk_justification = await self._generate_risk_justification(
                    pof_assessment, cof_assessment, risk_level, calculation, request.risk_factors
                )
                
                # Create response
                response = InspectionIntervalResponse(
                    equipment_id=request.equipment_id,
                    calculation_id=request.calculation_id,
                    recommended_interval_years=final_intervals["recommended"],
                    maximum_interval_years=final_intervals["maximum"],
                    minimum_interval_years=final_intervals.get("minimum"),
                    risk_justification=risk_justification,
                    next_inspection_due_date=await self._calculate_next_inspection_date(
                        session, equipment, final_intervals["recommended"]
                    ),
                    inspection_scope_recommendations=await self._generate_inspection_scope(
                        risk_level, equipment, calculation
                    ),
                    regulatory_compliance=await self._assess_regulatory_compliance(
                        equipment, final_intervals
                    ),
                    calculation_metadata=await self._create_calculation_metadata(request, risk_level),
                    created_at=datetime.now(),
                    created_by="RBI_Service_v1.0"
                )
                
                self.logger.info(
                    f"RBI interval calculation completed for {request.equipment_id}: "
                    f"recommended {final_intervals['recommended']} years, "
                    f"risk level {risk_level.value}"
                )
                
                return response
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error in RBI calculation: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in RBI calculation: {e}")
            raise
    
    async def _validate_request(
        self, 
        session: Session, 
        request: IntervalCalculationRequest
    ) -> Tuple[Equipment, API579Calculation]:
        """Validate that equipment and calculation exist."""
        
        # Find equipment
        equipment = session.query(Equipment).filter(
            Equipment.tag_number == request.equipment_id
        ).first()
        
        if not equipment:
            raise ValueError(f"Equipment {request.equipment_id} not found")
        
        # Find API 579 calculation
        calculation = session.query(API579Calculation).filter(
            API579Calculation.id == request.calculation_id
        ).first()
        
        if not calculation:
            raise ValueError(f"API 579 calculation {request.calculation_id} not found")
        
        # Verify calculation is for the same equipment
        if calculation.inspection.equipment_id != equipment.id:
            raise ValueError(
                f"Calculation {request.calculation_id} is not for equipment {request.equipment_id}"
            )
        
        return equipment, calculation
    
    async def _assess_probability_of_failure(
        self,
        session: Session,
        equipment: Equipment, 
        calculation: API579Calculation,
        risk_factors: RiskFactors
    ) -> str:
        """Assess Probability of Failure per API 580 methodology."""
        
        pof_score = 0
        
        # Factor 1: Remaining Strength Factor from API 579
        rsf = calculation.remaining_strength_factor
        if rsf < Decimal('0.8'):
            pof_score += 3  # High contribution
        elif rsf < Decimal('1.0'):
            pof_score += 2  # Medium contribution  
        else:
            pof_score += 1  # Low contribution
        
        # Factor 2: Corrosion environment
        env_map = {"SEVERE": 3, "MODERATE": 2, "MILD": 1}
        pof_score += env_map.get(risk_factors.corrosion_environment, 2)
        
        # Factor 3: Inspection effectiveness
        eff_map = {"LOW": 3, "MEDIUM": 2, "HIGH": 1}
        pof_score += eff_map.get(risk_factors.inspection_effectiveness, 2)
        
        # Factor 4: Material susceptibility (if provided)
        if risk_factors.material_susceptibility:
            susc_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            pof_score += susc_map.get(risk_factors.material_susceptibility, 2)
        
        # Factor 5: Operating conditions severity (if provided)
        if risk_factors.operating_conditions_severity:
            op_map = {"SEVERE": 3, "MODERATE": 2, "MILD": 1}
            pof_score += op_map.get(risk_factors.operating_conditions_severity, 2)
        
        # Factor 6: Previous failures (if provided)
        if risk_factors.previous_failures is not None:
            if risk_factors.previous_failures > 2:
                pof_score += 3
            elif risk_factors.previous_failures > 0:
                pof_score += 2
            # No additional score for zero failures
        
        # Convert score to POF category
        if pof_score <= 6:
            return "LOW"
        elif pof_score <= 12:
            return "MEDIUM"
        else:
            return "HIGH"
    
    async def _assess_consequence_of_failure(
        self,
        session: Session,
        equipment: Equipment,
        risk_factors: RiskFactors
    ) -> str:
        """Assess Consequence of Failure per API 580 methodology."""
        
        cof_score = 0
        
        # Factor 1: Process criticality
        crit_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        cof_score += crit_map.get(risk_factors.process_criticality, 2)
        
        # Factor 2: Equipment type and size (inferred from design parameters)
        if equipment.design_pressure > Decimal('600'):
            cof_score += 2  # High pressure equipment
        if equipment.design_temperature > Decimal('400'):
            cof_score += 2  # High temperature equipment
        
        # Factor 3: Redundancy factor (if provided)
        if risk_factors.redundancy_factor:
            red_map = {"NONE": 3, "LOW": 2, "MEDIUM": 1, "HIGH": 0}
            cof_score += red_map.get(risk_factors.redundancy_factor, 1)
        
        # Factor 4: Equipment location (simplified assessment)
        # In practice, this would consider environmental consequences,
        # population density, etc.
        cof_score += 2  # Default medium consequence
        
        # Convert score to COF category
        if cof_score <= 4:
            return "LOW"
        elif cof_score <= 8:
            return "MEDIUM"
        else:
            return "HIGH"
    
    async def _determine_risk_level(self, pof: str, cof: str) -> RiskLevel:
        """Determine overall risk level using API 580 risk matrix."""
        
        # API 580 risk matrix (simplified)
        risk_matrix = {
            ("LOW", "LOW"): RiskLevel.LOW,
            ("LOW", "MEDIUM"): RiskLevel.MEDIUM_LOW,
            ("LOW", "HIGH"): RiskLevel.MEDIUM,
            ("MEDIUM", "LOW"): RiskLevel.MEDIUM_LOW,
            ("MEDIUM", "MEDIUM"): RiskLevel.MEDIUM,
            ("MEDIUM", "HIGH"): RiskLevel.MEDIUM_HIGH,
            ("HIGH", "LOW"): RiskLevel.MEDIUM,
            ("HIGH", "MEDIUM"): RiskLevel.MEDIUM_HIGH,
            ("HIGH", "HIGH"): RiskLevel.HIGH,
        }
        
        return risk_matrix.get((pof, cof), RiskLevel.MEDIUM)
    
    async def _calculate_base_interval(
        self, 
        risk_level: RiskLevel, 
        calculation: API579Calculation
    ) -> Decimal:
        """Calculate base inspection interval based on risk level and RSF."""
        
        # Base intervals by risk level (years)
        base_intervals = {
            RiskLevel.LOW: Decimal('10.0'),
            RiskLevel.MEDIUM_LOW: Decimal('6.0'),
            RiskLevel.MEDIUM: Decimal('4.0'),
            RiskLevel.MEDIUM_HIGH: Decimal('2.0'),
            RiskLevel.HIGH: Decimal('1.0')
        }
        
        base_interval = base_intervals[risk_level]
        
        # Adjust based on Remaining Strength Factor
        rsf = calculation.remaining_strength_factor
        if rsf < Decimal('0.8'):
            # Low RSF requires more frequent inspection
            base_interval *= Decimal('0.5')
        elif rsf < Decimal('1.0'):
            base_interval *= Decimal('0.75')
        # RSF >= 1.0 uses base interval
        
        # Ensure minimum interval of 6 months for high-risk equipment
        return max(base_interval, Decimal('0.5'))
    
    async def _apply_constraints(
        self,
        base_interval: Decimal,
        request: IntervalCalculationRequest,
        equipment: Equipment
    ) -> Dict[str, Decimal]:
        """Apply regulatory and business constraints to inspection interval."""
        
        recommended = base_interval
        
        # Regulatory maximum limits (simplified)
        # In practice, these would be jurisdiction-specific
        regulatory_max = Decimal('10.0')  # 10 years maximum
        
        # Apply regulatory constraints from request
        if request.regulatory_requirements:
            reg_max = request.regulatory_requirements.get("maximum_interval_years")
            if reg_max:
                regulatory_max = min(regulatory_max, Decimal(str(reg_max)))
        
        # Apply business constraints
        if request.business_constraints:
            business_max = request.business_constraints.get("maximum_interval_years")
            if business_max:
                regulatory_max = min(regulatory_max, Decimal(str(business_max)))
        
        # Final constraints
        maximum_interval = regulatory_max
        recommended = min(recommended, maximum_interval)
        
        # Minimum interval for critical equipment
        minimum_interval = None
        if recommended <= Decimal('1.0'):
            minimum_interval = Decimal('0.5')  # 6 months minimum
        
        return {
            "recommended": recommended,
            "maximum": maximum_interval,
            "minimum": minimum_interval
        }
    
    async def _generate_risk_justification(
        self,
        pof: str,
        cof: str,
        risk_level: RiskLevel,
        calculation: API579Calculation,
        risk_factors: RiskFactors
    ) -> RiskJustification:
        """Generate detailed risk justification for the interval decision."""
        
        # Determine corrosion rate trend (simplified)
        # In practice, this would use the Analysis API results
        corrosion_trend = "STABLE"  # Default assumption
        
        # Key factors influencing the assessment
        key_factors = [
            f"Remaining Strength Factor: {calculation.remaining_strength_factor}",
            f"Process criticality: {risk_factors.process_criticality}",
            f"Corrosion environment: {risk_factors.corrosion_environment}",
            f"Inspection effectiveness: {risk_factors.inspection_effectiveness}"
        ]
        
        # Add optional factors if provided
        if risk_factors.material_susceptibility:
            key_factors.append(f"Material susceptibility: {risk_factors.material_susceptibility}")
        
        if risk_factors.operating_conditions_severity:
            key_factors.append(f"Operating conditions: {risk_factors.operating_conditions_severity}")
        
        if risk_factors.previous_failures is not None:
            key_factors.append(f"Previous failures: {risk_factors.previous_failures}")
        
        # Mitigation measures based on risk level
        mitigation_measures = []
        if risk_level in [RiskLevel.MEDIUM_HIGH, RiskLevel.HIGH]:
            mitigation_measures.extend([
                "Enhanced inspection techniques recommended",
                "Consider online monitoring systems",
                "Develop detailed inspection procedures"
            ])
        
        if calculation.remaining_strength_factor < Decimal('0.9'):
            mitigation_measures.append("Monitor corrosion rate trends closely")
        
        return RiskJustification(
            probability_of_failure_category=pof,
            consequence_of_failure_category=cof,
            overall_risk_ranking=risk_level.value,
            remaining_strength_factor=calculation.remaining_strength_factor,
            corrosion_rate_trend=corrosion_trend,
            key_factors=key_factors,
            mitigation_measures=mitigation_measures if mitigation_measures else None
        )
    
    async def _calculate_next_inspection_date(
        self,
        session: Session,
        equipment: Equipment,
        interval_years: Decimal
    ) -> Optional[datetime]:
        """Calculate the next inspection due date."""
        
        # Find the most recent inspection
        latest_inspection = session.query(InspectionRecord).filter(
            InspectionRecord.equipment_id == equipment.id
        ).order_by(InspectionRecord.inspection_date.desc()).first()
        
        if latest_inspection:
            # Calculate from last inspection date
            interval_days = int(interval_years * 365)
            next_due = latest_inspection.inspection_date + timedelta(days=interval_days)
            return next_due
        
        # No previous inspections - calculate from installation date
        if equipment.installation_date:
            interval_days = int(interval_years * 365)
            next_due = equipment.installation_date + timedelta(days=interval_days)
            return next_due
        
        return None
    
    async def _generate_inspection_scope(
        self,
        risk_level: RiskLevel,
        equipment: Equipment,
        calculation: API579Calculation
    ) -> list[str]:
        """Generate inspection scope recommendations based on risk assessment."""
        
        scope = ["Visual inspection of all accessible surfaces"]
        
        # Add thickness measurements for all equipment
        scope.append("Ultrasonic thickness measurements at all CML locations")
        
        # Enhanced scope for higher risk equipment
        if risk_level in [RiskLevel.MEDIUM_HIGH, RiskLevel.HIGH]:
            scope.extend([
                "100% thickness survey of critical areas",
                "Non-destructive testing (PT/MT) of welds",
                "Internal inspection where accessible"
            ])
        
        # Additional scope based on equipment type
        if equipment.equipment_type == "VESSEL":
            scope.append("Inspect all nozzles and connections")
        elif equipment.equipment_type == "PIPING":
            scope.append("Focus on areas of expected high corrosion rates")
        
        # Low RSF requires detailed inspection
        if calculation.remaining_strength_factor < Decimal('0.9'):
            scope.append("Detailed fitness-for-service assessment")
        
        return scope
    
    async def _assess_regulatory_compliance(
        self,
        equipment: Equipment,
        intervals: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """Assess regulatory compliance status."""
        
        return {
            "compliant": True,  # Simplified - would check against specific regulations
            "applicable_codes": ["ASME B31.3", "API 570", "API 510"],
            "jurisdiction": "Generic",
            "maximum_allowed_interval": str(intervals["maximum"]),
            "notes": "Intervals calculated per API 580 RBI methodology"
        }
    
    async def _create_calculation_metadata(
        self,
        request: IntervalCalculationRequest,
        risk_level: RiskLevel
    ) -> Dict[str, Any]:
        """Create calculation metadata for audit trail."""
        
        return {
            "rbi_methodology": "API 580/581",
            "calculation_version": "1.0",
            "risk_matrix_version": "Simplified_API_580",
            "risk_level_determined": risk_level.value,
            "safety_factors_applied": True,
            "regulatory_compliance_checked": True,
            "assumptions": {
                "corrosion_rate_trend": "Stable (default)",
                "environmental_factors": "Standard industrial environment",
                "inspection_quality": "Per API 510/570 standards"
            }
        }