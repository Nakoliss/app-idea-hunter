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
        alias="database_url"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Echo SQL queries for debugging",
        alias="database_echo"
    )
    SUPABASE_URL: Optional[str] = Field(
        default=None,
        description="Supabase project URL",
        alias="supabase_url"
    )
    SUPABASE_KEY: Optional[str] = Field(
        default=None,
        description="Supabase service role key",
        alias="supabase_service_key"
    )
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key for GPT-3.5",
        alias="openai_api_key"
    )
    
    # Application
    environment: str = Field(
        default="development",
        description="Application environment"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Scraping
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for HTTP requests"
    )
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds"
    )
    
    # Cost monitoring
    max_tokens_per_complaint: int = Field(
        default=600,
        description="Maximum tokens per complaint for cost guard"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()