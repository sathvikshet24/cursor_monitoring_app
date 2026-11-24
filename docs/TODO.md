# TODO: Demo Linux Server Monitoring

Small increments for AI-assisted development. Complete phases in order. Each phase includes **security** and **docs** checkboxes.

Reference: [requirements.md](./requirements.md)

---

## Phase 1 — Project initialization and basic UI

- [x] Create project layout (`app/`, `templates/`, `static/`, `tests/`, `docs/`)
- [x] Add `requirements.txt` (Flask, and pin versions lightly for the demo)
- [x] Add `.gitignore` (venv, `__pycache__`, `.env`, `*.db`, IDE files)
- [x] Add minimal Flask app that serves a home/dashboard shell page
- [x] Add basic Jinja layout + Bootstrap (CDN) for an attractive read-only shell (nav, title, placeholder content)
- [x] **Security:** Do not commit secrets; add `.env.example` with placeholder keys only; document that `.env` is local-only
- [x] **Docs:** Short `README.md` — what the demo is, how to create venv, install deps, and run `flask run` / `python app.py`

---

## Phase 2 — Sign-in and unit tests

- [x] Add session-based login route (GET/POST) and logout route
- [x] Default username `admin`; password from env; store/compare with Werkzeug password hash
- [x] Protect dashboard (and later APIs) so unauthenticated users are redirected to login
- [x] Add login form UI (username/password) using the existing Bootstrap layout
- [x] Add unit tests: valid login, invalid password, unauthenticated access blocked, logout clears session
- [x] **Security:** Use `SECRET_KEY` from env; hashed password only (never store plaintext); set secure session cookie flags appropriate for local demo (`HttpOnly`; note HTTPS not required for local demo)
- [x] **Docs:** Document `SECRET_KEY`, `ADMIN_USERNAME`/`ADMIN_PASSWORD` (or hash) in `README.md` and `.env.example`

---

## Phase 3 — CI/CD (GitHub Actions)

- [x] Add `.github/workflows/ci.yml`
- [x] On push/PR: install deps, run unit tests (pytest), fail on test failure
- [x] Optionally run a minimal lint step (e.g. `ruff` or `flake8`) if already lightweight to add
- [x] **Security:** CI must not require real secrets; use dummy env vars in the workflow; never echo passwords
- [x] **Docs:** Add a short “CI” section in `README.md` describing what the workflow runs

---

## Phase 4 — SQLite server registry (add / remove hosts)

- [x] Add SQLite model/table for monitored servers (`hostname`/`ip`, optional label, created timestamp)
- [x] Auto-create DB on first run
- [x] Add authenticated form to add a server (hostname or IP required)
- [x] Add authenticated action to remove a server from the local registry
- [x] Show server list on the dashboard (even if metrics are still placeholders)
- [x] Add unit tests for add/remove and auth required for those actions
- [x] **Security:** Validate/sanitize hostname/IP input (reject empty/malicious strings); CSRF protection for forms (Flask-WTF or equivalent simple token); only local DB writes—no remote changes
- [x] **Docs:** Document DB file location, that remove only unregisters locally, and sample add-server flow in `README.md`

---

## Phase 5 — SSH config and safe connection helper

- [x] Add env-based SSH settings (user, key path or password, port, timeout)
- [x] Implement a small SSH helper (e.g. Paramiko) with connection timeout and clear error return
- [x] Add unit tests with mocks (no real SSH in CI)
- [x] **Security:** Read-only remote commands only; never log private keys or passwords; keep credentials in env/files outside git; disable or avoid unknown-host auto-accept in a documented demo-safe way
- [x] **Docs:** Document required SSH env vars and that all targets share one demo credential set

---

## Phase 6 — Collect CPU and memory over SSH

- [x] Run read-only remote commands to gather CPU % and memory used/available
- [x] Show values on dashboard / server detail section
- [x] On SSH failure, show status like “SSH failed” without crashing
- [x] Unit tests with mocked SSH command output
- [x] **Security:** Allowlist exact remote commands (no user-supplied shell strings); treat remote output as untrusted when rendering (escape in Jinja)
- [x] **Docs:** Note which commands are used and that metrics are live snapshots only

---

## Phase 7 — Collect network and ports over SSH

- [x] Gather simple network RX/TX snapshot
- [x] Gather listening/open ports list (`ss`/`netstat` style, read-only)
- [x] Display on server detail area of the single dashboard
- [x] Unit tests with mocked output for network and ports
- [x] **Security:** Keep command allowlist; escape port/process text in UI; no links that trigger remote actions
- [x] **Docs:** Update metrics table in README (CPU, memory, network, ports)

---

## Phase 8 — Live auto-refresh (30 seconds)

- [x] Auto-refresh dashboard metrics every 30 seconds (JS poll of a JSON endpoint or full-page refresh)
- [x] Ensure refresh does not bypass auth
- [x] Basic test or manual checklist for auth on the refresh endpoint
- [x] **Security:** Refresh endpoint requires login; no sensitive SSH errors leaked beyond a safe message
- [x] **Docs:** Document 30s refresh behavior and how to change the interval if needed

---

## Phase 9 — UI polish and demo acceptance pass

- [x] Tighten single-dashboard UX: server list, add/remove, detail metrics, clear empty/error states
- [x] Confirm UI remains metrics-read-only (no destructive remote controls)
- [x] Run through PRD acceptance criteria checklist
- [x] **Security:** Quick review—no secrets in repo, forms protected, outputs escaped, SSH allowlist intact
- [x] **Docs:** Final README pass (setup, env, run, test, CI); keep steps minimal for local Cursor host

---

## Phase order (summary)

1. Init + basic UI  
2. Sign-in + unit tests  
3. GitHub Actions CI  
4. SQLite add/remove servers  
5. SSH helper  
6. CPU + memory  
7. Network + ports  
8. 30s refresh  
9. Acceptance polish  

---

## Out of scope (do not add to this TODO)

Alerts, historical graphs, multi-user/RBAC, HTTPS/production hardening, Docker, Windows hosts, disk/load/uptime metrics.
