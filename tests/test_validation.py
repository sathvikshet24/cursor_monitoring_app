from app.validation import (
    validate_hostname_or_ip,
    validate_label,
    validate_ssh_auth,
    validate_ssh_username,
)


def test_validate_hostname_accepts_fqdn():
    assert validate_hostname_or_ip("web-01.internal.example.com") is None


def test_validate_hostname_accepts_localhost():
    assert validate_hostname_or_ip("localhost") is None


def test_validate_ip_accepts_ipv6():
    assert validate_hostname_or_ip("2001:db8::1") is None


def test_validate_rejects_metachar():
    assert validate_hostname_or_ip("host|cat /etc/passwd") is not None


def test_validate_label_strips_empty():
    label, err = validate_label("  ")
    assert label is None and err is None


def test_validate_label_required():
    label, err = validate_label("  ", required=True)
    assert label is None
    assert "required" in err.lower()


def test_validate_ssh_username():
    user, err = validate_ssh_username("jumpuser17")
    assert user == "jumpuser17" and err is None


def test_validate_ssh_auth_requires_one(tmp_path):
    _pw, _key, err = validate_ssh_auth("", "")
    assert err is not None
    key_file = tmp_path / "id"
    key_file.write_text("x")
    _pw, key, err = validate_ssh_auth("", str(key_file))
    assert err is None and key == str(key_file)
