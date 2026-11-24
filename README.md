# Demo Linux Server Monitoring

Local Flask demo for viewing Linux host metrics (CPU, memory, network, ports) without SSH’ing into each server. Built for internal L1/L2/L3 and app teams.

See [docs/requirements.md](docs/requirements.md) and [docs/TODO.md](docs/TODO.md).

## Quick start (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set SECRET_KEY, ADMIN_PASSWORD, and SSH_* settings
python run.py
```

Or:

```bash
export FLASK_APP=run.py
flask run
```

Open http://127.0.0.1:6352/ (default `run.py` port) — you will be redirected to **/login**.

Default username: `admin` (password from `ADMIN_PASSWORD` in `.env`).  
If `ADMIN_PASSWORD` is unset, the demo fallback password is `admin`.

## SSH (demo credential set)

All monitored servers use the **same** SSH identity configured in `.env` (typical internal demo: one jump/read-only account):

| Variable | Purpose |
|----------|---------|
| `SSH_USER` | Remote login user |
| `SSH_PORT` | SSH port (default `22`) |
| `SSH_TIMEOUT` | Connect/command timeout in seconds |
| `SSH_KEY_PATH` | Path to private key file (preferred) |
| `SSH_PASSWORD` | Password auth if no key (avoid committing) |
| `SSH_STRICT_HOST_KEY` | `true` (default): reject unknown host keys (`RejectPolicy`). Set `false` only for a local lab to allow `AutoAddPolicy`. |

Remote commands are **read-only** and chosen from a fixed allowlist in `app/ssh_client.py` — never pass arbitrary shell from the UI.

### Metrics collected (live snapshots only)

| Metric | Allowlist key | Remote command | Display |
|--------|---------------|----------------|---------|
| CPU | `cpu` | `grep 'cpu ' /proc/stat` | Usage % (busy/total from counters) |
| Memory | `memory` | `free -b` | Used / available (+ %) |
| Network | `network` | `cat /proc/net/dev` | RX/TX byte counters (non-loopback) |
| Ports | `ports` | `ss -tuln` | Listening/open sockets |

Values are point-in-time snapshots, not historical charts. Unreachable hosts show **SSH failed** without crashing the UI.

## Auto-refresh

The dashboard polls `/api/metrics` every **30 seconds** (requires login). Change the interval with `REFRESH_INTERVAL_MS` in `.env` (milliseconds; default `30000`).

## Tests

```bash
source .venv/bin/activate
pytest
```

## CI

GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every **push** and **pull request**:

1. Checkout the repo and set up Python 3.12
2. Install dependencies from `requirements.txt`
3. Run **ruff** lint (`ruff check .`) — ruff is installed in CI only, not listed in `requirements.txt`
4. Run **pytest**

The job uses dummy `SECRET_KEY` and `ADMIN_PASSWORD` values for the environment (no real secrets). Unit tests override config via `tests/conftest.py`, so CI does not need your local `.env`.

## Server registry (SQLite)

On first run the app creates a SQLite database for the **local** monitored-server list only. By default the file is:

`app/instance/monitoring.db` (relative to the project root; the `instance/` folder is gitignored).

Override with `DATABASE_PATH` in `.env` (see `.env.example`).

### Add / remove flow

1. Sign in as `admin`.
2. On the dashboard, click **Add server** (opens `/servers/add`).
3. Fill in hostname/IP, inventory name, SSH username, and either an SSH password **or** absolute private key path (and port if not 22).
4. Submit — the host appears on the dashboard with live metrics collected using those per-host credentials.
5. **Remove** deletes the row from SQLite only; it does **not** change the remote Linux host.

Example for this machine (key-based localhost): hostname `127.0.0.1`, inventory name `Local demo`, SSH username your Linux user, key path `/home/<you>/.ssh/id_ed25519`. Ensure `sshd` is running and your key is in `~/.ssh/authorized_keys`. Keep `SSH_STRICT_HOST_KEY=false` for local lab host-key auto-add.

Forms use Flask-WTF CSRF protection. The UI is metrics-read-only — no destructive remote actions. Per-host SSH secrets stay in the local DB only and are never shown in the metrics API.

## Security notes

- Copy `.env.example` → `.env`. **Do not commit `.env`.**
- `SECRET_KEY` must be set for sessions.
- Admin password is hashed with Werkzeug (`generate_password_hash` / `check_password_hash`); plaintext is not kept in app config after startup.
- Session cookies use `HttpOnly` and `SameSite=Lax`. `Secure` is off for local HTTP demo (no HTTPS required).
- Server hostname/IP inputs are validated (no shell metacharacters; hostname or IPv4/IPv6). CSRF tokens protect POST forms.
- SSH private keys and passwords live only in `.env` / local files; the app does not log credentials. Use `SSH_STRICT_HOST_KEY=true` unless you understand the risk of auto-accepting host keys in your lab.
- Remote command strings are allowlisted; Jinja escapes untrusted remote text when rendering.
