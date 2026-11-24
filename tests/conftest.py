import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "testpass",
            "ADMIN_PASSWORD_HASH": "",
        }
    )
    yield application


@pytest.fixture
def client(app):
    return app.test_client()
