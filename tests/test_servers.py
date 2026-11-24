"""Server registry add/remove and validation tests."""

from pathlib import Path


def _key_file(tmp_path: Path) -> str:
    key = tmp_path / "id_test"
    key.write_text("fake-key-for-path-check\n")
    return str(key)


def _add_payload(tmp_path: Path, hostname: str, label: str = "Inventory", **extra):
    data = {
        "hostname": hostname,
        "label": label,
        "ssh_username": "monitor",
        "ssh_password": "",
        "ssh_key_path": _key_file(tmp_path),
        "ssh_port": "22",
    }
    data.update(extra)
    return data


def test_unauthenticated_cannot_open_add_page(client):
    response = client.get("/servers/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_cannot_add_server(client):
    response = client.post(
        "/servers/add",
        data={"hostname": "web-01.example.com"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_unauthenticated_cannot_remove_server(client):
    response = client.post("/servers/1/remove", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_add_page_renders(auth_client):
    response = auth_client.get("/servers/add")
    assert response.status_code == 200
    assert b"Add server" in response.data
    assert b"Name of this inventory" in response.data
    assert b"SSH username" in response.data
    assert b"SSH password" in response.data
    assert b"SSH private key path" in response.data


def test_dashboard_links_to_add_page(auth_client):
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"/servers/add" in response.data
    assert b"Add server" in response.data


def test_add_server_shows_on_dashboard(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "web-01.example.com", "Web tier"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"web-01.example.com" in response.data
    assert b"Web tier" in response.data


def test_remove_server_unregisters_locally(auth_client, tmp_path):
    auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "db-01.example.com"),
        follow_redirects=True,
    )
    dash = auth_client.get("/")
    assert b"db-01.example.com" in dash.data

    response = auth_client.post("/servers/1/remove", follow_redirects=True)
    assert response.status_code == 200
    assert b"db-01.example.com" not in response.data
    assert b"local registry" in response.data.lower() or b"removed" in response.data.lower()


def test_add_rejects_empty_hostname(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "   "),
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert b"required" in response.data.lower()


def test_add_rejects_shell_metacharacters(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "web$01.example.com"),
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert b"invalid characters" in response.data.lower()


def test_add_rejects_invalid_hostname(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "not a valid host name!!!"),
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert b"valid hostname" in response.data.lower()


def test_add_accepts_ipv4(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "10.0.0.5", "Edge"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"10.0.0.5" in response.data


def test_add_accepts_localhost(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "localhost", "Local box"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"localhost" in response.data
    assert b"Local box" in response.data


def test_add_requires_inventory_name(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "host.example.com", label=""),
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert b"inventory name is required" in response.data.lower()


def test_add_requires_ssh_auth(auth_client, tmp_path):
    response = auth_client.post(
        "/servers/add",
        data={
            "hostname": "host.example.com",
            "label": "No auth",
            "ssh_username": "monitor",
            "ssh_password": "",
            "ssh_key_path": "",
            "ssh_port": "22",
        },
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert b"password or a private key" in response.data.lower()


def test_duplicate_hostname_rejected(auth_client, tmp_path):
    auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "dup.example.com"),
        follow_redirects=True,
    )
    response = auth_client.post(
        "/servers/add",
        data=_add_payload(tmp_path, "dup.example.com"),
        follow_redirects=True,
    )
    assert response.status_code == 400
    assert b"already registered" in response.data.lower()
