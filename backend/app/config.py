from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> app -> backend
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Waypoint"
    environment: str = "development"

    # Required. No default, so a missing value fails at startup, not mid-request.
    database_url: str

    # Corpus lives outside backend/ because the scraper and the API both read it.
    corpus_dir: Path = REPO_ROOT / "data"
    manifest_filename: str = "manifest.json"

    @property
    def manifest_path(self) -> Path:
        return self.corpus_dir / self.manifest_filename


@lru_cache
def get_settings() -> Settings:
    return Settings()