"""
Application configuration using pydantic-settings.
All values loaded from environment variables with defaults.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./trading_journal.db"

    # JWT
    SECRET_KEY: str = "change-this-to-a-secure-random-32-char-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 7

    # External APIs
    GEMINI_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
