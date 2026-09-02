import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root directory resolution
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Google Gemini Settings
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 45

    # Qdrant Cloud Vector Database
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "regulations"

    # Embedding Settings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    VECTOR_DIMENSION: int = 384

    # SQLite Database Path
    DATABASE_PATH: str = str(ROOT_DIR / "data" / "reglens.db")
    DB_TIMEOUT: int = 10

    # CORS & Server Settings
    CORS_ORIGINS: str = "http://localhost:8501,http://localhost:3000"
    ALLOWED_ORIGINS: str = ""  # For backward compatibility
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

    # Paths
    PROMPT_PATH: str = str(ROOT_DIR / "prompts" / "compliance.txt")
    REGULATIONS_DIR: str = str(ROOT_DIR / "regulations")

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(ROOT_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_cors_origins(self) -> list[str]:
        raw_origins = self.CORS_ORIGINS or self.ALLOWED_ORIGINS or "http://localhost:8501,http://localhost:3000"
        return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


settings = Settings()
