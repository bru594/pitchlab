"""
PitchLab - Application Configuration
All settings loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "PitchLab"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./pitchlab.db"
    # For production: "postgresql+asyncpg://user:pass@localhost/pitchlab"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Google Places API (for real lead scraping)
    GOOGLE_PLACES_API_KEY: str = ""

    # Groq (AI pitch generation)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-8b-8192"

    # Anthropic (alternative AI)
    ANTHROPIC_API_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_FREE_PRICE_ID: str = ""
    STRIPE_PRO_PRICE_ID: str = ""

    # Email (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""

    # Redis (for Celery task queue)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Credits per plan
    FREE_MONTHLY_CREDITS: int = 15
    STARTER_MONTHLY_CREDITS: int = 150
    PRO_MONTHLY_CREDITS: int = 500

    STRIPE_STARTER_PRICE_ID: str = ""

    # Credit costs
    CREDIT_COST_LEAD_SEARCH: int = 5      # per search batch
    CREDIT_COST_AUDIT: int = 3            # per website audit
    CREDIT_COST_PITCH_GENERATION: int = 2 # per pitch set
    CREDIT_COST_MESSAGE_SEND: int = 1     # per message sent

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
