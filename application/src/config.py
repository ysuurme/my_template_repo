from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Logging
    log_profile: str = "TEST"           # PRD | TEST | DEBUG
    log_separator_width: int = 80
    log_line_width: int = 120
    log_dir: Path = Path("logs")

    # Google AI
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    # Application
    app_name: str = "{{ project_name }}"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


settings = Settings()
