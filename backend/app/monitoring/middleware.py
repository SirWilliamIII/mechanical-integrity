"""
Monitoring middleware for request tracking and performance measurement.
"""
import time
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.monitoring.logging import correlation_id, set_user_context, clear_user_context
from app.monitoring.metrics import MetricsCollector


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request monitoring and performance tracking.
    
    Adds correlation IDs, tracks request metrics, and sets up logging context.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID for request tracking
        corr_id = str(uuid4())
        correlation_id.set(corr_id)
        
        # Extract endpoint pattern for metrics
        endpoint = self._get_endpoint_pattern(request)
        
        # Record request start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            MetricsCollector.record_request(
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=duration
            )
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = corr_id
            
            return response
            
        except Exception:
            # Record error metrics
            duration = time.time() - start_time
            MetricsCollector.record_request(
                method=request.method,
                endpoint=endpoint,
                status_code=500,
                duration=duration
            )
            
            raise
        finally:
            # Clear user context
            clear_user_context()
    
    def _get_endpoint_pattern(self, request: Request) -> str:
        """
        Extract endpoint pattern for metrics aggregation.
        
        Converts paths with IDs to patterns (e.g., /equipment/123 -> /equipment/{id})
        """
        path = request.url.path
        
        # Common patterns for this API
        patterns = [
            (r'/api/v1/equipment/[^/]+$', '/api/v1/equipment/{id}'),
            (r'/api/v1/equipment/[^/]+/', '/api/v1/equipment/{id}/'),
            (r'/api/v1/inspections/[^/]+$', '/api/v1/inspections/{id}'),
            (r'/api/v1/inspections/[^/]+/', '/api/v1/inspections/{id}/'),
            (r'/api/v1/calculations/[^/]+$', '/api/v1/calculations/{id}'),
            (r'/api/v1/auth/users/[^/]+$', '/api/v1/auth/users/{id}'),
        ]
        
        import re
        for pattern, replacement in patterns:
            if re.match(pattern, path):
                return replacement
        
        return path


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and set user context from JWT tokens.
    
    Sets user information in logging context for audit trails.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract user information if authenticated
        user_info = await self._extract_user_info(request)
        
        if user_info:
            set_user_context(
                user_id=user_info.get("user_id", "unknown"),
                username=user_info.get("username", "unknown"),
                role=user_info.get("role", "unknown")
            )
        
        response = await call_next(request)
        return response
    
    async def _extract_user_info(self, request: Request) -> dict:
        """Extract user information from JWT token."""
        try:
            # Get authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return {}
            
            token = auth_header.split(" ")[1]
            
            # Decode token (simplified - in practice use proper JWT validation)
            from app.auth.security import verify_token
            payload = verify_token(token)
            
            if payload:
                return {
                    "user_id": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role"),
                }
            
        except Exception:
            # If token extraction fails, continue without user context
            pass
        
        return {}


class MetricsEndpointMiddleware(BaseHTTPMiddleware):
    """
    Middleware to expose Prometheus metrics endpoint.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle metrics endpoint
        if request.url.path == "/metrics":
            from fastapi import Response
            from app.monitoring.metrics import MetricsCollector
            
            metrics_data = MetricsCollector.get_metrics_data()
            
            return Response(
                content=metrics_data,
                media_type="text/plain; version=0.0.4; charset=utf-8",
                headers={
                    "Content-Type": "text/plain; version=0.0.4; charset=utf-8"
                }
            )
        
        return await call_next(request)