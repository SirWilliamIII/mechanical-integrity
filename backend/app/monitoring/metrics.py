"""
Prometheus metrics for monitoring API performance and safety-critical operations.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry

# Create custom registry for application metrics
REGISTRY = CollectorRegistry()

# HTTP request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
    registry=REGISTRY
)

# API 579 calculation metrics (safety-critical)
CALCULATION_COUNT = Counter(
    'api579_calculations_total',
    'Total API 579 calculations performed',
    ['calculation_type', 'equipment_type', 'status'],
    registry=REGISTRY
)

CALCULATION_DURATION = Histogram(
    'api579_calculation_duration_seconds',
    'API 579 calculation processing time',
    ['calculation_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=REGISTRY
)

CALCULATION_ERRORS = Counter(
    'api579_calculation_errors_total',
    'Total API 579 calculation errors',
    ['calculation_type', 'error_type'],
    registry=REGISTRY
)

# TODO: [SAFETY_MONITORING] Add critical safety threshold alerts
# Need: Real-time monitoring for RSF < 0.9, remaining life < 2 years
# Integration: PagerDuty/OpsGenie alerts for immediate engineering response
# Context: Safety-critical petroleum equipment requires instant notification
SAFETY_ALERTS = Counter(
    'safety_critical_alerts_total',
    'Critical safety threshold violations',
    ['alert_type', 'equipment_type', 'severity'],
    registry=REGISTRY
)

# TODO: [COMPLIANCE_MONITORING] Track regulatory audit trail completeness
# Gap: No monitoring of audit trail integrity or completeness
# Need: Metrics for missing documentation, incomplete calculations
# Compliance: Required for OSHA PSM and API 579 regulatory reviews
COMPLIANCE_VIOLATIONS = Counter(
    'compliance_violations_total',
    'Regulatory compliance violations detected',
    ['violation_type', 'severity'],
    registry=REGISTRY
)

# Equipment and inspection metrics
EQUIPMENT_COUNT = Gauge(
    'equipment_registered_total',
    'Total number of registered equipment',
    ['equipment_type', 'status'],
    registry=REGISTRY
)

INSPECTION_COUNT = Counter(
    'inspections_performed_total',
    'Total inspections performed',
    ['inspection_type', 'equipment_type'],
    registry=REGISTRY
)

THICKNESS_MEASUREMENTS = Histogram(
    'thickness_measurements_inches',
    'Distribution of thickness measurements',
    ['equipment_id', 'location'],
    buckets=[0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
    registry=REGISTRY
)

# Document processing metrics
DOCUMENT_PROCESSING = Counter(
    'document_processing_total',
    'Total documents processed',
    ['document_type', 'processing_method', 'status'],
    registry=REGISTRY
)

OCR_PROCESSING_TIME = Histogram(
    'ocr_processing_duration_seconds',
    'OCR processing time for documents',
    ['document_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=REGISTRY
)

# System health metrics
DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Active database connections',
    registry=REGISTRY
)

REDIS_CONNECTIONS = Gauge(
    'redis_connections_active',
    'Active Redis connections',
    registry=REGISTRY
)

OLLAMA_REQUESTS = Counter(
    'ollama_requests_total',
    'Total requests to Ollama LLM service',
    ['model', 'status'],
    registry=REGISTRY
)

# Safety and compliance metrics
RSF_VALUES = Histogram(
    'remaining_strength_factor',
    'Distribution of Remaining Strength Factor values',
    ['equipment_type'],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0, 1.1, 1.2],
    registry=REGISTRY
)

REMAINING_LIFE = Histogram(
    'remaining_life_years',
    'Distribution of remaining life estimates',
    ['equipment_type'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0],
    registry=REGISTRY
)

SAFETY_ALERTS = Counter(
    'safety_alerts_total',
    'Safety alerts triggered by system',
    ['alert_type', 'severity', 'equipment_type'],
    registry=REGISTRY
)

# Authentication metrics
LOGIN_ATTEMPTS = Counter(
    'login_attempts_total',
    'Total login attempts',
    ['status', 'user_role'],
    registry=REGISTRY
)

ACTIVE_SESSIONS = Gauge(
    'active_user_sessions',
    'Currently active user sessions',
    ['user_role'],
    registry=REGISTRY
)

# Error tracking
APPLICATION_ERRORS = Counter(
    'application_errors_total',
    'Total application errors',
    ['error_type', 'module', 'severity'],
    registry=REGISTRY
)

# Cache performance metrics
CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'namespace', 'status'],
    registry=REGISTRY
)

CACHE_HIT_RATIO = Gauge(
    'cache_hit_ratio',
    'Cache hit ratio by namespace',
    ['namespace'],
    registry=REGISTRY
)

# Business metrics
EQUIPMENT_CRITICALITY = Gauge(
    'equipment_by_criticality',
    'Equipment count by criticality level',
    ['criticality_level'],
    registry=REGISTRY
)

OVERDUE_INSPECTIONS = Gauge(
    'overdue_inspections_count',
    'Number of overdue inspections',
    ['equipment_type'],
    registry=REGISTRY
)


class MetricsCollector:
    """Utility class for collecting and recording metrics."""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    @staticmethod
    def record_calculation(
        calc_type: str, 
        equipment_type: str, 
        duration: float, 
        status: str = "success"
    ):
        """Record API 579 calculation metrics."""
        CALCULATION_COUNT.labels(
            calculation_type=calc_type,
            equipment_type=equipment_type,
            status=status
        ).inc()
        
        CALCULATION_DURATION.labels(
            calculation_type=calc_type
        ).observe(duration)
    
    @staticmethod
    def record_calculation_error(calc_type: str, error_type: str):
        """Record calculation error."""
        CALCULATION_ERRORS.labels(
            calculation_type=calc_type,
            error_type=error_type
        ).inc()
    
    @staticmethod
    def record_thickness_measurement(equipment_id: str, location: str, thickness: float):
        """Record thickness measurement for distribution analysis."""
        THICKNESS_MEASUREMENTS.labels(
            equipment_id=equipment_id,
            location=location
        ).observe(thickness)
    
    @staticmethod
    def record_rsf_value(equipment_type: str, rsf_value: float):
        """Record Remaining Strength Factor value."""
        RSF_VALUES.labels(equipment_type=equipment_type).observe(rsf_value)
        
        # Trigger safety alert if RSF is below threshold
        if rsf_value < 0.9:
            SAFETY_ALERTS.labels(
                alert_type="low_rsf",
                severity="high",
                equipment_type=equipment_type
            ).inc()
    
    @staticmethod
    def record_remaining_life(equipment_type: str, years: float):
        """Record remaining life estimate."""
        REMAINING_LIFE.labels(equipment_type=equipment_type).observe(years)
        
        # Trigger safety alert if remaining life is low
        if years < 2.0:
            SAFETY_ALERTS.labels(
                alert_type="low_remaining_life",
                severity="high",
                equipment_type=equipment_type
            ).inc()
    
    @staticmethod
    def record_login_attempt(status: str, user_role: str):
        """Record login attempt."""
        LOGIN_ATTEMPTS.labels(
            status=status,
            user_role=user_role
        ).inc()
    
    @staticmethod
    def record_document_processing(
        doc_type: str, 
        method: str, 
        status: str, 
        duration: float = None
    ):
        """Record document processing metrics."""
        DOCUMENT_PROCESSING.labels(
            document_type=doc_type,
            processing_method=method,
            status=status
        ).inc()
        
        if duration and method == "ocr":
            OCR_PROCESSING_TIME.labels(
                document_type=doc_type
            ).observe(duration)
    
    @staticmethod
    def update_system_gauges(db_connections: int, redis_connections: int):
        """Update system health gauges."""
        DATABASE_CONNECTIONS.set(db_connections)
        REDIS_CONNECTIONS.set(redis_connections)
    
    @staticmethod
    def record_cache_operation(operation: str, namespace: str, status: str = "success", count: int = 1):
        """Record cache operation metrics."""
        CACHE_OPERATIONS.labels(
            operation=operation,
            namespace=namespace,
            status=status
        ).inc(count)
    
    @staticmethod
    def update_cache_hit_ratio(namespace: str, hit_ratio: float):
        """Update cache hit ratio gauge."""
        CACHE_HIT_RATIO.labels(namespace=namespace).set(hit_ratio)
    
    @staticmethod
    def get_metrics_data() -> str:
        """Get Prometheus metrics data."""
        return generate_latest(REGISTRY).decode('utf-8')