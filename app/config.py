"""
Configuration management using pydantic-settings and python-dotenv
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///offline.db",
        description="Database connection URL",
        alias="DATABASE_URL"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Echo SQL queries for debugging",
        alias="DATABASE_ECHO"
    )
    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Supabase project URL",
        alias="SUPABASE_URL"
    )
    SUPABASE_SERVICE_KEY: Optional[str] = Field(
        default=None,
        description="Supabase service role key",
        alias="SUPABASE_SERVICE_KEY"
    )
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key for GPT-3.5",
        alias="OPENAI_API_KEY"
    )
    
    # Application
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Scraping
    MAX_RETRIES: int = Field(
        default=3,
        description="Maximum retry attempts for HTTP requests"
    )
    REQUEST_TIMEOUT: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    
    # Cost monitoring
    MAX_TOKENS_PER_COMPLAINT: int = Field(
        default=600,
        description="Maximum tokens per complaint for cost guard"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment variables


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()