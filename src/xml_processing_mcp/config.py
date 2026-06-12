"""Application configuration via environment variables."""

import logging
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
    log_level: str = "DEBUG"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging(settings: Settings | None = None) -> None:
    """Configure root logger from settings. Call once at server startup."""
    if settings is None:
        settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.DEBUG)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logging.getLogger(__name__).debug("Logging initialised at level %s", settings.log_level.upper())
