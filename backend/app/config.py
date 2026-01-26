from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "wisdomprompt"
    cors_allow_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./wisdomprompt.db"

    # LLM
    llm_provider: str = "openai"  # openai
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

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
