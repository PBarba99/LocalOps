"""Tests for environment configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from localops.config import Settings, load_settings


def test_load_settings_from_env_file(tmp_path: Path) -> None:
    key_path = tmp_path / "test_key"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SERVER_HOST=homeserver",
                "SERVER_PORT=2222",
                "SERVER_USERNAME=localops",
                f"SERVER_SSH_KEY={key_path}",
                "OLLAMA_BASE_URL=http://localhost:11434",
                "OLLAMA_MODEL=qwen3:4b",
                "OLLAMA_TIMEOUT_SECONDS=37.5",
                "LOG_LEVEL=debug",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.server_host == "homeserver"
    assert settings.server_port == 2222
    assert settings.server_username == "localops"
    assert settings.server_ssh_key == key_path
    assert str(settings.ollama_base_url) == "http://localhost:11434/"
    assert settings.ollama_model == "qwen3:4b"
    assert settings.ollama_timeout_seconds == 37.5
    assert settings.log_level == "DEBUG"


def test_required_settings_cannot_be_blank() -> None:
    with pytest.raises(ValidationError):
        Settings(
            server_host=" ",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )


def test_port_must_be_valid() -> None:
    with pytest.raises(ValidationError):
        Settings(
            server_host="homeserver",
            server_port=70000,
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )


def test_ollama_timeout_defaults_to_120_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OLLAMA_TIMEOUT_SECONDS", raising=False)
    settings = Settings(
        server_host="test-server",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )

    assert settings.ollama_timeout_seconds == 120.0


@pytest.mark.parametrize("timeout", [0, -1, "nan", "inf", "-inf", "invalid"])
def test_ollama_timeout_must_be_positive_and_finite(timeout: object) -> None:
    with pytest.raises(ValidationError):
        Settings(
            server_host="test-server",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            ollama_timeout_seconds=timeout,
            _env_file=None,
        )
