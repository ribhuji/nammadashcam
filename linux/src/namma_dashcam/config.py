"""Runtime configuration for the Linux verifier service."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration loaded from environment variables."""

    api_base_url: str = "http://localhost:8000"
    api_token: str | None = None
    webcam_device: str = "/dev/video0"
    webcam_width: int = 1280
    webcam_height: int = 720
    webcam_fps: int = 30
    clip_pre_seconds: float = 1.0
    clip_post_seconds: float = 1.0
    camera_buffer_seconds: float = 3.0
    bridge_event_path: Path = Field(default=Path("./data/bridge-events.jsonl"))
    bridge_poll_interval_seconds: float = 0.2
    storage_dir: Path = Field(default=Path("./data"))
    upload_retry_seconds: int = 30
    api_timeout_seconds: float = 10.0
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_prefix="NAMMA_DASHCAM_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings."""

    return Settings()
