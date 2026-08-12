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
