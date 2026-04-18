from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Logging
    log_profile: str = "TEST"           # PRD | TEST | DEBUG
    log_separator_width: int = 80
    log_line_width: int = 120
    log_dir: Path = Path("logs")

    # AI
    ai_provider: str = "anthropic"
    ai_api_key: str = ""
    ai_model: str = "claude-haiku-4-5-20251001"

    # ML
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"
    experiment_name: str = "{{ project_name }}"

    # Paths
    data_dir: Path = Path("data")
    models_dir: Path = Path("models")


settings = Settings()
