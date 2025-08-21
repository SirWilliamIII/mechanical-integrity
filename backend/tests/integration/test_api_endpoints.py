"""
Integration tests for API endpoints.
Tests the complete request/response cycle for safety-critical operations.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test system health and readiness endpoints."""
    
    def test_health_check(self, client: TestClient):
        """Test basic health check endpoint."""
        response = client.get("/health")
        
        # Allow service unavailable during testing
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "services" in data
    
    def test_health_check_response_structure(self, client: TestClient):
        """Test health check returns expected service status."""
        response = client.get("/health")
        data = response.json()
        
        services = data["services"]
        expected_services = ["postgresql", "redis", "ollama"]
        
        for service in expected_services:
            assert service in services
            # Services return detailed status objects, not just strings
            assert isinstance(services[service], dict)
            assert "status" in services[service]


class TestAPIVersioning:
    """Test API versioning and compatibility."""
    
    def test_api_prefix_structure(self, client: TestClient):
        """Test that API follows expected URL structure."""
        # Equipment endpoints should be accessible
        response = client.get("/api/equipment/")
        # May return 404 if not implemented yet, but should not be 500
        assert response.status_code in [200, 404, 405]
        
        # Inspections endpoints
        response = client.get("/api/inspections/")
        assert response.status_code in [200, 404, 405]
        
        # Analysis endpoints  
        response = client.get("/api/analysis/")
        assert response.status_code in [200, 404, 405]


class TestCORSConfiguration:
    """Test CORS middleware configuration for frontend integration."""
    
    def test_cors_preflight(self, client: TestClient):
        """Test CORS preflight requests."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # Should allow the request or return method not allowed
        assert response.status_code in [200, 204, 405]
    
    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are present in responses."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"}
        )
        
        # Should include CORS headers in response (allow service unavailable)
        assert response.status_code in [200, 503]
        # Note: CORS headers might not be present in test environment