"""Application settings loaded from environment variables / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Empty → the SDK falls back to its own credential resolution (env / ant profile).
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    # Holds the SQLite file and per-book caches; the only state to move when changing hosts.
    data_dir: Path = Path("data")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def books_dir(self) -> Path:
        return self.data_dir / "books"
