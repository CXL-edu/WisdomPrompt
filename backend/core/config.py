"""Application settings loaded from .env and optional config files."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


SearchSource = Literal["exa", "serper", "brave"]


class Settings(BaseSettings):
    """Application settings. Most config from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    CORS_ALLOW_ORIGINS: str = "http://localhost:5173"
    API_V1_STR: str = "/api/v1"
    API_BASE_URL: str = "http://localhost:8000"

    # LLM
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    LLM_MODEL_ID: str = "gpt-4o-mini"
    OPENAI_TIMEOUT: float = 60.0  # 秒，整次请求超时（非流式=等完整响应；流式=两段数据间最长等待）。非首 token 时间。

    # Embedding (Gemini)
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    # Retrieval
    TOP_K: int = 3
    MIN_SIMILARITY_SCORE: float = 0.7

    # Search
    SEARCH_SOURCE: SearchSource = "brave"
    BRAVE_API_KEY: str = ""
    EXA_API_KEY: str = ""
    SERPER_API_KEY: str = ""

    # Jina Reader (content fetch fallback)
    JINA_READER_ENABLED: bool = True
    JINA_DAILY_LIMIT_COUNT: int = 10
    JINA_DAILY_LIMIT_TOKENS: int = 10_000

    # Optional: SQLite for future use (plan mentions DuckDB for vectors)
    DATABASE_URL: str = "sqlite:///./wisdomprompt.db"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
