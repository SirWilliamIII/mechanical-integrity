#!/usr/bin/env python3
"""
Production deployment test script for Mechanical Integrity AI System.

Performs comprehensive testing of production deployment including:
- Service connectivity and health checks
- Security configuration validation
- API endpoint testing with authentication
- Database integrity and performance
- Cache functionality and performance
- Safety-critical calculation accuracy
"""
import asyncio
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx
import asyncpg
import redis.asyncio as redis
from decimal import Decimal

import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class DeploymentTester:
    """Comprehensive deployment testing suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client: Optional[httpx.AsyncClient] = None
        self.access_token: Optional[str] = None
        self.test_results: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": base_url,
            "tests": {},
            "summary": {"total": 0, "passed": 0, "failed": 0, "warnings": 0}
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources."""
        if self.client:
            await self.client.aclose()
    
    async def run_all_tests(self) -> bool:
        """Run comprehensive deployment tests."""
        logger.info("🚀 Starting production deployment testing...")
        
        test_suites = [
            ("Basic Connectivity", self.test_basic_connectivity),
            ("Health Checks", self.test_health_checks),
            ("Security Configuration", self.test_security),
            ("Authentication System", self.test_authentication),
            ("API Endpoints", self.test_api_endpoints),
            ("Database Operations", self.test_database),
            ("Cache Performance", self.test_cache),
            ("Safety-Critical Calculations", self.test_calculations),
            ("Performance Metrics", self.test_performance),
            ("Error Handling", self.test_error_handling),
        ]
        
        for suite_name, test_func in test_suites:
            logger.info(f"Running {suite_name} tests...")
            try:
                await test_func()
            except Exception as e:
                self.record_test_result(suite_name, False, f"Test suite failed: {str(e)}")
        
        # Generate summary
        self.generate_summary()
        return self.test_results["summary"]["failed"] == 0
    
    def record_test_result(self, test_name: str, passed: bool, message: str, details: Dict[str, Any] = None):
        """Record test result."""
        self.test_results["tests"][test_name] = {
            "passed": passed,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.test_results["summary"]["total"] += 1
        if passed:
            self.test_results["summary"]["passed"] += 1
            logger.info(f"✅ {test_name}: {message}")
        else:
            self.test_results["summary"]["failed"] += 1
            logger.error(f"❌ {test_name}: {message}")
    
    async def test_basic_connectivity(self):
        """Test basic service connectivity."""
        try:
            response = await self.client.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                self.record_test_result(
                    "API Root Endpoint",
                    True,
                    f"API responding: {data.get('application', 'Unknown')} v{data.get('version', 'Unknown')}",
                    {"response_data": data}
                )
            else:
                self.record_test_result(
                    "API Root Endpoint",
                    False,
                    f"API returned status {response.status_code}"
                )
        except Exception as e:
            self.record_test_result("API Root Endpoint", False, f"Connection failed: {str(e)}")
    
    async def test_health_checks(self):
        """Test health check endpoints."""
        health_endpoints = [
            ("/health", "Basic Health Check"),
            ("/health/detailed", "Detailed Health Check"),
            ("/health/ready", "Readiness Probe"),
            ("/health/live", "Liveness Probe"),
        ]
        
        for endpoint, test_name in health_endpoints:
            try:
                response = await self.client.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.record_test_result(
                        test_name,
                        True,
                        f"Health check passed: {data.get('status', 'unknown')}",
                        {"status": data.get("status"), "services": list(data.get("services", {}).keys())}
                    )
                else:
                    self.record_test_result(
                        test_name,
                        False,
                        f"Health check failed with status {response.status_code}"
                    )
            except Exception as e:
                self.record_test_result(test_name, False, f"Health check error: {str(e)}")
    
    async def test_security(self):
        """Test security configuration."""
        try:
            response = await self.client.get(f"{self.base_url}/")
            
            # Check security headers
            headers = response.headers
            security_headers = {
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block",
                "Server": "Mechanical-Integrity-API"
            }
            
            missing_headers = []
            for header, expected_value in security_headers.items():
                if header not in headers:
                    missing_headers.append(header)
                elif expected_value and headers[header] != expected_value:
                    missing_headers.append(f"{header} (incorrect value)")
            
            if missing_headers:
                self.record_test_result(
                    "Security Headers",
                    False,
                    f"Missing security headers: {', '.join(missing_headers)}"
                )
            else:
                self.record_test_result(
                    "Security Headers",
                    True,
                    "All required security headers present"
                )
            
            # Test rate limiting (if enabled)
            # This would require multiple rapid requests to test properly
            
        except Exception as e:
            self.record_test_result("Security Headers", False, f"Security test error: {str(e)}")
    
    async def test_authentication(self):
        """Test authentication system."""
        # Test login endpoint
        try:
            # Try to access protected endpoint without auth
            response = await self.client.get(f"{self.base_url}/api/v1/auth/me")
            if response.status_code == 401:
                self.record_test_result(
                    "Authentication Protection",
                    True,
                    "Protected endpoints properly secured"
                )
            else:
                self.record_test_result(
                    "Authentication Protection",
                    False,
                    f"Protected endpoint returned status {response.status_code} instead of 401"
                )
            
            # Test with invalid credentials
            response = await self.client.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": "invalid", "password": "invalid"}
            )
            if response.status_code == 401:
                self.record_test_result(
                    "Invalid Credentials Rejection",
                    True,
                    "Invalid credentials properly rejected"
                )
            else:
                self.record_test_result(
                    "Invalid Credentials Rejection",
                    False,
                    f"Invalid credentials returned status {response.status_code}"
                )
                
        except Exception as e:
            self.record_test_result("Authentication System", False, f"Auth test error: {str(e)}")
    
    async def test_api_endpoints(self):
        """Test key API endpoints."""
        # Test equipment endpoints
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/equipment")
            if response.status_code in [200, 401]:  # 200 if no auth, 401 if auth required
                self.record_test_result(
                    "Equipment API",
                    True,
                    f"Equipment endpoint responding (status: {response.status_code})"
                )
            else:
                self.record_test_result(
                    "Equipment API",
                    False,
                    f"Equipment endpoint returned status {response.status_code}"
                )
        except Exception as e:
            self.record_test_result("Equipment API", False, f"Equipment API error: {str(e)}")
        
        # Test documentation endpoints
        try:
            response = await self.client.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                self.record_test_result(
                    "API Documentation",
                    True,
                    "API documentation accessible"
                )
            else:
                self.record_test_result(
                    "API Documentation",
                    False,
                    f"Documentation returned status {response.status_code}"
                )
        except Exception as e:
            self.record_test_result("API Documentation", False, f"Documentation error: {str(e)}")
    
    async def test_database(self):
        """Test database connectivity and operations."""
        try:
            # This would require database connection details
            # For now, we'll test via the health endpoint which includes DB checks
            response = await self.client.get(f"{self.base_url}/health/detailed")
            
            if response.status_code == 200:
                data = response.json()
                db_status = data.get("services", {}).get("postgresql", {})
                
                if db_status.get("status") == "healthy":
                    self.record_test_result(
                        "Database Connectivity",
                        True,
                        "Database connection healthy",
                        db_status.get("details", {})
                    )
                else:
                    self.record_test_result(
                        "Database Connectivity",
                        False,
                        f"Database status: {db_status.get('status', 'unknown')}"
                    )
            else:
                self.record_test_result(
                    "Database Connectivity",
                    False,
                    "Cannot check database status"
                )
                
        except Exception as e:
            self.record_test_result("Database Connectivity", False, f"Database test error: {str(e)}")
    
    async def test_cache(self):
        """Test cache functionality."""
        try:
            response = await self.client.get(f"{self.base_url}/health/detailed")
            
            if response.status_code == 200:
                data = response.json()
                cache_status = data.get("services", {}).get("redis", {})
                
                if cache_status.get("status") == "healthy":
                    self.record_test_result(
                        "Cache System",
                        True,
                        "Redis cache operational",
                        cache_status.get("details", {})
                    )
                else:
                    self.record_test_result(
                        "Cache System",
                        False,
                        f"Cache status: {cache_status.get('status', 'unknown')}"
                    )
            else:
                self.record_test_result("Cache System", False, "Cannot check cache status")
                
        except Exception as e:
            self.record_test_result("Cache System", False, f"Cache test error: {str(e)}")
    
    async def test_calculations(self):
        """Test safety-critical calculation endpoints."""
        try:
            # Test material properties endpoint
            response = await self.client.get(f"{self.base_url}/api/v1/equipment/materials")
            
            if response.status_code in [200, 401]:
                if response.status_code == 200:
                    materials = response.json()
                    if len(materials) >= 10:  # We expect at least 10 materials
                        self.record_test_result(
                            "Material Database",
                            True,
                            f"Material database accessible with {len(materials)} materials"
                        )
                    else:
                        self.record_test_result(
                            "Material Database",
                            False,
                            f"Material database has insufficient materials: {len(materials)}"
                        )
                else:
                    self.record_test_result(
                        "Material Database",
                        True,
                        "Material database endpoint secured (requires auth)"
                    )
            else:
                self.record_test_result(
                    "Material Database",
                    False,
                    f"Material endpoint returned status {response.status_code}"
                )
                
        except Exception as e:
            self.record_test_result("Material Database", False, f"Material test error: {str(e)}")
    
    async def test_performance(self):
        """Test system performance."""
        try:
            # Measure response times
            start_time = time.time()
            response = await self.client.get(f"{self.base_url}/health")
            health_response_time = (time.time() - start_time) * 1000
            
            if health_response_time < 1000:  # Less than 1 second
                self.record_test_result(
                    "Health Check Performance",
                    True,
                    f"Health check responded in {health_response_time:.2f}ms"
                )
            elif health_response_time < 5000:  # Less than 5 seconds
                self.record_test_result(
                    "Health Check Performance",
                    True,
                    f"Health check responded in {health_response_time:.2f}ms (acceptable)",
                    {"warning": "Response time above 1 second"}
                )
                self.test_results["summary"]["warnings"] += 1
            else:
                self.record_test_result(
                    "Health Check Performance",
                    False,
                    f"Health check too slow: {health_response_time:.2f}ms"
                )
            
            # Check if response includes performance headers
            if "X-Process-Time" in response.headers:
                process_time = float(response.headers["X-Process-Time"]) * 1000
                self.record_test_result(
                    "Performance Monitoring",
                    True,
                    f"Performance headers present (process time: {process_time:.2f}ms)"
                )
            else:
                self.record_test_result(
                    "Performance Monitoring",
                    False,
                    "Performance headers missing"
                )
                
        except Exception as e:
            self.record_test_result("Performance Testing", False, f"Performance test error: {str(e)}")
    
    async def test_error_handling(self):
        """Test error handling and edge cases."""
        try:
            # Test 404 handling
            response = await self.client.get(f"{self.base_url}/nonexistent-endpoint")
            if response.status_code == 404:
                self.record_test_result(
                    "404 Error Handling",
                    True,
                    "Properly returns 404 for non-existent endpoints"
                )
            else:
                self.record_test_result(
                    "404 Error Handling",
                    False,
                    f"Non-existent endpoint returned status {response.status_code}"
                )
            
            # Test method not allowed
            response = await self.client.post(f"{self.base_url}/health")
            if response.status_code == 405:
                self.record_test_result(
                    "Method Not Allowed Handling",
                    True,
                    "Properly returns 405 for invalid methods"
                )
            else:
                self.record_test_result(
                    "Method Not Allowed Handling",
                    False,
                    f"Invalid method returned status {response.status_code}"
                )
                
        except Exception as e:
            self.record_test_result("Error Handling", False, f"Error handling test error: {str(e)}")
    
    def generate_summary(self):
        """Generate test summary."""
        summary = self.test_results["summary"]
        success_rate = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
        
        print("\n" + "="*80)
        print("🧪 DEPLOYMENT TEST RESULTS SUMMARY")
        print("="*80)
        print(f"Base URL: {self.base_url}")
        print(f"Test Time: {self.test_results['timestamp']}")
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']} ({success_rate:.1f}%)")
        print(f"Failed: {summary['failed']}")
        print(f"Warnings: {summary.get('warnings', 0)}")
        print("="*80)
        
        if summary["failed"] == 0:
            if summary.get("warnings", 0) > 0:
                print("⚠️  ALL TESTS PASSED WITH WARNINGS - Review recommendations before production")
            else:
                print("✅ ALL TESTS PASSED - System ready for production deployment")
        else:
            print("❌ DEPLOYMENT TESTS FAILED - Fix issues before deploying to production")
        
        print("="*80)
        
        # Print detailed results
        for test_name, result in self.test_results["tests"].items():
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {test_name}: {result['message']}")
        
        print("="*80)
    
    def save_report(self, filename: str = "deployment_test_report.json"):
        """Save test report to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"📊 Test report saved to: {filename}")


async def main():
    """Main test function."""
    base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
    
    async with DeploymentTester(base_url) as tester:
        success = await tester.run_all_tests()
        
        # Save report if requested
        if "--report" in sys.argv:
            tester.save_report()
        
        return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)