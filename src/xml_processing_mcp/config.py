"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="XML_PROCESSING_", case_sensitive=False)

    max_file_size_mb: int = 20
    max_batch_size: int = 200
    allowed_input_dirs: list[str] = ["/input"]
    allowed_output_dirs: list[str] = ["/output"]
    include_headers_footers: bool = False
    include_comments: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
