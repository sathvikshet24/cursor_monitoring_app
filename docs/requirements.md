# PRD: Demo Linux Server Monitoring

## 1. Overview

Local demo web app for internal L1/L2/L3 and app teams to view **real-time Linux server metrics** without SSH’ing into each host.

**Problem:** Operators must log into servers to check CPU, memory, network, and port usage.

**Goal:** A read-only Flask UI that collects metrics over SSH and refreshes every 30 seconds.

---

## 2. Users

| Who | Need |
|-----|------|
| L1 / L2 / L3, infra & app teams | View live metrics in a browser |
| Admin (`admin`) | Sign in; add/remove monitored Linux servers |

Single account only. No roles beyond admin.

---

## 3. Scope

### In scope

- Login with username `admin` and a hashed password
- Add/remove Linux servers (hostname or IP)
- Collect via **SSH from the monitoring app**: CPU %, memory used/available, network I/O, listening/open ports
- Read-only metrics UI (no remote commands that change server state)
- Single dashboard: server list + detail view
- Auto-refresh every **30 seconds**
- Local run: Python + Flask + Jinja + Bootstrap (or similar), SQLite for server registry

### Out of scope

- Alerts, history/graphs, multi-user/RBAC, HTTPS, Docker, Windows hosts, disk/load/uptime metrics

---

## 4. Features

### F1 — Read-only, user-friendly UI

- Attractive, simple layout (Bootstrap or equivalent)
- Metrics and ports are view-only
- Allowed writes: add/remove entries in the **local** monitored-server list (does not modify remote hosts)

### F2 — Admin sign-in

- Default username: `admin`
- Password stored as a hash (e.g. Werkzeug/`generate_password_hash`)
- Configure initial password via env or config for local demo
- Unauthenticated users cannot see metrics or manage servers

### F3 — Add Linux servers to monitor

- Fields: **hostname or IP** (required)
- Optional display name/label if useful for the demo
- Stored in SQLite
- Admin can remove a server from monitoring
- App connects over SSH to collect metrics (credentials/key via local env/config—not entered per request in the UI for minimal demo)

### F4 — Live metrics (auto-refresh 30s)

Per reachable server, show:

| Metric | Display |
|--------|---------|
| CPU | Usage % |
| Memory | Used / available (and % if easy) |
| Network | RX/TX (simple counters or rates) |
| Ports | Listening/open ports list |

- Dashboard auto-refreshes every 30 seconds (JS poll or meta refresh)
- Unreachable hosts: clear error/status (e.g. “SSH failed”) without crashing the UI

---

## 5. UX (minimal)

1. **Login** → username/password
2. **Dashboard** → list of servers with high-level status / CPU & memory snapshot
3. **Server detail** (same page expand or simple detail section) → full metrics + ports
4. **Add server** form (hostname/IP) + remove action

---

## 6. Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3 |
| Web | Flask + Jinja2 |
| UI | Bootstrap (or similar CDN CSS) |
| DB | SQLite (server registry) |
| Auth | Session cookie + hashed password |
| Collect | SSH from app host (e.g. Paramiko) to run read-only remote checks |

---

## 7. Local deploy (minimal)

1. Create venv and `pip install -r requirements.txt`
2. Set env (examples): `SECRET_KEY`, `ADMIN_PASSWORD` (or pre-hashed), SSH user/key path for target hosts
3. Initialize SQLite (auto on first run is fine)
4. Run: `flask run` (or `python app.py`) on localhost
5. Open UI → sign in as `admin` → add a Linux hostname/IP → view metrics

No Docker, no production hardening required for this demo.

---

## 8. Non-functional (demo-level)

- Runs on the machine where Cursor/local Python runs
- Prefer clarity over scale; a handful of servers is enough
- SSH collection is best-effort; timeouts should fail gracefully
- No requirement for historical retention

---

## 9. Acceptance criteria

- [ ] Login works only with `admin` + correct password (hash verified)
- [ ] Logged-out users cannot access dashboard or server management
- [ ] Admin can add a Linux host by hostname/IP and remove it
- [ ] Dashboard shows CPU, memory, network, and ports for reachable hosts
- [ ] UI refreshes metrics about every 30 seconds
- [ ] Metrics UI does not offer destructive remote actions
- [ ] App starts locally with venv + Flask and SQLite

---

## 10. Open assumptions

- All monitored hosts share the same SSH credentials configured on the app host (demo simplicity).
- “Ports” means listening TCP/UDP sockets visible via a read-only remote command (e.g. `ss`/`netstat`).
- Network metrics are a simple live snapshot, not historical charts.
