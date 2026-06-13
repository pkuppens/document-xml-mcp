"""Application configuration via environment variables."""

import json
import logging
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources.types import NoDecode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="XML_PROCESSING_", case_sensitive=False)

    max_file_size_mb: int = 20
    max_batch_size: int = 200
    # NoDecode prevents pydantic-settings from calling json.loads on the raw env string,
    # so _parse_dir_list can handle both plain paths (/input) and JSON arrays (["/a","/b"]).
    allowed_input_dirs: Annotated[list[str], NoDecode] = ["/input"]
    allowed_output_dirs: Annotated[list[str], NoDecode] = ["/output"]
    include_headers_footers: bool = False
    include_comments: bool = False
    log_level: str = "INFO"

    @field_validator("allowed_input_dirs", "allowed_output_dirs", mode="before")
    @classmethod
    def _parse_dir_list(cls, v: object) -> object:
        """Accept a JSON array, a comma-separated string, or a plain single path.

        Enables docker-compose style ``XML_PROCESSING_ALLOWED_INPUT_DIRS: /input``
        as well as multi-dir ``/input,/data`` and JSON ``["/input","/data"]``.
        """
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if stripped.startswith("["):
            return json.loads(stripped)
        return [p.strip() for p in stripped.split(",") if p.strip()]


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
