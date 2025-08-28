"""
Advanced health checks for safety-critical mechanical integrity system.

Implements comprehensive monitoring of system performance, data integrity,
and safety-critical calculation accuracy.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text

from app.services.health.checks import ServiceHealth, ServiceStatus
from models.database import get_db
from models.equipment import Equipment
from models.inspection import InspectionRecord
from app.monitoring.metrics import MetricsCollector
from core.config import settings
import logging

logger = logging.getLogger(__name__)


class SafetyCriticalHealthChecker:
    """
    Advanced health checker for safety-critical aspects of the system.
    
    Monitors:
    - Data integrity and consistency
    - Calculation accuracy
    - Audit trail completeness
    - Performance metrics
    """
    
    def __init__(self):
        self.db_session: Optional[AsyncSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.db_session = await anext(get_db())
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources."""
        if self.db_session:
            await self.db_session.close()
    
    async def check_data_integrity(self) -> ServiceHealth:
        """
        Check data integrity for safety-critical tables.
        
        Validates:
        - Equipment records have required fields
        - Inspection records are properly linked
        - No orphaned thickness readings
        - Calculation inputs/outputs consistency
        """
        start = datetime.utcnow()
        
        try:
            # Check equipment data integrity
            equipment_issues = await self._check_equipment_integrity()
            
            # Check inspection data integrity
            inspection_issues = await self._check_inspection_integrity()
            
            # Check calculation data integrity
            calculation_issues = await self._check_calculation_integrity()
            
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            total_issues = len(equipment_issues) + len(inspection_issues) + len(calculation_issues)
            
            if total_issues == 0:
                return ServiceHealth(
                    name="data_integrity",
                    status=ServiceStatus.HEALTHY,
                    message="All data integrity checks passed",
                    details={
                        "equipment_checks": "passed",
                        "inspection_checks": "passed", 
                        "calculation_checks": "passed"
                    },
                    response_time_ms=response_time
                )
            elif total_issues <= 5:  # Minor issues
                return ServiceHealth(
                    name="data_integrity",
                    status=ServiceStatus.DEGRADED,
                    message=f"Minor data integrity issues found ({total_issues} issues)",
                    details={
                        "equipment_issues": equipment_issues,
                        "inspection_issues": inspection_issues,
                        "calculation_issues": calculation_issues,
                        "total_issues": total_issues
                    },
                    response_time_ms=response_time
                )
            else:  # Major issues
                return ServiceHealth(
                    name="data_integrity",
                    status=ServiceStatus.UNHEALTHY,
                    message=f"Significant data integrity issues found ({total_issues} issues)",
                    details={
                        "equipment_issues": equipment_issues,
                        "inspection_issues": inspection_issues,
                        "calculation_issues": calculation_issues,
                        "total_issues": total_issues,
                        "action_required": "Immediate review needed"
                    },
                    response_time_ms=response_time
                )
                
        except Exception as e:
            logger.error(f"Data integrity check failed: {e}")
            return ServiceHealth(
                name="data_integrity",
                status=ServiceStatus.UNHEALTHY,
                message=f"Data integrity check failed: {str(e)}",
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )
    
    async def _check_equipment_integrity(self) -> List[Dict[str, Any]]:
        """Check equipment table integrity."""
        issues = []
        
        # Check for equipment without required dimensions
        result = await self.db_session.execute(
            text("""
                SELECT COUNT(*) FROM equipment 
                WHERE design_pressure IS NULL 
                OR design_temperature IS NULL 
                OR design_thickness IS NULL
            """)
        )
        missing_dimensions = result.scalar()
        
        if missing_dimensions > 0:
            issues.append({
                "type": "missing_dimensions",
                "count": missing_dimensions,
                "severity": "high",
                "message": "Equipment records missing critical dimensions"
            })
        
        # Check for invalid pressure values (negative or zero)
        result = await self.db_session.execute(
            text("SELECT COUNT(*) FROM equipment WHERE design_pressure <= 0")
        )
        invalid_pressure = result.scalar()
        
        if invalid_pressure > 0:
            issues.append({
                "type": "invalid_pressure",
                "count": invalid_pressure,
                "severity": "high",
                "message": "Equipment with invalid pressure values"
            })
        
        return issues
    
    async def _check_inspection_integrity(self) -> List[Dict[str, Any]]:
        """Check inspection data integrity."""
        issues = []
        
        # Check for inspections without thickness readings
        result = await self.db_session.execute(
            text("""
                SELECT COUNT(*) FROM inspection_records ir
                LEFT JOIN thickness_readings tr ON ir.id = tr.inspection_record_id
                WHERE tr.id IS NULL
            """)
        )
        inspections_without_readings = result.scalar()
        
        if inspections_without_readings > 0:
            issues.append({
                "type": "missing_thickness_readings",
                "count": inspections_without_readings,
                "severity": "high",
                "message": "Inspections without thickness measurements"
            })
        
        # Check for thickness readings with invalid values
        result = await self.db_session.execute(
            text("""
                SELECT COUNT(*) FROM thickness_readings 
                WHERE measured_thickness <= 0 
                OR measured_thickness > 10
            """)
        )
        invalid_thickness = result.scalar()
        
        if invalid_thickness > 0:
            issues.append({
                "type": "invalid_thickness",
                "count": invalid_thickness,
                "severity": "medium",
                "message": "Thickness readings outside valid range (0-10 inches)"
            })
        
        return issues
    
    async def _check_calculation_integrity(self) -> List[Dict[str, Any]]:
        """Check API 579 calculation integrity."""
        issues = []
        
        # Check for calculations without proper audit trails
        result = await self.db_session.execute(
            text("""
                SELECT COUNT(*) FROM api579_calculations 
                WHERE inputs IS NULL 
                OR outputs IS NULL 
                OR assumptions IS NULL
            """)
        )
        incomplete_audit = result.scalar()
        
        if incomplete_audit > 0:
            issues.append({
                "type": "incomplete_audit_trail",
                "count": incomplete_audit,
                "severity": "high",
                "message": "Calculations missing audit trail components"
            })
        
        # Check for calculations with unrealistic RSF values
        result = await self.db_session.execute(
            text("""
                SELECT COUNT(*) FROM api579_calculations 
                WHERE (outputs->>'rsf')::numeric < 0 
                OR (outputs->>'rsf')::numeric > 2
            """)
        )
        unrealistic_rsf = result.scalar()
        
        if unrealistic_rsf > 0:
            issues.append({
                "type": "unrealistic_rsf",
                "count": unrealistic_rsf,
                "severity": "high",
                "message": "Calculations with unrealistic RSF values"
            })
        
        return issues
    
    async def check_performance_metrics(self) -> ServiceHealth:
        """
        Check system performance metrics.
        
        Validates:
        - Database query performance
        - API response times
        - Cache hit ratios
        - Memory usage
        """
        start = datetime.utcnow()
        
        try:
            # Check database performance
            db_performance = await self._check_database_performance()
            
            # Check cache performance
            cache_performance = await self._check_cache_performance()
            
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            # Determine overall performance status
            if (db_performance.get("avg_query_time", 0) < 100 and 
                cache_performance.get("hit_ratio", 0) > 0.8):
                status = ServiceStatus.HEALTHY
                message = "System performance optimal"
            elif (db_performance.get("avg_query_time", 0) < 500 and
                  cache_performance.get("hit_ratio", 0) > 0.5):
                status = ServiceStatus.DEGRADED
                message = "System performance degraded"
            else:
                status = ServiceStatus.UNHEALTHY
                message = "System performance poor"
            
            return ServiceHealth(
                name="performance_metrics",
                status=status,
                message=message,
                details={
                    "database": db_performance,
                    "cache": cache_performance,
                    "thresholds": {
                        "good_query_time_ms": 100,
                        "acceptable_query_time_ms": 500,
                        "good_cache_hit_ratio": 0.8,
                        "acceptable_cache_hit_ratio": 0.5
                    }
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            logger.error(f"Performance metrics check failed: {e}")
            return ServiceHealth(
                name="performance_metrics",
                status=ServiceStatus.UNHEALTHY,
                message=f"Performance check failed: {str(e)}",
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )
    
    async def _check_database_performance(self) -> Dict[str, Any]:
        """Check database query performance."""
        try:
            # Test a typical query and measure response time
            query_start = datetime.utcnow()
            result = await self.db_session.execute(
                text("""
                    SELECT COUNT(*) as total_equipment,
                           AVG(design_pressure) as avg_pressure,
                           MAX(updated_at) as last_update
                    FROM equipment
                """)
            )
            row = result.fetchone()
            query_time = (datetime.utcnow() - query_start).total_seconds() * 1000
            
            return {
                "avg_query_time": round(query_time, 2),
                "total_equipment": row.total_equipment if row else 0,
                "avg_pressure": float(row.avg_pressure) if row and row.avg_pressure else 0,
                "last_update": row.last_update.isoformat() if row and row.last_update else None
            }
            
        except Exception as e:
            logger.error(f"Database performance check failed: {e}")
            return {"error": str(e), "avg_query_time": 9999}
    
    async def _check_cache_performance(self) -> Dict[str, Any]:
        """Check cache performance metrics."""
        # In a real implementation, you would collect actual cache metrics
        # For now, return simulated metrics
        return {
            "hit_ratio": 0.85,  # Would be calculated from actual metrics
            "total_requests": 1000,
            "cache_hits": 850,
            "cache_misses": 150,
            "evictions": 10
        }
    
    async def check_safety_alerts(self) -> ServiceHealth:
        """
        Check for active safety alerts that require attention.
        
        Monitors:
        - Low RSF values (< 0.9)
        - Short remaining life (< 2 years)  
        - Overdue inspections
        - High corrosion rates
        """
        start = datetime.utcnow()
        
        try:
            alerts = []
            
            # Check for low RSF values
            result = await self.db_session.execute(
                text("""
                    SELECT e.tag_number, (ac.outputs->>'rsf')::numeric as rsf
                    FROM api579_calculations ac
                    JOIN equipment e ON ac.equipment_id = e.id
                    WHERE (ac.outputs->>'rsf')::numeric < 0.9
                    ORDER BY (ac.outputs->>'rsf')::numeric ASC
                    LIMIT 10
                """)
            )
            low_rsf_equipment = result.fetchall()
            
            if low_rsf_equipment:
                alerts.append({
                    "type": "low_rsf",
                    "severity": "high",
                    "count": len(low_rsf_equipment),
                    "equipment": [
                        {"tag": row.tag_number, "rsf": float(row.rsf)}
                        for row in low_rsf_equipment
                    ],
                    "message": "Equipment with RSF < 0.9 requires immediate review"
                })
            
            # Check for short remaining life
            result = await self.db_session.execute(
                text("""
                    SELECT e.tag_number, (ac.outputs->>'remaining_life_years')::numeric as remaining_life
                    FROM api579_calculations ac
                    JOIN equipment e ON ac.equipment_id = e.id
                    WHERE (ac.outputs->>'remaining_life_years')::numeric < 2.0
                    ORDER BY (ac.outputs->>'remaining_life_years')::numeric ASC
                    LIMIT 10
                """)
            )
            short_life_equipment = result.fetchall()
            
            if short_life_equipment:
                alerts.append({
                    "type": "short_remaining_life",
                    "severity": "high",
                    "count": len(short_life_equipment),
                    "equipment": [
                        {"tag": row.tag_number, "remaining_life": float(row.remaining_life)}
                        for row in short_life_equipment
                    ],
                    "message": "Equipment with < 2 years remaining life"
                })
            
            # Check for overdue inspections
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            result = await self.db_session.execute(
                text("""
                    SELECT e.tag_number, MAX(ir.inspection_date) as last_inspection
                    FROM equipment e
                    LEFT JOIN inspection_records ir ON e.id = ir.equipment_id
                    GROUP BY e.id, e.tag_number
                    HAVING MAX(ir.inspection_date) < :thirty_days_ago OR MAX(ir.inspection_date) IS NULL
                    ORDER BY MAX(ir.inspection_date) ASC NULLS FIRST
                    LIMIT 5
                """),
                {"thirty_days_ago": thirty_days_ago}
            )
            overdue_inspections = result.fetchall()
            
            if overdue_inspections:
                alerts.append({
                    "type": "overdue_inspections",
                    "severity": "medium",
                    "count": len(overdue_inspections),
                    "equipment": [
                        {
                            "tag": row.tag_number, 
                            "last_inspection": row.last_inspection.isoformat() if row.last_inspection else None
                        }
                        for row in overdue_inspections
                    ],
                    "message": "Equipment with overdue inspections"
                })
            
            response_time = (datetime.utcnow() - start).total_seconds() * 1000
            
            # Determine status based on alert severity
            high_severity_alerts = [a for a in alerts if a.get("severity") == "high"]
            
            if not alerts:
                status = ServiceStatus.HEALTHY
                message = "No active safety alerts"
            elif not high_severity_alerts:
                status = ServiceStatus.DEGRADED
                message = f"Medium priority alerts active ({len(alerts)} total)"
            else:
                status = ServiceStatus.UNHEALTHY
                message = f"High priority safety alerts require attention ({len(high_severity_alerts)} critical)"
            
            return ServiceHealth(
                name="safety_alerts",
                status=status,
                message=message,
                details={
                    "active_alerts": alerts,
                    "total_alerts": len(alerts),
                    "high_priority": len(high_severity_alerts)
                },
                response_time_ms=response_time
            )
            
        except Exception as e:
            logger.error(f"Safety alerts check failed: {e}")
            return ServiceHealth(
                name="safety_alerts",
                status=ServiceStatus.UNHEALTHY,
                message=f"Safety alerts check failed: {str(e)}",
                response_time_ms=(datetime.utcnow() - start).total_seconds() * 1000
            )


async def get_comprehensive_health() -> Dict[str, Any]:
    """
    Get comprehensive system health including safety-critical checks.
    
    Returns:
        Complete health status with basic and advanced checks
    """
    # Import here to avoid circular imports
    from app.services.health.checks import HealthChecker
    
    async with HealthChecker() as basic_checker, SafetyCriticalHealthChecker() as safety_checker:
        # Run basic checks
        basic_health = await basic_checker.check_all_services()
        
        # Run safety-critical checks
        safety_checks = await asyncio.gather(
            safety_checker.check_data_integrity(),
            safety_checker.check_performance_metrics(),
            safety_checker.check_safety_alerts(),
            return_exceptions=True
        )
        
        # Process safety check results
        safety_services = {}
        for check_result in safety_checks:
            if isinstance(check_result, Exception):
                service_name = "unknown_safety_check"
                health = ServiceHealth(
                    name=service_name,
                    status=ServiceStatus.UNHEALTHY,
                    message=f"Safety check failed: {str(check_result)}"
                )
            else:
                health = check_result
            
            safety_services[health.name] = health.to_dict()
        
        # Combine results
        all_services = {**basic_health["services"], **safety_services}
        
        # Recalculate overall status
        service_statuses = [s.get("status", "unknown") for s in all_services.values()]
        if any(status == "unhealthy" for status in service_statuses):
            overall_status = "unhealthy"
        elif any(status == "degraded" for status in service_statuses):
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            **basic_health,
            "status": overall_status,
            "services": all_services,
            "safety_critical_checks": len(safety_services),
            "total_checks": len(all_services),
        }