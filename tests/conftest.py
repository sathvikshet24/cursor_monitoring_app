import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test_monitoring.db"
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "testpass",
            "ADMIN_PASSWORD_HASH": "",
            "DATABASE_PATH": str(db_path),
            # Avoid real SSH during UI tests (no credentials in CI)
            "SSH_USER": "",
            "SSH_KEY_PATH": None,
            "SSH_PASSWORD": None,
            "REFRESH_INTERVAL_MS": 30_000,
        }
    )
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"username": "admin", "password": "testpass"})
    return client
