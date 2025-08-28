"""
Safety-critical alerting system for mechanical integrity monitoring.

Implements real-time alerting for RSF < 0.9, remaining life < 2 years,
and other safety-critical thresholds per API 579 requirements.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.inspection import API579Calculation
from models.equipment import Equipment, EquipmentCriticality
from app.monitoring.metrics import SAFETY_ALERTS, COMPLIANCE_VIOLATIONS
from core.config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels for safety-critical notifications."""
    CRITICAL = "CRITICAL"    # RSF < 0.9, immediate action required
    HIGH = "HIGH"            # Remaining life < 2 years
    MEDIUM = "MEDIUM"        # Approaching limits
    LOW = "LOW"              # Information/trending


class AlertType(str, Enum):
    """Types of safety-critical alerts."""
    RSF_BELOW_THRESHOLD = "rsf_below_threshold"
    REMAINING_LIFE_LOW = "remaining_life_low"  
    CALCULATION_ERROR = "calculation_error"
    AUDIT_TRAIL_INCOMPLETE = "audit_trail_incomplete"
    EQUIPMENT_OVERDUE = "equipment_overdue"
    CORROSION_ACCELERATED = "corrosion_accelerated"


class SafetyAlert(BaseModel):
    """Safety-critical alert model."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    equipment_id: str
    equipment_tag: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class SafetyAlertingService:
    """
    Service for monitoring and alerting on safety-critical conditions.
    
    Monitors:
    - RSF < 0.9 (CRITICAL - immediate engineering review)
    - Remaining life < 2 years (HIGH - inspection planning needed)
    - Missing audit trails (MEDIUM - compliance risk)
    - Overdue inspections (varies by equipment criticality)
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.active_alerts: Dict[str, SafetyAlert] = {}
        
        # Safety thresholds per API 579
        self.RSF_CRITICAL_THRESHOLD = Decimal('0.9')
        self.REMAINING_LIFE_WARNING_YEARS = Decimal('2.0')
        self.HIGH_CRITICALITY_OVERDUE_DAYS = 30
        self.MEDIUM_CRITICALITY_OVERDUE_DAYS = 90
        self.LOW_CRITICALITY_OVERDUE_DAYS = 180

    async def monitor_safety_conditions(self) -> List[SafetyAlert]:
        """
        Main monitoring loop for safety-critical conditions.
        
        Returns:
            List of new or updated safety alerts
        """
        new_alerts = []
        
        try:
            # Check RSF thresholds
            rsf_alerts = await self._check_rsf_thresholds()
            new_alerts.extend(rsf_alerts)
            
            # Check remaining life warnings
            life_alerts = await self._check_remaining_life()
            new_alerts.extend(life_alerts)
            
            # Check overdue inspections
            overdue_alerts = await self._check_overdue_inspections()
            new_alerts.extend(overdue_alerts)
            
            # Check audit trail completeness
            audit_alerts = await self._check_audit_completeness()
            new_alerts.extend(audit_alerts)
            
            # Update metrics
            for alert in new_alerts:
                SAFETY_ALERTS.labels(
                    alert_type=alert.alert_type.value,
                    equipment_type=alert.details.get('equipment_type', 'unknown'),
                    severity=alert.severity.value
                ).inc()
            
            logger.info(f"Safety monitoring complete: {len(new_alerts)} new alerts")
            return new_alerts
            
        except Exception as e:
            logger.error(f"Error in safety monitoring: {e}")
            return []

    async def _check_rsf_thresholds(self) -> List[SafetyAlert]:
        """Check for RSF values below critical threshold."""
        alerts = []
        
        # Query recent calculations with low RSF
        recent_calculations = self.db.query(API579Calculation).join(
            Equipment, API579Calculation.inspection_record.has(
                equipment_id=Equipment.id
            )
        ).filter(
            and_(
                API579Calculation.remaining_strength_factor < self.RSF_CRITICAL_THRESHOLD,
                API579Calculation.created_at > datetime.utcnow() - timedelta(hours=24)
            )
        ).all()
        
        for calc in recent_calculations:
            equipment = self.db.query(Equipment).filter(
                Equipment.id == calc.inspection_record.equipment_id
            ).first()
            
            if equipment:
                alert_id = f"rsf_{equipment.id}_{calc.id}"
                
                if alert_id not in self.active_alerts:
                    alert = SafetyAlert(
                        alert_id=alert_id,
                        alert_type=AlertType.RSF_BELOW_THRESHOLD,
                        severity=AlertSeverity.CRITICAL,
                        equipment_id=str(equipment.id),
                        equipment_tag=equipment.tag_number,
                        message=f"CRITICAL: RSF {calc.remaining_strength_factor} below 0.9 threshold",
                        details={
                            'rsf_value': float(calc.remaining_strength_factor),
                            'threshold': 0.9,
                            'equipment_type': equipment.equipment_type.value,
                            'calculation_id': str(calc.id),
                            'fitness_for_service': calc.fitness_for_service,
                            'recommendations': calc.recommendations
                        },
                        timestamp=datetime.utcnow()
                    )
                    
                    self.active_alerts[alert_id] = alert
                    alerts.append(alert)
        
        return alerts

    async def _check_remaining_life(self) -> List[SafetyAlert]:
        """Check for remaining life below warning threshold."""
        alerts = []
        
        # Query calculations with low remaining life
        low_life_calculations = self.db.query(API579Calculation).join(
            Equipment, API579Calculation.inspection_record.has(
                equipment_id=Equipment.id
            )
        ).filter(
            and_(
                API579Calculation.remaining_life_years.isnot(None),
                API579Calculation.remaining_life_years < self.REMAINING_LIFE_WARNING_YEARS,
                API579Calculation.created_at > datetime.utcnow() - timedelta(days=7)
            )
        ).all()
        
        for calc in low_life_calculations:
            equipment = self.db.query(Equipment).filter(
                Equipment.id == calc.inspection_record.equipment_id
            ).first()
            
            if equipment and calc.remaining_life_years:
                alert_id = f"life_{equipment.id}_{calc.id}"
                
                if alert_id not in self.active_alerts:
                    severity = AlertSeverity.CRITICAL if calc.remaining_life_years < Decimal('1.0') else AlertSeverity.HIGH
                    
                    alert = SafetyAlert(
                        alert_id=alert_id,
                        alert_type=AlertType.REMAINING_LIFE_LOW,
                        severity=severity,
                        equipment_id=str(equipment.id),
                        equipment_tag=equipment.tag_number,
                        message=f"Remaining life: {calc.remaining_life_years} years",
                        details={
                            'remaining_life_years': float(calc.remaining_life_years),
                            'threshold_years': 2.0,
                            'equipment_type': equipment.equipment_type.value,
                            'equipment_criticality': equipment.criticality.value,
                            'calculation_id': str(calc.id)
                        },
                        timestamp=datetime.utcnow()
                    )
                    
                    self.active_alerts[alert_id] = alert
                    alerts.append(alert)
        
        return alerts

    async def _check_overdue_inspections(self) -> List[SafetyAlert]:
        """Check for overdue inspections based on equipment criticality."""
        alerts = []
        current_date = datetime.utcnow()
        
        # Query equipment with overdue inspections
        overdue_equipment = self.db.query(Equipment).filter(
            or_(
                and_(
                    Equipment.criticality == EquipmentCriticality.HIGH,
                    Equipment.last_inspection_date < current_date - timedelta(days=self.HIGH_CRITICALITY_OVERDUE_DAYS)
                ),
                and_(
                    Equipment.criticality == EquipmentCriticality.MEDIUM,
                    Equipment.last_inspection_date < current_date - timedelta(days=self.MEDIUM_CRITICALITY_OVERDUE_DAYS)
                ),
                and_(
                    Equipment.criticality == EquipmentCriticality.LOW,
                    Equipment.last_inspection_date < current_date - timedelta(days=self.LOW_CRITICALITY_OVERDUE_DAYS)
                )
            )
        ).all()
        
        for equipment in overdue_equipment:
            alert_id = f"overdue_{equipment.id}"
            
            if alert_id not in self.active_alerts:
                days_overdue = (current_date - equipment.last_inspection_date).days
                
                # Severity based on equipment criticality and overdue duration
                if equipment.criticality == EquipmentCriticality.HIGH:
                    severity = AlertSeverity.CRITICAL if days_overdue > 60 else AlertSeverity.HIGH
                elif equipment.criticality == EquipmentCriticality.MEDIUM:
                    severity = AlertSeverity.HIGH if days_overdue > 120 else AlertSeverity.MEDIUM
                else:
                    severity = AlertSeverity.MEDIUM
                
                alert = SafetyAlert(
                    alert_id=alert_id,
                    alert_type=AlertType.EQUIPMENT_OVERDUE,
                    severity=severity,
                    equipment_id=str(equipment.id),
                    equipment_tag=equipment.tag_number,
                    message=f"Inspection overdue by {days_overdue} days",
                    details={
                        'days_overdue': days_overdue,
                        'last_inspection': equipment.last_inspection_date.isoformat() if equipment.last_inspection_date else None,
                        'equipment_criticality': equipment.criticality.value,
                        'equipment_type': equipment.equipment_type.value
                    },
                    timestamp=current_date
                )
                
                self.active_alerts[alert_id] = alert
                alerts.append(alert)
        
        return alerts

    async def _check_audit_completeness(self) -> List[SafetyAlert]:
        """Check for incomplete audit trails."""
        alerts = []
        
        # Query calculations missing required audit trail elements
        incomplete_audits = self.db.query(API579Calculation).filter(
            or_(
                API579Calculation.reviewed_by.is_(None),
                API579Calculation.assumptions.is_(None),
                API579Calculation.input_parameters.is_(None)
            )
        ).filter(
            API579Calculation.created_at > datetime.utcnow() - timedelta(days=1)
        ).all()
        
        for calc in incomplete_audits:
            equipment = self.db.query(Equipment).filter(
                Equipment.id == calc.inspection_record.equipment_id
            ).first()
            
            if equipment:
                alert_id = f"audit_{equipment.id}_{calc.id}"
                
                if alert_id not in self.active_alerts:
                    missing_elements = []
                    if not calc.reviewed_by:
                        missing_elements.append("reviewer")
                    if not calc.assumptions:
                        missing_elements.append("assumptions")
                    if not calc.input_parameters:
                        missing_elements.append("input_parameters")
                    
                    alert = SafetyAlert(
                        alert_id=alert_id,
                        alert_type=AlertType.AUDIT_TRAIL_INCOMPLETE,
                        severity=AlertSeverity.MEDIUM,
                        equipment_id=str(equipment.id),
                        equipment_tag=equipment.tag_number,
                        message=f"Incomplete audit trail: missing {', '.join(missing_elements)}",
                        details={
                            'missing_elements': missing_elements,
                            'calculation_id': str(calc.id),
                            'calculation_date': calc.created_at.isoformat()
                        },
                        timestamp=datetime.utcnow()
                    )
                    
                    self.active_alerts[alert_id] = alert
                    alerts.append(alert)
                    
                    # Update compliance metrics
                    COMPLIANCE_VIOLATIONS.labels(
                        violation_type='incomplete_audit_trail',
                        severity='medium'
                    ).inc()
        
        return alerts

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge a safety alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        
        return False

    async def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[SafetyAlert]:
        """Get all active (unacknowledged) alerts, optionally filtered by severity."""
        alerts = [alert for alert in self.active_alerts.values() if not alert.acknowledged]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return alerts

    async def send_notifications(self, alerts: List[SafetyAlert]):
        """Send notifications for safety-critical alerts."""
        for alert in alerts:
            if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                # In production, integrate with PagerDuty, OpsGenie, email, etc.
                logger.critical(f"SAFETY ALERT: {alert.message} - Equipment: {alert.equipment_tag}")
                
                # TODO: Implement actual notification service integration
                # await self.send_pagerduty_alert(alert)
                # await self.send_email_notification(alert) 
                # await self.send_slack_notification(alert)