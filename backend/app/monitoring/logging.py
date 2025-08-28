"""
Structured logging configuration for production deployment.

Implements JSON logging with correlation IDs and audit trails
for safety-critical mechanical integrity system.
"""
import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

from core.config import settings

# Context variable for request correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('user_context', default=None)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Includes correlation ID, user context, and safety-critical metadata.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            log_data["correlation_id"] = corr_id
        
        # Add user context if available
        user_ctx = user_context.get()
        if user_ctx:
            log_data["user"] = user_ctx
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'message'
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        # Add safety-critical metadata
        if hasattr(record, 'equipment_id'):
            log_data["equipment_id"] = record.equipment_id
        
        if hasattr(record, 'calculation_type'):
            log_data["calculation_type"] = record.calculation_type
            log_data["safety_critical"] = True
        
        if hasattr(record, 'audit_event'):
            log_data["audit_event"] = record.audit_event
            log_data["audit_trail"] = True
        
        return json.dumps(log_data, default=str, separators=(',', ':'))


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for development console output.
    """
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console output."""
        formatted = super().format(record)
        
        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            formatted = f"[{corr_id[:8]}] {formatted}"
        
        # Add user context if available
        user_ctx = user_context.get()
        if user_ctx and user_ctx.get('username'):
            formatted = f"[{user_ctx['username']}] {formatted}"
        
        return formatted


def setup_logging():
    """
    Configure structured logging for the application.
    """
    # Determine log format based on environment
    if settings.is_production:
        formatter = StructuredFormatter()
        log_level = logging.INFO
    else:
        formatter = ConsoleFormatter()
        log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    loggers = [
        'app',
        'uvicorn.access',
        'uvicorn.error',
        'sqlalchemy.engine',
        'alembic',
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log startup information
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "environment": settings.ENVIRONMENT,
            "log_format": "json" if settings.is_production else "console",
            "log_level": log_level,
        }
    )


class AuditLogger:
    """
    Specialized logger for audit trail and compliance logging.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    def log_calculation(
        self,
        calculation_type: str,
        equipment_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        user_id: Optional[str] = None,
        confidence: Optional[float] = None,
    ):
        """Log API 579 calculation for audit trail."""
        self.logger.info(
            f"API 579 calculation performed: {calculation_type}",
            extra={
                "audit_event": "api579_calculation",
                "calculation_type": calculation_type,
                "equipment_id": equipment_id,
                "inputs": inputs,
                "outputs": outputs,
                "user_id": user_id,
                "confidence": confidence,
                "safety_critical": True,
            }
        )
    
    def log_inspection_data(
        self,
        equipment_id: str,
        inspection_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ai_processed: bool = False,
    ):
        """Log inspection data entry for audit trail."""
        self.logger.info(
            f"Inspection data recorded for equipment {equipment_id}",
            extra={
                "audit_event": "inspection_data_entry",
                "equipment_id": equipment_id,
                "inspection_data": inspection_data,
                "user_id": user_id,
                "ai_processed": ai_processed,
                "safety_critical": True,
            }
        )
    
    def log_user_action(
        self,
        action: str,
        user_id: str,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log user action for audit trail."""
        self.logger.info(
            f"User action: {action}",
            extra={
                "audit_event": "user_action",
                "action": action,
                "user_id": user_id,
                "resource": resource,
                "details": details or {},
            }
        )
    
    def log_system_event(
        self,
        event: str,
        severity: str = "info",
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log system event for monitoring."""
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method(
            f"System event: {event}",
            extra={
                "audit_event": "system_event",
                "event": event,
                "severity": severity,
                "details": details or {},
            }
        )


def get_correlation_id() -> str:
    """Get or create correlation ID for request tracking."""
    corr_id = correlation_id.get()
    if not corr_id:
        corr_id = str(uuid.uuid4())
        correlation_id.set(corr_id)
    return corr_id


def set_user_context(user_id: str, username: str, role: str):
    """Set user context for logging."""
    user_context.set({
        "user_id": user_id,
        "username": username,
        "role": role,
    })


def clear_user_context():
    """Clear user context."""
    user_context.set(None)


# Create global audit logger instance
audit_logger = AuditLogger()

# Export commonly used functions
__all__ = [
    'setup_logging',
    'AuditLogger',
    'audit_logger',
    'get_correlation_id',
    'set_user_context',
    'clear_user_context',
]