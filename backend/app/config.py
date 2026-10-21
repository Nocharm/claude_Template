"""Application settings loaded from environment variables / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    # Empty → the SDK falls back to its own credential resolution (env / ant profile).
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"
    # IANA zone of the learner; decides when "today" rolls over for streaks and reviews.
    timezone: str = "Asia/Seoul"
    # Azure Speech resource; TTS is disabled (503) while the key is empty.
    azure_speech_key: str = ""
    azure_speech_region: str = "koreacentral"
    # Gemini image model for webtoon panels; comics are disabled while the key is empty.
    gemini_api_key: str = ""
    gemini_image_model: str = "gemini-2.5-flash-image"
    # Holds the SQLite file and per-book caches; the only state to move when changing hosts.
    data_dir: Path = PROJECT_ROOT / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def books_dir(self) -> Path:
        return self.data_dir / "books"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def comics_dir(self) -> Path:
        return self.data_dir / "comics"
