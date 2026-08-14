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
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536
    embedding_batch_size: int = 100    

    # Required. No default, so a missing value fails at startup, not mid-request.
    database_url: str

    # Corpus lives outside backend/ because the scraper and the API both read it.
    corpus_dir: Path = REPO_ROOT / "data"
    manifest_filename: str = "manifest.json"
    acronyms_filename: str = "acronyms.json"

    answer_model: str = "gpt-5.4-mini"
    answer_max_tokens: int = 800
    # 'none' assumes the task is reading provided text rather than reasoning
    # about policy. Worth re-testing against the eval set: classifying Type
    # A/B/C is a judgment call and may want more deliberation than answering.
    answer_reasoning_effort: str = "none"

    @property
    def manifest_path(self) -> Path:
        return self.corpus_dir / self.manifest_filename
    @property
    def acronyms_path(self) -> Path:
        return self.corpus_dir / self.acronyms_filename

@lru_cache
def get_settings() -> Settings:
    return Settings()