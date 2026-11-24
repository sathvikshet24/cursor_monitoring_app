"""Input validation for server registry fields."""

import ipaddress
import os
import re

SHELL_METACHAR = re.compile(r'[;|&$`\n\r<>(){}\[\]\'\"\\]')
MAX_HOST_LEN = 253
MAX_LABEL_LEN = 100
MAX_USER_LEN = 64
MAX_PATH_LEN = 512

HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)
USERNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")


def validate_hostname_or_ip(value: str) -> str | None:
    """Return an error message if value is not a safe hostname or IP, else None."""
    value = (value or "").strip()
    if not value:
        return "Hostname or IP is required."
    if len(value) > MAX_HOST_LEN:
        return "Hostname or IP is too long."
    if SHELL_METACHAR.search(value):
        return "Hostname or IP contains invalid characters."
    try:
        ipaddress.ip_address(value)
        return None
    except ValueError:
        pass
    if HOSTNAME_RE.match(value):
        return None
    return "Enter a valid hostname or IPv4/IPv6 address."


def validate_label(value: str | None, *, required: bool = False) -> tuple[str | None, str | None]:
    """Return (sanitized label or None, error message or None)."""
    if value is None:
        label = ""
    else:
        label = value.strip()
    if not label:
        if required:
            return None, "Inventory name is required."
        return None, None
    if len(label) > MAX_LABEL_LEN:
        return None, "Inventory name is too long."
    if SHELL_METACHAR.search(label):
        return None, "Inventory name contains invalid characters."
    return label, None


def validate_ssh_username(value: str) -> tuple[str | None, str | None]:
    value = (value or "").strip()
    if not value:
        return None, "SSH username is required."
    if len(value) > MAX_USER_LEN:
        return None, "SSH username is too long."
    if not USERNAME_RE.match(value):
        return None, "Enter a valid SSH username."
    return value, None


def validate_ssh_auth(
    password: str | None,
    key_path: str | None,
) -> tuple[str | None, str | None, str | None]:
    """
    Return (password_or_None, key_path_or_None, error_or_None).
    At least one of password or key path is required.
    """
    pw = (password or "").strip() or None
    key = (key_path or "").strip() or None

    if not pw and not key:
        return None, None, "Provide an SSH password or a private key path."

    if key:
        if len(key) > MAX_PATH_LEN:
            return None, None, "SSH key path is too long."
        if SHELL_METACHAR.search(key):
            return None, None, "SSH key path contains invalid characters."
        if not os.path.isabs(key):
            return None, None, "SSH key path must be an absolute path."
        if not os.path.isfile(key):
            return None, None, "SSH private key file was not found."

    return pw, key, None


def validate_ssh_port(value: str | None) -> tuple[int | None, str | None]:
    raw = (value or "22").strip() or "22"
    try:
        port = int(raw)
    except ValueError:
        return None, "SSH port must be a number."
    if not 1 <= port <= 65535:
        return None, "SSH port must be between 1 and 65535."
    return port, None
