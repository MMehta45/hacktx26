from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend configuration loaded from environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    nessie_api_key: str | None = None
    serpapi_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    research_max_calls: int = 6
    research_rerun_max_calls: int = 8
    research_max_iterations: int = 4
    research_deadline_seconds: int = 85
    research_cache_ttl_seconds: int = 900
    nessie_base_url: str = "https://prod-api.nessieisreal.com"
    demo_data_mode: Literal["auto", "fixture", "nessie"] = "auto"
    demo_anchor_date: date = date(2026, 10, 24)
    seed_manifest_path: Path = Path(".local/nessie-seed.json")
    frontend_origin: str = "http://localhost:3000"

    @field_validator("nessie_api_key", "serpapi_api_key", "gemini_api_key", mode="before")
    @classmethod
    def blank_secrets_are_unset(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def integration_status(self) -> dict[str, bool]:
        return {
            "nessie": bool(self.nessie_api_key),
            "serpapi": bool(self.serpapi_api_key),
            "gemini": bool(self.gemini_api_key),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
