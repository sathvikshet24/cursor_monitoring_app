def test_unauthenticated_dashboard_redirects_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_valid_login_reaches_dashboard(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "testpass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Monitoring" in response.data
    assert b"Servers" in response.data
    assert b"Live metrics" in response.data


def test_invalid_password_rejected(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    blocked = client.get("/")
    assert blocked.status_code == 302
    assert "/login" in blocked.headers["Location"]


def test_logout_clears_session(client):
    client.post("/login", data={"username": "admin", "password": "testpass"})
    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Sign in" in response.data
    blocked = client.get("/")
    assert blocked.status_code == 302
    assert "/login" in blocked.headers["Location"]
