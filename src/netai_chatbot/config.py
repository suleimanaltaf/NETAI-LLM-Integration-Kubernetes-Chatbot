"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class LLMSettings(BaseSettings):
    """Configuration for the LLM service integration."""

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"
    mock_mode: bool = True
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 60.0


class PerfSONARSettings(BaseSettings):
    """Configuration for perfSONAR data integration."""

    model_config = SettingsConfigDict(env_prefix="PERFSONAR_")

    api_url: str = "https://ps-dashboard.nrp.ai/api"
    poll_interval: int = 300


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: Literal["debug", "info", "warning", "error"] = "info"
    app_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # Database
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'netai_chatbot.db'}"

    # Sub-configs
    llm: LLMSettings = Field(default_factory=LLMSettings)
    perfsonar: PerfSONARSettings = Field(default_factory=PerfSONARSettings)

    # Kubernetes
    k8s_namespace: str = "netai"
    k8s_gpu_enabled: bool = False

    @property
    def db_path(self) -> Path:
        """Extract the file path from the SQLite URL."""
        return Path(self.database_url.replace("sqlite:///", ""))


def get_settings() -> Settings:
    """Create and return application settings (cached per-call for testing)."""
    return Settings()
