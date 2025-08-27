"""
Manages all environment variables and settings for the Mechanical Integrity AI system.
All safety-critical parameters are defined here with appropriate defaults.
"""
from typing import List, Union, Literal

from pydantic import AnyHttpUrl, Field, field_validator, ValidationInfo
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

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Changed from 'forbid' to 'ignore' to allow extra env vars
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

    # TODO: [PRODUCTION] Add production deployment configuration
    # - SSL/TLS certificate paths and validation
    # - Production database connection pooling settings (max_connections, overflow)
    # - Redis cluster configuration for high availability
    # - Load balancer health check endpoint configuration
    # - Logging configuration with proper log rotation and structured JSON logging


settings = Settings()
