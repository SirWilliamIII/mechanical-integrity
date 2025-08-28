#!/usr/bin/env python3
"""
Configuration validation script for Mechanical Integrity AI System.

Validates environment configuration before deployment to catch
configuration errors early and ensure compliance requirements.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from core.config import settings, Settings, ValidationError
from pydantic import Field
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ConfigValidator:
    """Configuration validator for deployment readiness."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        logger.info("🔍 Starting configuration validation...")
        
        # Core validation checks
        self.validate_basic_config()
        self.validate_security_config()
        self.validate_database_config()
        self.validate_production_readiness()
        self.validate_compliance_requirements()
        self.validate_feature_flags()
        
        # Print results
        self.print_results()
        
        return len(self.errors) == 0
    
    def validate_basic_config(self):
        """Validate basic configuration settings."""
        logger.info("Validating basic configuration...")
        
        try:
            # Test settings loading
            test_settings = Settings()
            self.info.append(f"✅ Configuration loaded successfully: {test_settings.PROJECT_NAME} v{test_settings.API_VERSION}")
            
            # Check environment
            if test_settings.ENVIRONMENT not in ["development", "testing", "production"]:
                self.errors.append("❌ ENVIRONMENT must be one of: development, testing, production")
            else:
                self.info.append(f"✅ Environment: {test_settings.ENVIRONMENT}")
            
            # Check debug mode
            if test_settings.is_production and test_settings.DEBUG:
                self.errors.append("❌ DEBUG mode cannot be enabled in production")
            
        except ValidationError as e:
            self.errors.append(f"❌ Configuration validation failed: {e}")
        except Exception as e:
            self.errors.append(f"❌ Configuration loading failed: {e}")
    
    def validate_security_config(self):
        """Validate security configuration."""
        logger.info("Validating security configuration...")
        
        # Check SECRET_KEY
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
            self.errors.append("❌ SECRET_KEY must be at least 32 characters long")
        elif settings.SECRET_KEY == "your-super-secret-key-here-replace-with-strong-random-value":
            self.errors.append("❌ SECRET_KEY is using default value - must be changed")
        else:
            self.info.append("✅ SECRET_KEY is properly configured")
        
        # Check JWT token expiration
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES < 5:
            self.warnings.append("⚠️  Very short JWT token expiration (< 5 minutes)")
        elif settings.ACCESS_TOKEN_EXPIRE_MINUTES > 1440:  # 24 hours
            self.warnings.append("⚠️  Very long JWT token expiration (> 24 hours)")
        else:
            self.info.append(f"✅ JWT token expiration: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
        
        # Check CORS origins
        if not settings.BACKEND_CORS_ORIGINS:
            self.warnings.append("⚠️  No CORS origins configured")
        else:
            self.info.append(f"✅ CORS origins: {len(settings.BACKEND_CORS_ORIGINS)} configured")
        
        # Check SSL configuration in production
        if settings.is_production:
            if not settings.SSL_ENABLED:
                self.warnings.append("⚠️  SSL not enabled in production")
            elif settings.SSL_ENABLED and (not settings.SSL_CERT_PATH or not settings.SSL_KEY_PATH):
                self.errors.append("❌ SSL enabled but certificate paths not configured")
            else:
                self.info.append("✅ SSL properly configured for production")
    
    def validate_database_config(self):
        """Validate database configuration."""
        logger.info("Validating database configuration...")
        
        # Check database credentials
        if not settings.POSTGRES_PASSWORD or settings.POSTGRES_PASSWORD == "postgres":
            if settings.is_production:
                self.errors.append("❌ Production database password is weak or default")
            else:
                self.warnings.append("⚠️  Using default database password")
        else:
            self.info.append("✅ Database password configured")
        
        # Check database connection parameters
        if settings.DB_POOL_SIZE < 5:
            self.warnings.append("⚠️  Database pool size is very small")
        elif settings.DB_POOL_SIZE > 100:
            self.warnings.append("⚠️  Database pool size is very large")
        else:
            self.info.append(f"✅ Database pool size: {settings.DB_POOL_SIZE}")
        
        # Test database URL construction
        try:
            db_url = settings.get_database_url()
            self.info.append("✅ Database URL construction successful")
        except Exception as e:
            self.errors.append(f"❌ Database URL construction failed: {e}")
    
    def validate_production_readiness(self):
        """Validate production deployment readiness."""
        logger.info("Validating production readiness...")
        
        if not settings.is_production:
            self.info.append("ℹ️  Skipping production checks (not production environment)")
            return
        
        # Check monitoring configuration
        if not settings.PROMETHEUS_ENABLED:
            self.warnings.append("⚠️  Prometheus monitoring disabled in production")
        else:
            self.info.append("✅ Prometheus monitoring enabled")
        
        # Check audit logging
        if not settings.AUDIT_LOG_ENABLED:
            self.errors.append("❌ Audit logging must be enabled in production")
        else:
            self.info.append(f"✅ Audit logging enabled (retention: {settings.AUDIT_LOG_RETENTION_DAYS} days)")
        
        # Check backup configuration
        if not settings.BACKUP_ENABLED:
            self.warnings.append("⚠️  Automated backups not configured")
        else:
            self.info.append(f"✅ Backups enabled (schedule: {settings.BACKUP_SCHEDULE})")
        
        # Check rate limiting
        if not settings.RATE_LIMIT_ENABLED:
            self.warnings.append("⚠️  Rate limiting disabled")
        else:
            self.info.append(f"✅ Rate limiting enabled ({settings.RATE_LIMIT_REQUESTS_PER_MINUTE} req/min)")
        
        # Check trusted proxy configuration
        if not settings.TRUSTED_PROXIES:
            self.warnings.append("⚠️  No trusted proxies configured")
        else:
            self.info.append(f"✅ Trusted proxies: {len(settings.TRUSTED_PROXIES)}")
    
    def validate_compliance_requirements(self):
        """Validate compliance and regulatory requirements."""
        logger.info("Validating compliance requirements...")
        
        # Check compliance mode
        if settings.is_production and settings.COMPLIANCE_MODE != "strict":
            self.errors.append("❌ COMPLIANCE_MODE must be 'strict' in production")
        else:
            self.info.append(f"✅ Compliance mode: {settings.COMPLIANCE_MODE}")
        
        # Check API 579 safety factors
        if settings.API579_DEFAULT_SAFETY_FACTOR < 0.8 or settings.API579_DEFAULT_SAFETY_FACTOR > 1.0:
            self.errors.append("❌ API 579 safety factor outside acceptable range (0.8-1.0)")
        else:
            self.info.append(f"✅ API 579 safety factor: {settings.API579_DEFAULT_SAFETY_FACTOR}")
        
        # Check corrosion rate
        if settings.API579_DEFAULT_CORROSION_RATE <= 0 or settings.API579_DEFAULT_CORROSION_RATE > 0.1:
            self.warnings.append("⚠️  API 579 corrosion rate outside typical range")
        else:
            self.info.append(f"✅ API 579 corrosion rate: {settings.API579_DEFAULT_CORROSION_RATE} in/yr")
    
    def validate_feature_flags(self):
        """Validate feature flag configuration."""
        logger.info("Validating feature flags...")
        
        enabled_features = []
        if settings.FEATURE_AI_ANALYSIS:
            enabled_features.append("AI Analysis")
        if settings.FEATURE_REAL_TIME_MONITORING:
            enabled_features.append("Real-time Monitoring")
        if settings.FEATURE_ADVANCED_ANALYTICS:
            enabled_features.append("Advanced Analytics")
        
        if enabled_features:
            self.info.append(f"✅ Enabled features: {', '.join(enabled_features)}")
        else:
            self.warnings.append("⚠️  No optional features enabled")
        
        # Check development endpoints
        if settings.is_production and settings.ENABLE_DEVELOPMENT_ENDPOINTS:
            self.errors.append("❌ Development endpoints must be disabled in production")
    
    def validate_external_services(self):
        """Validate external service configuration."""
        logger.info("Validating external services...")
        
        # Check Redis configuration
        try:
            from urllib.parse import urlparse
            redis_url = urlparse(settings.REDIS_URL)
            if not redis_url.hostname:
                self.errors.append("❌ Invalid Redis URL")
            else:
                self.info.append("✅ Redis URL is valid")
        except Exception as e:
            self.errors.append(f"❌ Redis URL validation failed: {e}")
        
        # Check Ollama configuration
        if not settings.OLLAMA_BASE_URL.startswith(("http://", "https://")):
            self.errors.append("❌ Invalid Ollama URL")
        else:
            self.info.append("✅ Ollama URL is valid")
    
    def print_results(self):
        """Print validation results."""
        print("\n" + "="*80)
        print("🔍 CONFIGURATION VALIDATION RESULTS")
        print("="*80)
        
        # Print info messages
        if self.info:
            print(f"\n📋 Information ({len(self.info)}):")
            for msg in self.info:
                print(f"  {msg}")
        
        # Print warnings
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for msg in self.warnings:
                print(f"  {msg}")
        
        # Print errors
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for msg in self.errors:
                print(f"  {msg}")
        
        print("\n" + "="*80)
        
        if self.errors:
            print("❌ VALIDATION FAILED - Fix errors before deployment")
            return False
        elif self.warnings:
            print("⚠️  VALIDATION PASSED WITH WARNINGS - Review recommendations")
        else:
            print("✅ VALIDATION PASSED - Configuration is ready for deployment")
        
        print("="*80)
    
    def generate_report(self, output_file: str = "config_validation_report.json"):
        """Generate JSON validation report."""
        report = {
            "timestamp": str(pd.Timestamp.now()),
            "environment": settings.ENVIRONMENT,
            "validation_results": {
                "passed": len(self.errors) == 0,
                "total_checks": len(self.info) + len(self.warnings) + len(self.errors),
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "info": len(self.info)
            },
            "messages": {
                "errors": self.errors,
                "warnings": self.warnings,
                "info": self.info
            },
            "configuration_summary": {
                "project_name": settings.PROJECT_NAME,
                "version": settings.API_VERSION,
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
                "ssl_enabled": getattr(settings, 'SSL_ENABLED', False),
                "prometheus_enabled": getattr(settings, 'PROMETHEUS_ENABLED', False),
                "compliance_mode": getattr(settings, 'COMPLIANCE_MODE', 'unknown')
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📊 Validation report saved to: {output_file}")


def main():
    """Main validation function."""
    validator = ConfigValidator()
    
    # Run validation
    success = validator.validate_all()
    
    # Generate report if requested
    if "--report" in sys.argv:
        validator.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()