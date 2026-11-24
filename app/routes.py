"""HTTP routes for the demo monitoring UI."""

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.auth import current_user, login_required, login_user, logout_user, verify_login
from app.metrics import attach_metrics
from app.servers import add_server, list_servers, remove_server
from app.validation import (
    validate_hostname_or_ip,
    validate_label,
    validate_ssh_auth,
    validate_ssh_port,
    validate_ssh_username,
)

bp = Blueprint("main", __name__)

DEFAULT_REFRESH_MS = 30_000


def _dashboard_servers():
    return attach_metrics(list_servers(), current_app)


@bp.route("/")
@login_required
def dashboard():
    refresh_ms = int(current_app.config.get("REFRESH_INTERVAL_MS", DEFAULT_REFRESH_MS))
    return render_template(
        "dashboard.html",
        page_title="Dashboard",
        servers=_dashboard_servers(),
        refresh_ms=refresh_ms,
    )


@bp.route("/api/metrics")
@login_required
def api_metrics():
    """JSON metrics snapshot for auto-refresh. Requires login; no SSH secrets."""
    servers = _dashboard_servers()
    payload = []
    for s in servers:
        m = s.get("metrics") or {}
        payload.append(
            {
                "id": s["id"],
                "hostname": s["hostname"],
                "label": s.get("label"),
                "status": m.get("status"),
                "error": m.get("error"),
                "cpu_count": m.get("cpu_count"),
                "memory_total_info": m.get("memory_total_info"),
                "uptime": m.get("uptime"),
                "kernel": m.get("kernel"),
                "ips": m.get("ips") or [],
                "load": m.get("load"),
                "cpu_percent": m.get("cpu_percent"),
                "top_procs": m.get("top_procs") or [],
                "memory_percent": m.get("memory_percent"),
                "memory_used": m.get("memory_used"),
                "memory_total": m.get("memory_total"),
                "disks": m.get("disks") or [],
                "network_rx": m.get("network_rx"),
                "network_tx": m.get("network_tx"),
            }
        )
    return jsonify(
        {
            "servers": payload,
            "refresh_ms": int(
                current_app.config.get("REFRESH_INTERVAL_MS", DEFAULT_REFRESH_MS)
            ),
        }
    )


@bp.route("/servers/add", methods=["GET", "POST"])
@login_required
def servers_add():
    form = {
        "hostname": "",
        "label": "",
        "ssh_username": "",
        "ssh_password": "",
        "ssh_key_path": "",
        "ssh_port": "22",
    }

    if request.method == "GET":
        return render_template(
            "server_add.html",
            page_title="Add server",
            form=form,
            error=None,
        )

    form = {
        "hostname": (request.form.get("hostname") or "").strip(),
        "label": (request.form.get("label") or "").strip(),
        "ssh_username": (request.form.get("ssh_username") or "").strip(),
        "ssh_password": request.form.get("ssh_password") or "",
        "ssh_key_path": (request.form.get("ssh_key_path") or "").strip(),
        "ssh_port": (request.form.get("ssh_port") or "22").strip(),
    }

    host_err = validate_hostname_or_ip(form["hostname"])
    if host_err:
        return render_template(
            "server_add.html", page_title="Add server", form=form, error=host_err
        ), 400

    label, label_err = validate_label(form["label"], required=True)
    if label_err:
        return render_template(
            "server_add.html", page_title="Add server", form=form, error=label_err
        ), 400

    ssh_user, user_err = validate_ssh_username(form["ssh_username"])
    if user_err:
        return render_template(
            "server_add.html", page_title="Add server", form=form, error=user_err
        ), 400

    ssh_password, ssh_key_path, auth_err = validate_ssh_auth(
        form["ssh_password"], form["ssh_key_path"]
    )
    if auth_err:
        return render_template(
            "server_add.html", page_title="Add server", form=form, error=auth_err
        ), 400

    ssh_port, port_err = validate_ssh_port(form["ssh_port"])
    if port_err:
        return render_template(
            "server_add.html", page_title="Add server", form=form, error=port_err
        ), 400

    ok, err = add_server(
        form["hostname"],
        label,
        ssh_username=ssh_user,
        ssh_password=ssh_password,
        ssh_key_path=ssh_key_path,
        ssh_port=ssh_port or 22,
    )
    if not ok:
        return render_template(
            "server_add.html",
            page_title="Add server",
            form=form,
            error=err or "Could not add server.",
        ), 400

    flash(f"Registered {form['hostname']} for monitoring.", "success")
    return redirect(url_for("main.dashboard"))


@bp.route("/servers/<int:server_id>/remove", methods=["POST"])
@login_required
def servers_remove(server_id: int):
    if remove_server(server_id):
        flash("Server removed from the local registry (remote host unchanged).", "success")
    else:
        flash("Server not found.", "warning")
    return redirect(url_for("main.dashboard"))


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
