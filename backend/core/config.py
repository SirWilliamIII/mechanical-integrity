"""
Application configuration using Pydantic Settings.

Manages all environment variables and settings for the Mechanical Integrity AI system.
All safety-critical parameters are defined here with appropriate defaults.
"""
from typing import List, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with safety-critical defaults for petroleum industry compliance."""
    
    # ============================================================================
    # APPLICATION CONFIGURATION
    # ============================================================================
    PROJECT_NAME: str = "Mechanical Integrity AI"
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    @property
    def APP_NAME(self) -> str:
        """Alias for PROJECT_NAME to maintain backward compatibility."""
        return self.PROJECT_NAME
    
    # ============================================================================
    # SECURITY CONFIGURATION
    # ============================================================================
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS - Cross-Origin Resource Sharing for frontend integration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",   # React default
        "http://localhost:5173",   # Vite/Vue default
    ]
    
    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mechanical_integrity"
    
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


settings = Settings()
