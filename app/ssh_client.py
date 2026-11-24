"""SSH connection helper with allowlisted read-only remote commands."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import paramiko
from flask import Flask

logger = logging.getLogger(__name__)

# Exact allowlisted remote command strings — never accept user-supplied shell.
ALLOWLISTED_COMMANDS: dict[str, str] = {
    "cpu": "grep 'cpu ' /proc/stat",
    "memory": "free -b",
    "disk": "df -B1 -P",
    "network": "cat /proc/net/dev",
    "cpu_count": "nproc",
    "uptime": "cat /proc/uptime",
    "kernel": "uname -r",
    "ips": "hostname -I",
    "load": "cat /proc/loadavg",
    "top_procs": "ps -eo pid,pcpu,pmem,comm --sort=-pcpu",
}


@dataclass(frozen=True)
class SSHConfig:
    user: str
    port: int
    timeout: float
    key_path: str | None
    password: str | None
    strict_host_key: bool


def configure_ssh(app: Flask) -> None:
    """Load global SSH defaults from environment (timeout / host-key policy)."""
    strict_raw = os.getenv("SSH_STRICT_HOST_KEY", "false").strip().lower()
    strict = strict_raw in ("1", "true", "yes", "on")
    app.config["SSH_PORT"] = int(os.getenv("SSH_PORT", "22"))
    app.config["SSH_TIMEOUT"] = float(os.getenv("SSH_TIMEOUT", "10"))
    # Optional global fallbacks (per-server credentials preferred)
    app.config["SSH_USER"] = os.getenv("SSH_USER", "").strip()
    key_path = os.getenv("SSH_KEY_PATH", "").strip()
    app.config["SSH_KEY_PATH"] = key_path or None
    password = os.getenv("SSH_PASSWORD", "")
    app.config["SSH_PASSWORD"] = password if password else None
    app.config["SSH_STRICT_HOST_KEY"] = strict


def ssh_config_from_app(app: Flask) -> SSHConfig:
    return SSHConfig(
        user=app.config.get("SSH_USER", ""),
        port=int(app.config.get("SSH_PORT", 22)),
        timeout=float(app.config.get("SSH_TIMEOUT", 10)),
        key_path=app.config.get("SSH_KEY_PATH"),
        password=app.config.get("SSH_PASSWORD"),
        strict_host_key=bool(app.config.get("SSH_STRICT_HOST_KEY", False)),
    )


def ssh_config_for_server(server: dict[str, Any], app: Flask) -> SSHConfig:
    """Build SSH config from a registry row, falling back to app defaults."""
    user = (server.get("ssh_username") or app.config.get("SSH_USER") or "").strip()
    key_path = server.get("ssh_key_path") or app.config.get("SSH_KEY_PATH")
    password = server.get("ssh_password")
    if password is None:
        password = app.config.get("SSH_PASSWORD")
    port = server.get("ssh_port") or app.config.get("SSH_PORT") or 22
    return SSHConfig(
        user=user,
        port=int(port),
        timeout=float(app.config.get("SSH_TIMEOUT", 10)),
        key_path=key_path or None,
        password=password or None,
        strict_host_key=bool(app.config.get("SSH_STRICT_HOST_KEY", False)),
    )


def _host_key_policy(strict: bool) -> paramiko.MissingHostKeyPolicy:
    if strict:
        return paramiko.RejectPolicy()
    return paramiko.AutoAddPolicy()


def _validate_config(config: SSHConfig) -> str | None:
    if not config.user:
        return "SSH username is not configured"
    if not config.key_path and not config.password:
        return "SSH password or key path must be configured"
    return None


def _connect_hostname(host: str) -> str:
    """Prefer IPv4 for localhost so demo SSH does not fail on ::1-only resolution."""
    if host.strip().lower() == "localhost":
        return "127.0.0.1"
    return host


def open_ssh_client(
    host: str,
    config: SSHConfig,
    *,
    client_cls: type[paramiko.SSHClient] = paramiko.SSHClient,
) -> tuple[bool, paramiko.SSHClient | str]:
    """Connect to ``host``. Returns ``(ok, client_or_error)``."""
    err = _validate_config(config)
    if err:
        return False, err

    client = client_cls()
    try:
        with suppress(Exception):
            client.load_system_host_keys()
        client.set_missing_host_key_policy(_host_key_policy(config.strict_host_key))
        connect_kwargs: dict[str, Any] = {
            "hostname": _connect_hostname(host),
            "port": config.port,
            "username": config.user,
            "timeout": config.timeout,
            "banner_timeout": config.timeout,
            "auth_timeout": config.timeout,
            "look_for_keys": False,
            "allow_agent": False,
        }
        if config.key_path:
            connect_kwargs["key_filename"] = config.key_path
        if config.password:
            connect_kwargs["password"] = config.password
        client.connect(**connect_kwargs)
        return True, client
    except Exception as exc:  # noqa: BLE001 — surface as safe error tuple
        logger.warning("SSH connection to %s failed: %s", host, type(exc).__name__)
        with suppress(Exception):
            client.close()
        return False, f"SSH connection failed: {type(exc).__name__}"


def _exec_allowlisted(
    client: paramiko.SSHClient,
    command_key: str,
    timeout: float,
) -> tuple[bool, str]:
    if command_key not in ALLOWLISTED_COMMANDS:
        return False, f"Unknown or disallowed command key: {command_key}"
    command = ALLOWLISTED_COMMANDS[command_key]
    try:
        _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            detail = err.strip() or out.strip() or f"exit status {exit_status}"
            return False, f"Remote command failed: {detail}"
        return True, out
    except Exception as exc:  # noqa: BLE001 — surface as safe error tuple
        logger.warning("SSH command %s failed: %s", command_key, type(exc).__name__)
        return False, f"SSH command failed: {type(exc).__name__}"


def run_command(
    host: str,
    command_key: str,
    config: SSHConfig,
    *,
    client_opener: Callable[
        [str, SSHConfig], tuple[bool, paramiko.SSHClient | str]
    ] = open_ssh_client,
) -> tuple[bool, str]:
    """
    Run a single allowlisted command on ``host``.

    Returns ``(True, stdout)`` or ``(False, error_message)``. Never raises to callers.
    """
    if command_key not in ALLOWLISTED_COMMANDS:
        return False, f"Unknown or disallowed command key: {command_key}"

    ok, client_or_err = client_opener(host, config)
    if not ok:
        return False, str(client_or_err)

    client = client_or_err
    try:
        return _exec_allowlisted(client, command_key, config.timeout)
    finally:
        with suppress(Exception):
            client.close()


def run_commands(
    host: str,
    command_keys: list[str],
    config: SSHConfig,
    *,
    client_opener: Callable[
        [str, SSHConfig], tuple[bool, paramiko.SSHClient | str]
    ] = open_ssh_client,
) -> dict[str, tuple[bool, str]]:
    """Run several allowlisted commands on one SSH connection."""
    results: dict[str, tuple[bool, str]] = {}
    for key in command_keys:
        if key not in ALLOWLISTED_COMMANDS:
            results[key] = (False, f"Unknown or disallowed command key: {key}")

    ok, client_or_err = client_opener(host, config)
    if not ok:
        err = str(client_or_err)
        for key in command_keys:
            results.setdefault(key, (False, err))
        return results

    client = client_or_err
    try:
        for key in command_keys:
            if key in results:
                continue
            results[key] = _exec_allowlisted(client, key, config.timeout)
    finally:
        with suppress(Exception):
            client.close()
    return results


def run_allowlisted(
    host: str,
    command_key: str,
    app: Flask,
) -> dict[str, Any]:
    """Thin API: structured result for one allowlisted command using app defaults."""
    config = ssh_config_from_app(app)
    ok, payload = run_command(host, command_key, config)
    if ok:
        return {
            "ok": True,
            "host": host,
            "command_key": command_key,
            "output": payload,
            "error": None,
        }
    return {
        "ok": False,
        "host": host,
        "command_key": command_key,
        "output": None,
        "error": payload,
    }
