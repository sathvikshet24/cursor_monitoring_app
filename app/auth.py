"""Authentication helpers for the single admin demo account."""

from functools import wraps

from flask import current_app, flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def configure_auth(app) -> None:
    """Load admin credentials from env into app config (hashed password only)."""
    username = app.config.get("ADMIN_USERNAME") or "admin"
    password = app.config.get("ADMIN_PASSWORD") or ""
    password_hash = app.config.get("ADMIN_PASSWORD_HASH") or ""

    if password_hash:
        stored_hash = password_hash
    elif password:
        stored_hash = generate_password_hash(password)
    else:
        # Local demo fallback — change via ADMIN_PASSWORD in .env
        stored_hash = generate_password_hash("admin")

    app.config["ADMIN_USERNAME"] = username
    app.config["ADMIN_PASSWORD_HASH"] = stored_hash
    # Drop plaintext from config after hashing
    app.config.pop("ADMIN_PASSWORD", None)


def verify_login(username: str, password: str) -> bool:
    expected_user = current_app.config["ADMIN_USERNAME"]
    password_hash = current_app.config["ADMIN_PASSWORD_HASH"]
    if username != expected_user:
        return False
    return check_password_hash(password_hash, password)


def login_user(username: str) -> None:
    session.clear()
    session["user"] = username
    session.permanent = False


def logout_user() -> None:
    session.clear()


def current_user() -> str | None:
    return session.get("user")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped
