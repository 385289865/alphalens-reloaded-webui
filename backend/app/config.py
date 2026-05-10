from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Alphalens WebUI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DB_PATH: str = "./db/alphalens.db"

    # Raw data storage
    RAW_DATA_DIR: str = "./db/raw"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Chart generation
    CHART_OUTPUT_DIR: Optional[str] = "./charts"
    MATPLOTLIB_BACKEND: str = "Agg"

    # CORS
    CORS_ORIGINS: list = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
