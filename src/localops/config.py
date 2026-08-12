"""Load and validate LocalOps settings from environment variables."""

from pathlib import Path

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    server_host: str = Field(min_length=1)
    server_port: int = Field(default=22, ge=1, le=65535)
    server_username: str = Field(min_length=1)
    server_ssh_key: Path
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    ollama_model: str = Field(default="qwen3:4b", min_length=1)
    log_level: str = "INFO"

    @field_validator("server_host", "server_username", "ollama_model")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("server_ssh_key")
    @classmethod
    def expand_ssh_key_path(cls, value: Path) -> Path:
        return value.expanduser()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"must be one of: {', '.join(sorted(allowed))}")
        return normalized


def load_settings(env_file: str | Path = ".env") -> Settings:
    """Load settings from an env file, with environment variables taking priority."""
    return Settings(_env_file=env_file)
