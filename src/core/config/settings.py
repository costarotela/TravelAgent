"""Application settings and configuration."""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Database
    DATABASE_URL: str = "sqlite:///./travel_agency.db"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "travel_agent"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # API
    API_VERSION: str = "v1"
    DEBUG: bool = True

    # Cache
    CACHE_TTL: int = 3600  # 1 hour
    CACHE_DIR: str = "./cache"
    CACHE_EXPIRY: int = 3600

    # Provider Credentials
    OLA_USERNAME: str = "usuario_ola"
    OLA_PASSWORD: str = "password_ola"
    AERO_USERNAME: str = "usuario_aero"
    AERO_PASSWORD: str = "password_aero"
    DESPEGAR_USERNAME: str = "usuario_despegar"
    DESPEGAR_PASSWORD: str = "password_despegar"

    # Supabase
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_KEY: str = "your-supabase-key"

    # OpenAI
    OPENAI_API_KEY: str = "your-openai-key"

    # Browser
    BROWSER_HEADLESS: str = "true"
    BROWSER_TIMEOUT: str = "30"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "travel_agent.log"

    # Agent Settings
    AGENT_ANALYSIS_INTERVAL: int = 3600  # 1 hour
    AGENT_MAX_RETRIES: int = 3
    AGENT_TIMEOUT: int = 30

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
