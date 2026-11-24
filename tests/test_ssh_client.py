"""Unit tests for SSH helper (Paramiko mocked; no real SSH)."""

from unittest.mock import MagicMock, patch

import paramiko
import pytest

from app import create_app
from app.ssh_client import (
    ALLOWLISTED_COMMANDS,
    SSHConfig,
    open_ssh_client,
    run_allowlisted,
    run_command,
)


@pytest.fixture
def ssh_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret",
            "DATABASE_PATH": str(tmp_path / "ssh_test.db"),
            "SSH_USER": "monitor",
            "SSH_PORT": 2222,
            "SSH_TIMEOUT": 5.0,
            "SSH_KEY_PATH": "/tmp/fake_key",
            "SSH_PASSWORD": None,
            "SSH_STRICT_HOST_KEY": True,
        }
    )


def test_allowlisted_keys_map_to_exact_commands():
    assert ALLOWLISTED_COMMANDS["cpu"] == "grep 'cpu ' /proc/stat"
    assert ALLOWLISTED_COMMANDS["memory"] == "free -b"
    assert ALLOWLISTED_COMMANDS["disk"] == "df -B1 -P"
    assert ALLOWLISTED_COMMANDS["network"] == "cat /proc/net/dev"
    assert ALLOWLISTED_COMMANDS["cpu_count"] == "nproc"
    assert ALLOWLISTED_COMMANDS["top_procs"] == "ps -eo pid,pcpu,pmem,comm --sort=-pcpu"


def test_run_command_rejects_unknown_key():
    config = SSHConfig("u", 22, 10.0, "/k", None, True)
    ok, msg = run_command("10.0.0.1", "rm_rf", config)
    assert ok is False
    assert "disallowed" in msg


def test_run_command_missing_user():
    config = SSHConfig("", 22, 10.0, "/k", None, True)
    ok, msg = run_command("host", "cpu", config)
    assert ok is False
    assert "username" in msg.lower()


def test_run_command_missing_credentials():
    config = SSHConfig("user", 22, 10.0, None, None, True)
    ok, msg = run_command("host", "cpu", config)
    assert ok is False
    assert "password or key" in msg.lower()


@patch("app.ssh_client.paramiko.SSHClient")
def test_open_ssh_client_uses_reject_policy_when_strict(mock_client_cls, ssh_app):
    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    config = SSHConfig("monitor", 2222, 5.0, "/tmp/fake_key", None, True)
    ok, client = open_ssh_client("192.0.2.1", config, client_cls=mock_client_cls)

    assert ok is True
    assert client is mock_instance
    policy = mock_instance.set_missing_host_key_policy.call_args[0][0]
    assert isinstance(policy, paramiko.RejectPolicy)
    mock_instance.connect.assert_called_once()
    kwargs = mock_instance.connect.call_args.kwargs
    assert kwargs["hostname"] == "192.0.2.1"
    assert kwargs["username"] == "monitor"
    assert kwargs["port"] == 2222
    assert kwargs["key_filename"] == "/tmp/fake_key"
    assert "password" not in kwargs


@patch("app.ssh_client.paramiko.SSHClient")
def test_open_ssh_client_auto_add_when_not_strict(mock_client_cls):
    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    config = SSHConfig("u", 22, 10.0, None, "secret", False)
    ok, _client = open_ssh_client("host", config, client_cls=mock_client_cls)

    assert ok is True
    policy = mock_instance.set_missing_host_key_policy.call_args[0][0]
    assert isinstance(policy, paramiko.AutoAddPolicy)


@patch("app.ssh_client.paramiko.SSHClient")
def test_open_ssh_client_connection_error_returns_tuple(mock_client_cls):
    mock_instance = MagicMock()
    mock_instance.connect.side_effect = paramiko.SSHException("auth failed")
    mock_client_cls.return_value = mock_instance

    config = SSHConfig("u", 22, 10.0, None, "pw", True)
    ok, msg = open_ssh_client("bad.host", config, client_cls=mock_client_cls)

    assert ok is False
    assert "SSH connection failed" in msg
    assert "SSHException" in msg
    mock_instance.close.assert_called()


def test_run_command_success_with_mock_client():
    config = SSHConfig("u", 22, 10.0, "/k", None, True)
    mock_client = MagicMock()
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"cpu data\n"
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_client.exec_command.return_value = (None, mock_stdout, MagicMock())

    def opener(_host, _config):
        return True, mock_client

    ok, out = run_command("10.0.0.2", "cpu", config, client_opener=opener)

    assert ok is True
    assert out == "cpu data\n"
    mock_client.exec_command.assert_called_once_with(
        ALLOWLISTED_COMMANDS["cpu"], timeout=10.0
    )
    mock_client.close.assert_called_once()


def test_run_command_nonzero_exit():
    config = SSHConfig("u", 22, 10.0, "/k", None, True)
    mock_client = MagicMock()
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b""
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b"permission denied"
    mock_stdout.channel.recv_exit_status.return_value = 1
    mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

    def opener(_host, _config):
        return True, mock_client

    ok, msg = run_command("host", "disk", config, client_opener=opener)

    assert ok is False
    assert "Remote command failed" in msg
    assert "permission denied" in msg


def test_run_allowlisted_structured_result(ssh_app):
    with patch("app.ssh_client.run_command", return_value=(True, "Mem:\n")):
        result = run_allowlisted("srv1", "memory", ssh_app)

    assert result == {
        "ok": True,
        "host": "srv1",
        "command_key": "memory",
        "output": "Mem:\n",
        "error": None,
    }


def test_run_allowlisted_error_shape(ssh_app):
    with patch(
        "app.ssh_client.run_command",
        return_value=(False, "SSH connection failed: timeout"),
    ):
        result = run_allowlisted("srv1", "cpu", ssh_app)

    assert result["ok"] is False
    assert result["output"] is None
    assert "timeout" in result["error"]