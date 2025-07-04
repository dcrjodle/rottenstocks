"""
Application configuration management.

Handles environment variables, settings validation, and configuration loading
using Pydantic Settings for type safety and validation.
"""

import secrets
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import (
    AnyHttpUrl,
    EmailStr,
    HttpUrl,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings
from pydantic_core import MultiHostUrl

# Type definitions for URLs
PostgresDsn = str  # Simplified for now
RedisDsn = str     # Simplified for now


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Application Configuration
    PROJECT_NAME: str = "RottenStocks API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Stock sentiment analysis platform API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = True
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "rottenstocks"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        """Assemble database URL if not provided."""
        if self.DATABASE_URL is None:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[RedisDsn] = None
    
    @model_validator(mode="after")
    def assemble_redis_connection(self) -> "Settings":
        """Assemble Redis URL if not provided."""
        if self.REDIS_URL is None:
            password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return self
    
    # External API Keys
    REDDIT_CLIENT_ID: str
    REDDIT_CLIENT_SECRET: str
    REDDIT_USER_AGENT: str
    
    ALPHA_VANTAGE_API_KEY: str
    GOOGLE_GEMINI_API_KEY: str
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 100
    
    # External API Rate Limits
    REDDIT_RATE_LIMIT_PER_MINUTE: int = 55  # Conservative, API allows 60
    ALPHA_VANTAGE_RATE_LIMIT_PER_MINUTE: int = 5
    GEMINI_RATE_LIMIT_PER_MINUTE: int = 1000
    
    # Caching Configuration
    CACHE_TTL_STOCK_PRICE: int = 300  # 5 minutes
    CACHE_TTL_RATING: int = 1800      # 30 minutes
    CACHE_TTL_SOCIAL_DATA: int = 3600 # 1 hour
    CACHE_PREFIX: str = "rottenstocks"
    
    # Background Tasks Configuration
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    @model_validator(mode="after")
    def assemble_celery_config(self) -> "Settings":
        """Set Celery configuration based on Redis URL."""
        if self.CELERY_BROKER_URL is None:
            # Use Redis DB 1 for Celery broker
            redis_url = str(self.REDIS_URL).replace(f"/{self.REDIS_DB}", "/1")
            self.CELERY_BROKER_URL = redis_url
        
        if self.CELERY_RESULT_BACKEND is None:
            # Use Redis DB 2 for Celery results
            redis_url = str(self.REDIS_URL).replace(f"/{self.REDIS_DB}", "/2")
            self.CELERY_RESULT_BACKEND = redis_url
        
        return self
    
    # Stock Sync Configuration
    STOCK_SYNC_INTERVAL_MINUTES: int = 15
    SENTIMENT_ANALYSIS_BATCH_SIZE: int = 50
    RATING_UPDATE_INTERVAL_MINUTES: int = 30
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "detailed"
    LOG_FILE: Optional[str] = None
    
    # Security Configuration
    ALLOWED_HOSTS: List[str] = ["*"]
    TRUSTED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # Database Pool Configuration
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Testing Configuration
    TESTING: bool = False
    TEST_DATABASE_URL: Optional[PostgresDsn] = None
    
    # Email Configuration (for future use)
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # Social Media Configuration
    REDDIT_SUBREDDITS: List[str] = [
        "wallstreetbets",
        "stocks", 
        "investing",
        "StockMarket",
        "SecurityAnalysis"
    ]
    
    # Sentiment Analysis Configuration
    SENTIMENT_CONFIDENCE_THRESHOLD: float = 0.7
    MIN_POST_SCORE: int = 5  # Minimum Reddit post score to analyze
    MAX_POSTS_PER_SYMBOL: int = 100
    
    class Config:
        env_file = "../.env"
        case_sensitive = True
        extra = "ignore"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return not self.TESTING and self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.TESTING and self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.TESTING or self.ENVIRONMENT.lower() == "test"
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        if self.DATABASE_URL:
            return str(self.DATABASE_URL).replace("+asyncpg", "")
        return ""
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list of strings."""
        return [str(origin) for origin in self.BACKEND_CORS_ORIGINS]


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()


def get_database_url() -> str:
    """Get database URL for current environment."""
    settings = get_settings()
    if settings.is_testing and settings.TEST_DATABASE_URL:
        return str(settings.TEST_DATABASE_URL)
    return str(settings.DATABASE_URL)


def get_redis_url() -> str:
    """Get Redis URL for current environment."""
    settings = get_settings()
    return str(settings.REDIS_URL)


def validate_environment() -> Dict[str, Any]:
    """Validate environment configuration and return status."""
    settings = get_settings()
    
    status = {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "database_configured": bool(settings.DATABASE_URL),
        "redis_configured": bool(settings.REDIS_URL),
        "external_apis": {
            "reddit": bool(settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET),
            "alpha_vantage": bool(settings.ALPHA_VANTAGE_API_KEY),
            "gemini": bool(settings.GOOGLE_GEMINI_API_KEY),
        },
        "security": {
            "secret_key_set": bool(settings.SECRET_KEY),
            "cors_origins_count": len(settings.BACKEND_CORS_ORIGINS),
        },
        "features": {
            "background_tasks": bool(settings.CELERY_BROKER_URL),
            "caching": bool(settings.REDIS_URL),
            "metrics": settings.ENABLE_METRICS,
        }
    }
    
    return status