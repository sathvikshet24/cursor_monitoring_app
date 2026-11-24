"""HTTP routes for the demo monitoring UI."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import current_user, login_required, login_user, logout_user, verify_login

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    """Read-only dashboard shell (metrics wired in later phases)."""
    return render_template(
        "dashboard.html",
        page_title="Dashboard",
        servers=[],
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("main.dashboard"))

    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if verify_login(username, password):
            login_user(username)
            flash("Signed in successfully.", "success")
            return redirect(url_for("main.dashboard"))
        error = "Invalid username or password."

    return render_template(
        "login.html",
        page_title="Sign in",
        error=error,
    )


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("main.login"))
