"""Application settings and configuration"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    perplexity_api_key: str = ""
    
    # Database
    database_url: str = "sqlite:///./roofing_ai.db"
    
    # Application
    app_name: str = "GAF Roofing AI System"
    debug: bool = True
    log_level: str = "INFO"
    
    # Scraping
    default_zipcode: str = "10013"
    default_distance: int = 25
    scraping_delay: float = 2.0
    
    # AI
    ai_model: str = "gpt-4-turbo-preview"
    ai_temperature: float = 0.7
    max_tokens: int = 2000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

