# Demo Linux Server Monitoring

Local Flask demo for viewing Linux host metrics (CPU, memory, network, ports) without SSH’ing into each server. Built for internal L1/L2/L3 and app teams.

See [docs/requirements.md](docs/requirements.md) and [docs/TODO.md](docs/TODO.md).

## Quick start (local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set SECRET_KEY and ADMIN_PASSWORD
python run.py
```

Or:

```bash
export FLASK_APP=run.py
flask run
```

Open http://127.0.0.1:5000/ — you will be redirected to **/login**.

Default username: `admin` (password from `ADMIN_PASSWORD` in `.env`).  
If `ADMIN_PASSWORD` is unset, the demo fallback password is `admin`.

## Tests

```bash
source .venv/bin/activate
pytest
```

## Security notes

- Copy `.env.example` → `.env`. **Do not commit `.env`.**
- `SECRET_KEY` must be set for sessions.
- Admin password is hashed with Werkzeug (`generate_password_hash` / `check_password_hash`); plaintext is not kept in app config after startup.
- Session cookies use `HttpOnly` and `SameSite=Lax`. `Secure` is off for local HTTP demo (no HTTPS required).
