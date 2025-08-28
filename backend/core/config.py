"""
Manages all environment variables and settings for the Mechanical Integrity AI system.
All safety-critical parameters are defined here with appropriate defaults.
"""
from typing import List, Union, Literal, Optional
import logging

from pydantic import AnyHttpUrl, Field, field_validator, ValidationInfo, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with safety-critical defaults for petroleum industry compliance."""

    # ============================================================================
    # APPLICATION CONFIGURATION
    # ============================================================================
    PROJECT_NAME: str = "Mechanical Integrity AI"
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    # Production-safe defaults for safety-critical petroleum industry compliance
    ENVIRONMENT: Literal["development", "testing", "production"] = "production"  # Default to production for safety
    DEBUG: bool = False  # Never enable debug mode by default in safety-critical systems

    @property
    def is_development(self) -> bool:
        """Check if running in development mode for safety-critical features."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.ENVIRONMENT.lower() in ("test", "testing")

    @property
    def APP_NAME(self) -> str:
        """Alias for PROJECT_NAME to maintain backward compatibility."""
        return self.PROJECT_NAME

    @property
    def APP_VERSION(self) -> str:
        """Alias for API_VERSION to maintain backward compatibility."""
        return self.API_VERSION

    # ============================================================================
    # SECURITY CONFIGURATION
    # ============================================================================
    SECRET_KEY: str = Field(
        description="JWT token signing key - MUST be set via environment variable",
        min_length=64  # Ensure sufficient entropy for security
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS - Cross-Origin Resource Sharing for frontend integration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",   # React default
        "http://localhost:5173",   # Vite/Vue default
    ]

    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    POSTGRES_USER: str = Field(default="will", description="Database username")
    POSTGRES_PASSWORD: str = Field(
        description="Database password - MUST be set via environment variable for security"
    )
    POSTGRES_SERVER: str = Field(default="localhost", description="Database server hostname")
    POSTGRES_PORT: int = Field(default=5432, description="Database server port")
    POSTGRES_DB: str = Field(
        default="risk-assessment", 
        description="Database name - matches existing deployment"
    )

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL with AsyncPG driver."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ============================================================================
    # EXTERNAL SERVICES
    # ============================================================================
    # Redis for job queuing and caching
    REDIS_URL: str = "redis://localhost:6379"

    # Ollama LLM service for document analysis
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # ============================================================================
    # MACHINE LEARNING CONFIGURATION
    # ============================================================================
    YOLO_MODEL_PATH: str = "ml/models/corrosion_yolov8.pt"
    ML_CONFIDENCE_THRESHOLD: float = 0.85

    # ============================================================================
    # DOCUMENT PROCESSING
    # ============================================================================
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FILE_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png"]
    UPLOAD_DIRECTORY: str = "uploads"
    REPORTS_DIRECTORY: str = "reports"

    # ============================================================================
    # API 579 SAFETY-CRITICAL PARAMETERS
    # ============================================================================
    # These values are critical for regulatory compliance - modify with extreme caution
    API579_DEFAULT_SAFETY_FACTOR: float = 0.9  # Conservative safety factor
    API579_DEFAULT_CORROSION_RATE: float = 0.005  # inches/year - must be validated per equipment
    
    # TODO: [COMPLIANCE-CRITICAL] Add SAFETY_FACTOR environment variable per audit findings
    # Compliance audit identified missing SAFETY_FACTOR config (ref: compliance_audit_report.md line 26)  
    # Required: SAFETY_FACTOR >= 2.0 for API 579 Part 5 conservative safety factor compliance
    # Implementation: Add SAFETY_FACTOR: float = Field(ge=2.0, default=2.0) to config
    # Priority: CRITICAL - blocking regulatory compliance certification
    SAFETY_FACTOR: float = Field(default=2.0, ge=2.0, description="Global safety factor for API 579 calculations")

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],  # Local overrides global
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Allow extra env vars for flexibility
        validate_default=True,  # Validate default values
    )

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, debug_value) -> bool:
        """
        Parse DEBUG value from environment variable.
        Handles string-to-boolean conversion gracefully.
        """
        if isinstance(debug_value, bool):
            return debug_value
        elif isinstance(debug_value, str):
            # Handle common string representations
            debug_lower = debug_value.lower().strip()
            if debug_lower in ("true", "1", "yes", "on"):
                return True
            elif debug_lower in ("false", "0", "no", "off", "warn"):
                return False
            else:
                raise ValueError(
                    f"Invalid DEBUG value: '{debug_value}'. "
                    "Use 'true'/'false', '1'/'0', 'yes'/'no', or 'on'/'off'."
                )
        else:
            raise ValueError(f"DEBUG must be boolean or string, got {type(debug_value)}")

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_production_safety(cls, debug_value: bool, info: ValidationInfo) -> bool:
        """
        Safety validation: Prevent DEBUG=True in production environment.

        For safety-critical petroleum industry applications, debug mode
        must never be enabled in production as it could expose sensitive
        API 579 compliance data and calculation internals.
        """
        # Get environment from validation context if available
        if hasattr(info, 'data') and info.data:
            environment = info.data.get('ENVIRONMENT', '').lower()
            if environment == 'production' and debug_value:
                raise ValueError(
                    "SAFETY VIOLATION: DEBUG=True is forbidden in production environment "
                    "for safety-critical petroleum industry compliance system. "
                    "Set ENVIRONMENT=development to enable debug mode."
                )
        return debug_value

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> Union[List[str], str]:
        """
        Parse CORS origins from environment variable.

        Supports both comma-separated strings and list formats.
        """
        if isinstance(value, str) and not value.startswith("["):
            # Handle comma-separated string: "http://localhost:3000,http://localhost:5173"
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        elif isinstance(value, (list, str)):
            # Handle list or JSON string format
            return value
        else:
            raise ValueError(f"Invalid CORS origins format: {value}")

    # ============================================================================
    # PRODUCTION DEPLOYMENT CONFIGURATION
    # ============================================================================
    
    # SSL/TLS Configuration
    SSL_CERT_PATH: Optional[str] = Field(None, description="SSL certificate file path")
    SSL_KEY_PATH: Optional[str] = Field(None, description="SSL private key file path")
    SSL_ENABLED: bool = Field(False, description="Enable SSL/TLS")
    
    @field_validator("SSL_ENABLED")
    @classmethod
    def validate_ssl_config(cls, ssl_enabled: bool, info: ValidationInfo) -> bool:
        """Validate SSL configuration in production."""
        if hasattr(info, 'data') and info.data:
            environment = info.data.get('ENVIRONMENT', '').lower()
            ssl_cert = info.data.get('SSL_CERT_PATH')
            ssl_key = info.data.get('SSL_KEY_PATH')
            
            if environment == 'production' and ssl_enabled:
                if not ssl_cert or not ssl_key:
                    raise ValueError(
                        "SSL_CERT_PATH and SSL_KEY_PATH must be provided when SSL_ENABLED=true in production"
                    )
        return ssl_enabled
    
    # Database Connection Pooling
    DB_POOL_SIZE: int = Field(20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(30, description="Database connection pool overflow")
    DB_POOL_TIMEOUT: int = Field(30, description="Database connection timeout seconds")
    DB_POOL_RECYCLE: int = Field(3600, description="Database connection recycle time seconds")
    
    # Redis Configuration
    REDIS_POOL_SIZE: int = Field(20, description="Redis connection pool size")
    REDIS_TIMEOUT: int = Field(5, description="Redis operation timeout seconds")
    REDIS_MAX_CONNECTIONS: int = Field(50, description="Maximum Redis connections")
    
    # Load Balancer and Proxy Configuration
    TRUSTED_PROXIES: List[str] = Field(
        ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
        description="Trusted proxy IP addresses/ranges"
    )
    
    @field_validator("TRUSTED_PROXIES", mode="before")
    @classmethod
    def parse_trusted_proxies(cls, value):
        """Parse trusted proxy list from environment."""
        if isinstance(value, str):
            return [proxy.strip() for proxy in value.split(",") if proxy.strip()]
        return value
    
    # Monitoring and Alerting
    PROMETHEUS_ENABLED: bool = Field(True, description="Enable Prometheus metrics")
    PROMETHEUS_PREFIX: str = Field("mechanical_integrity", description="Prometheus metric prefix")
    
    GRAFANA_ENABLED: bool = Field(False, description="Enable Grafana dashboards")
    GRAFANA_URL: Optional[str] = Field(None, description="Grafana dashboard URL")
    
    # Alerting Configuration
    SLACK_WEBHOOK_URL: Optional[str] = Field(None, description="Slack webhook for alerts")
    ALERT_EMAIL_RECIPIENTS: List[str] = Field([], description="Email recipients for alerts")
    
    @field_validator("ALERT_EMAIL_RECIPIENTS", mode="before")
    @classmethod
    def parse_email_list(cls, value):
        """Parse email list from environment."""
        if isinstance(value, str):
            return [email.strip() for email in value.split(",") if email.strip()]
        return value
    
    # Backup Configuration
    BACKUP_ENABLED: bool = Field(False, description="Enable automated backups")
    BACKUP_SCHEDULE: str = Field("0 2 * * *", description="Backup cron schedule")
    BACKUP_RETENTION_DAYS: int = Field(30, description="Backup retention period")
    BACKUP_S3_BUCKET: Optional[str] = Field(None, description="S3 bucket for backups")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(100, description="Requests per minute per IP")
    RATE_LIMIT_BURST: int = Field(20, description="Rate limit burst allowance")
    
    # Feature Flags
    FEATURE_AI_ANALYSIS: bool = Field(True, description="Enable AI document analysis")
    FEATURE_REAL_TIME_MONITORING: bool = Field(False, description="Enable real-time monitoring")
    FEATURE_ADVANCED_ANALYTICS: bool = Field(False, description="Enable advanced analytics")
    
    # Compliance and Audit
    AUDIT_LOG_ENABLED: bool = Field(True, description="Enable audit logging")
    AUDIT_LOG_RETENTION_DAYS: int = Field(2555, description="Audit log retention (7 years)")  # 7 years = 2555 days
    COMPLIANCE_MODE: Literal["strict", "standard", "development"] = Field(
        "strict", 
        description="Compliance enforcement level"
    )
    
    @field_validator("COMPLIANCE_MODE")
    @classmethod
    def validate_compliance_mode(cls, compliance_mode: str, info: ValidationInfo) -> str:
        """Ensure strict compliance mode in production."""
        if hasattr(info, 'data') and info.data:
            environment = info.data.get('ENVIRONMENT', '').lower()
            if environment == 'production' and compliance_mode != 'strict':
                raise ValueError(
                    "COMPLIANCE_MODE must be 'strict' in production environment for regulatory compliance"
                )
        return compliance_mode
    
    # Performance Tuning
    MAX_CONCURRENT_CALCULATIONS: int = Field(10, description="Maximum concurrent API 579 calculations")
    CALCULATION_TIMEOUT_SECONDS: int = Field(300, description="Calculation timeout (5 minutes)")
    CACHE_DEFAULT_TTL_SECONDS: int = Field(3600, description="Default cache TTL (1 hour)")
    
    # Development and Testing
    ENABLE_DEVELOPMENT_ENDPOINTS: bool = Field(False, description="Enable development-only endpoints")
    
    @field_validator("ENABLE_DEVELOPMENT_ENDPOINTS")
    @classmethod
    def validate_dev_endpoints(cls, enable_dev: bool, info: ValidationInfo) -> bool:
        """Disable development endpoints in production."""
        if hasattr(info, 'data') and info.data:
            environment = info.data.get('ENVIRONMENT', '').lower()
            if environment == 'production' and enable_dev:
                raise ValueError(
                    "ENABLE_DEVELOPMENT_ENDPOINTS must be false in production environment"
                )
        return enable_dev
    
    def get_database_url(self, async_driver: bool = True) -> str:
        """Get database URL with proper driver."""
        driver = "postgresql+asyncpg" if async_driver else "postgresql"
        return (
            f"{driver}://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature flag is enabled."""
        feature_map = {
            "ai_analysis": self.FEATURE_AI_ANALYSIS,
            "real_time_monitoring": self.FEATURE_REAL_TIME_MONITORING,
            "advanced_analytics": self.FEATURE_ADVANCED_ANALYTICS,
        }
        return feature_map.get(feature, False)
    
    def get_trusted_proxy_networks(self):
        """Get trusted proxy networks as ipaddress objects."""
        import ipaddress
        networks = []
        for proxy in self.TRUSTED_PROXIES:
            try:
                networks.append(ipaddress.ip_network(proxy, strict=False))
            except ValueError:
                logger.warning(f"Invalid proxy network: {proxy}")
        return networks


# Create settings instance with validation
try:
    settings = Settings()
    
    # Log configuration summary (non-sensitive values only)
    logger = logging.getLogger(__name__)
    logger.info(
        f"Configuration loaded: {settings.PROJECT_NAME} v{settings.API_VERSION} "
        f"({settings.ENVIRONMENT})"
    )
    
    if settings.is_production:
        logger.info("Production mode: Enhanced security and compliance enabled")
        if settings.SSL_ENABLED:
            logger.info("SSL/TLS enabled")
        if settings.PROMETHEUS_ENABLED:
            logger.info("Prometheus metrics enabled")
        if settings.AUDIT_LOG_ENABLED:
            logger.info(f"Audit logging enabled (retention: {settings.AUDIT_LOG_RETENTION_DAYS} days)")
    
except ValidationError as e:
    logger.error(f"Configuration validation failed: {e}")
    raise
except Exception as e:
    logger.error(f"Configuration loading failed: {e}")
    raise
