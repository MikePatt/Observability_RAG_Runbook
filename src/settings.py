from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "obs-rag"
    app_version: str = "0.2.0"
    app_env: str = Field(default="dev", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")

    runbook_dir: str = Field(default="runbooks", alias="RUNBOOK_DIR")
    persist_path: str = Field(default="faiss_index", alias="PERSIST_PATH")
    top_k: int = Field(default=4, alias="TOP_K")
    force_rebuild: bool = Field(default=False, alias="FORCE_REBUILD")
    query_timeout_seconds: int = Field(default=30, alias="QUERY_TIMEOUT_SECONDS")

    enable_docs: bool = Field(default=True, alias="ENABLE_DOCS")


@lru_cache
def get_settings() -> Settings:
    return Settings()