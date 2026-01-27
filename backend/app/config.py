from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ignore unrelated environment variables (common in CI/dev shells).
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "wisdomprompt"
    cors_allow_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./wisdomprompt.db"

    # LLM Provider
    llm_provider: str = "nvidia"  # "nvidia" or "openai"
    
    # OpenAI
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    
    # NVIDIA (OpenAI-compatible endpoint)
    nvidia_api_key: str | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "z-ai/glm4.7"

    # Vector store
    vector_store: str = "milvus"  # milvus
    embedding_dim: int = 384
    milvus_uri: str | None = None
    milvus_token: str | None = None
    milvus_collection: str = "wisdomprompt_docs"
    milvus_id_field: str = "id"
    milvus_text_field: str = "content"
    milvus_vector_field: str = "vector"
    milvus_metadata_field: str = "metadata"

    # Search providers
    exa_api_key: str | None = None
    serper_api_key: str | None = None
    github_token: str | None = None

    # Retrieval behavior
    top_k: int = 6
    high_score_threshold: float = 0.85
    min_high_score_hits: int = 2


settings = Settings()
