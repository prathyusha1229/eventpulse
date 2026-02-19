from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EVENTPULSE_", extra="ignore")

    data_dir: Path = Path("data")  # you can override via env var EVENTPULSE_DATA_DIR


settings = Settings()
