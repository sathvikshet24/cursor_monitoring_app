"""Demo Linux server monitoring application factory."""

import os

from dotenv import load_dotenv
from flask import Flask
from flask_wtf import CSRFProtect

from app.auth import configure_auth
from app.db import close_db, init_db
from app.ssh_client import configure_ssh

csrf = CSRFProtect()


def create_app(test_config: dict | None = None) -> Flask:
    load_dotenv()

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "admin")
    app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "")
    app.config["ADMIN_PASSWORD_HASH"] = os.getenv("ADMIN_PASSWORD_HASH", "")

    default_db = os.getenv("DATABASE_PATH", "")
    if default_db:
        app.config["DATABASE_PATH"] = default_db
    else:
        os.makedirs(app.instance_path, exist_ok=True)
        app.config["DATABASE_PATH"] = os.path.join(app.instance_path, "monitoring.db")

    # Session cookie hardening for local demo (HttpOnly; HTTPS not required locally)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False

    # Env defaults first; test_config may override SSH_* and auth settings
    configure_ssh(app)
    app.config["REFRESH_INTERVAL_MS"] = int(os.getenv("REFRESH_INTERVAL_MS", "30000"))

    if test_config:
        app.config.update(test_config)

    configure_auth(app)
    csrf.init_app(app)
    init_db(app)

    app.teardown_appcontext(close_db)

    from app.routes import bp

    app.register_blueprint(bp)
    return app
