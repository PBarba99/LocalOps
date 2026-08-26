"""Tests for the restricted SSH transport boundary."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from localops.config import Settings
from localops.ssh_client import CommandResult, SSHClient
from localops.tools.registry import CommandID


def test_ssh_client_uses_validated_settings() -> None:
    settings = Settings(
        server_host="homeserver",
        server_port=2222,
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )

    client = SSHClient(settings=settings)

    assert client.settings is settings


def test_paramiko_client_uses_known_hosts_and_rejects_unknown_hosts() -> None:
    with (
        patch("localops.ssh_client.paramiko.SSHClient") as client_class,
        patch("localops.ssh_client.paramiko.RejectPolicy") as policy_class,
    ):
        client = SSHClient._create_paramiko_client()

    assert client is client_class.return_value
    client.load_system_host_keys.assert_called_once_with()
    policy_class.assert_called_once_with()
    client.set_missing_host_key_policy.assert_called_once_with(
        policy_class.return_value
    )
    client.connect.assert_not_called()


def test_check_connection_uses_settings_and_always_closes() -> None:
    settings = Settings(
        server_host="homeserver",
        server_port=2222,
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )
    ssh = SSHClient(settings=settings, connection_timeout=5)

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        ssh.check_connection()

    client = create_client.return_value
    client.connect.assert_called_once_with(
        hostname="homeserver",
        port=2222,
        username="localops",
        key_filename="test_key",
        timeout=5,
        banner_timeout=5,
        auth_timeout=5,
        look_for_keys=False,
        allow_agent=False,
    )
    client.close.assert_called_once_with()


def test_check_connection_closes_after_connection_failure() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )
    ssh = SSHClient(settings=settings)

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        create_client.return_value.connect.side_effect = TimeoutError("timed out")

        with pytest.raises(TimeoutError, match="timed out"):
            ssh.check_connection()

    create_client.return_value.close.assert_called_once_with()


def test_connection_timeout_must_be_positive() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )

    with pytest.raises(ValueError, match="greater than zero"):
        SSHClient(settings=settings, connection_timeout=0)


def test_command_timeout_must_be_positive() -> None:
    settings = Settings(
        server_host="homeserver",
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )

    with pytest.raises(ValueError, match="Command timeout"):
        SSHClient(settings=settings, command_timeout=0)


def test_ssh_client_resolves_an_approved_command() -> None:
    client = SSHClient(
        settings=Settings(
            server_host="homeserver",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )
    )

    assert client.resolve_command(CommandID.UPTIME) == "uptime"


@pytest.mark.parametrize("untrusted_id", ["uptime", "uptime; id", "$(id)"])
def test_ssh_client_rejects_untrusted_command_text(untrusted_id: str) -> None:
    client = SSHClient(
        settings=Settings(
            server_host="homeserver",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )
    )

    with pytest.raises(ValueError, match="Unknown command ID"):
        client.resolve_command(untrusted_id)  # type: ignore[arg-type]


def test_run_approved_command_executes_exact_fixed_command() -> None:
    settings = Settings(
        server_host="homeserver",
        server_port=2222,
        server_username="localops",
        server_ssh_key=Path("test_key"),
        _env_file=None,
    )
    ssh = SSHClient(settings=settings, connection_timeout=5, command_timeout=7)
    channel = MagicMock()
    channel.recv_ready.side_effect = [True, False]
    channel.recv.return_value = b"server-01\n"
    channel.recv_stderr_ready.return_value = False
    channel.exit_status_ready.return_value = True
    channel.recv_exit_status.return_value = 0
    stdout = MagicMock(channel=channel)

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        client = create_client.return_value
        client.exec_command.return_value = (MagicMock(), stdout, MagicMock())

        result = ssh.run_approved_command(CommandID.HOSTNAME)

    client.exec_command.assert_called_once_with("hostname", timeout=7)
    client.close.assert_called_once_with()
    assert result == CommandResult(
        stdout="server-01\n",
        stderr="",
        exit_code=0,
    )


def test_run_rejects_injected_text_before_creating_ssh_client() -> None:
    ssh = SSHClient(
        settings=Settings(
            server_host="homeserver",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )
    )

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        with pytest.raises(ValueError, match="Unknown command ID"):
            ssh.run_approved_command("hostname; id")  # type: ignore[arg-type]

    create_client.assert_not_called()


def test_run_stops_and_closes_client_when_connection_fails() -> None:
    ssh = SSHClient(
        settings=Settings(
            server_host="homeserver",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )
    )

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        client = create_client.return_value
        client.connect.side_effect = ConnectionRefusedError("connection refused")

        with pytest.raises(ConnectionRefusedError, match="connection refused"):
            ssh.run_approved_command(CommandID.HOSTNAME)

    client.exec_command.assert_not_called()
    client.close.assert_called_once_with()


@pytest.mark.parametrize("failure", [TimeoutError("timed out"), OSError("closed")])
def test_run_closes_client_when_ssh_operation_fails(failure: Exception) -> None:
    ssh = SSHClient(
        settings=Settings(
            server_host="homeserver",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )
    )

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        client = create_client.return_value
        client.exec_command.side_effect = failure

        with pytest.raises(type(failure), match=str(failure)):
            ssh.run_approved_command(CommandID.UPTIME)

    client.close.assert_called_once_with()


def test_run_returns_nonzero_exit_status_and_stderr() -> None:
    ssh = SSHClient(
        settings=Settings(
            server_host="homeserver",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        )
    )
    channel = MagicMock()
    channel.recv_ready.side_effect = [True, False]
    channel.recv.return_value = b"partial output\n"
    channel.recv_stderr_ready.side_effect = [True, False]
    channel.recv_stderr.return_value = b"command failed\n"
    channel.exit_status_ready.return_value = True
    channel.recv_exit_status.return_value = 1
    stdout = MagicMock(channel=channel)

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        create_client.return_value.exec_command.return_value = (
            MagicMock(),
            stdout,
            MagicMock(),
        )
        result = ssh.run_approved_command(CommandID.DISK_USAGE)

    assert result == CommandResult(
        stdout="partial output\n",
        stderr="command failed\n",
        exit_code=1,
    )


def test_run_times_out_when_command_never_finishes() -> None:
    ssh = SSHClient(
        settings=Settings(
            server_host="homeserver",
            server_username="localops",
            server_ssh_key=Path("test_key"),
            _env_file=None,
        ),
        command_timeout=0.01,
    )
    channel = MagicMock()
    channel.recv_ready.return_value = False
    channel.recv_stderr_ready.return_value = False
    channel.exit_status_ready.return_value = False
    stdout = MagicMock(channel=channel)

    with patch.object(SSHClient, "_create_paramiko_client") as create_client:
        client = create_client.return_value
        client.exec_command.return_value = (MagicMock(), stdout, MagicMock())

        with pytest.raises(TimeoutError, match="exceeded"):
            ssh.run_approved_command(CommandID.UPTIME)

    channel.close.assert_called_once_with()
    client.close.assert_called_once_with()
