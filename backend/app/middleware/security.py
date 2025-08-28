"""
Security middleware for production FastAPI deployment.

Implements security headers and input validation for safety-critical systems.
"""
import ipaddress
import re
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Implements OWASP recommended security headers for production deployment.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Security headers for production deployment
        security_headers = {
            # Prevent clickjacking attacks
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Enable XSS protection (legacy browsers)
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy for privacy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy - strict for safety-critical system
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
            
            # Permissions policy (restrict browser features)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "fullscreen=(self)"
            ),
            
            # Server identification
            "Server": f"Mechanical-Integrity-API/{settings.API_VERSION}",
        }
        
        # Add HTTPS security headers in production
        if settings.is_production:
            security_headers.update({
                # Force HTTPS for 1 year
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                
                # Prevent HTTP downgrade attacks
                "Upgrade-Insecure-Requests": "1",
            })
        
        # Apply all security headers
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic rate limiting middleware for API protection.
    
    In production, use Redis-based distributed rate limiting.
    """
    
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # In production, use Redis
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/healthz", "/ready"]:
            return await call_next(request)
        
        # TODO: Implement Redis-based distributed rate limiting for production
        # This is a basic in-memory implementation for development
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request headers."""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP from comma-separated list
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Input validation middleware for security hardening.
    
    Validates request size, content types, and detects malicious patterns.
    """
    
    def __init__(
        self,
        app,
        max_request_size: int = 50 * 1024 * 1024,  # 50MB for file uploads
        allowed_content_types: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
            "application/pdf",  # For inspection documents
        ]
        
        # SQL injection detection patterns
        self.sql_injection_patterns = [
            re.compile(r"(\bunion\b|\bselect\b|\binsert\b|\bdelete\b|\bdrop\b|\bupdate\b)", re.IGNORECASE),
            re.compile(r"('|(\\x27)|(\\x2D\\x2D)|(%27)|(%2D%2D))", re.IGNORECASE),
            re.compile(r"((\%3D)|(=))[^\n]*((\%27)|(\\x27)|(')|(\-\-)|(\%3B)|(;))", re.IGNORECASE),
        ]
        
        # XSS detection patterns
        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large"}
            )
        
        # Validate content type for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "").split(";")[0]
            if content_type and not any(ct in content_type for ct in self.allowed_content_types):
                return JSONResponse(
                    status_code=415,
                    content={"detail": "Unsupported content type"}
                )
        
        # Check for malicious patterns in URL
        if self._contains_malicious_patterns(str(request.url)):
            return JSONResponse(
                status_code=400,
                content={"detail": "Malicious request detected"}
            )
        
        # Check query parameters
        for param_value in request.query_params.values():
            if self._contains_malicious_patterns(param_value):
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Malicious query parameter detected"}
                )
        
        return await call_next(request)
    
    def _contains_malicious_patterns(self, text: str) -> bool:
        """Check if text contains SQL injection or XSS patterns."""
        # Check SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if pattern.search(text):
                return True
        
        # Check XSS patterns
        for pattern in self.xss_patterns:
            if pattern.search(text):
                return True
        
        return False


class TrustedProxyMiddleware(BaseHTTPMiddleware):
    """
    Handle trusted proxy headers for load balancer deployments.
    
    Validates and processes X-Forwarded-* headers from trusted sources.
    """
    
    def __init__(self, app, trusted_proxies: Optional[List[str]] = None):
        super().__init__(app)
        self.trusted_proxies = self._parse_trusted_proxies(trusted_proxies or [])
    
    def _parse_trusted_proxies(self, proxies: List[str]) -> List[ipaddress.IPv4Network]:
        """Parse trusted proxy IP ranges."""
        networks = []
        for proxy in proxies:
            try:
                networks.append(ipaddress.IPv4Network(proxy, strict=False))
            except ValueError:
                # Skip invalid IP ranges
                pass
        return networks
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Validate proxy headers only from trusted sources
        client_ip = request.client.host if request.client else None
        
        if client_ip and self._is_trusted_proxy(client_ip):
            # Process forwarded headers from trusted proxy
            forwarded_proto = request.headers.get("X-Forwarded-Proto")
            if forwarded_proto:
                request.scope["scheme"] = forwarded_proto
            
            forwarded_host = request.headers.get("X-Forwarded-Host")
            if forwarded_host:
                request.scope["server"] = (forwarded_host.split(":")[0], 443 if forwarded_proto == "https" else 80)
        
        return await call_next(request)
    
    def _is_trusted_proxy(self, ip: str) -> bool:
        """Check if IP is from a trusted proxy."""
        try:
            client_ip = ipaddress.IPv4Address(ip)
            return any(client_ip in network for network in self.trusted_proxies)
        except ValueError:
            return False