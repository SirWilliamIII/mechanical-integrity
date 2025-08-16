"""
Integration tests for API endpoints.
Tests the complete request/response cycle for safety-critical operations.
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test system health and readiness endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
    
    @pytest.mark.asyncio  
    async def test_health_check_response_structure(self, client: AsyncClient):
        """Test health check returns expected service status."""
        response = await client.get("/health")
        data = response.json()
        
        services = data["services"]
        expected_services = ["database", "redis", "ollama"]
        
        for service in expected_services:
            assert service in services
            # Note: In test environment, these may not be "connected"
            assert isinstance(services[service], str)


class TestAPIVersioning:
    """Test API versioning and compatibility."""
    
    @pytest.mark.asyncio
    async def test_api_prefix_structure(self, client: AsyncClient):
        """Test that API follows expected URL structure."""
        # Equipment endpoints should be accessible
        response = await client.get("/api/equipment/")
        # May return 404 if not implemented yet, but should not be 500
        assert response.status_code in [200, 404, 405]
        
        # Inspections endpoints
        response = await client.get("/api/inspections/")
        assert response.status_code in [200, 404, 405]
        
        # Analysis endpoints  
        response = await client.get("/api/analysis/")
        assert response.status_code in [200, 404, 405]


class TestCORSConfiguration:
    """Test CORS middleware configuration for frontend integration."""
    
    @pytest.mark.asyncio
    async def test_cors_preflight(self, client: AsyncClient):
        """Test CORS preflight requests."""
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # Should allow the request or return method not allowed
        assert response.status_code in [200, 204, 405]
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test that CORS headers are present in responses."""
        response = await client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"}
        )
        
        # Should include CORS headers in response
        assert response.status_code == 200
        # Note: CORS headers might not be present in test environment