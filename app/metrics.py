"""Parse allowlisted SSH command output into dashboard metrics."""

from __future__ import annotations

from typing import Any

from flask import Flask

from app.ssh_client import run_commands, ssh_config_for_server

_METRIC_KEYS = [
    "cpu",
    "memory",
    "disk",
    "network",
    "cpu_count",
    "uptime",
    "kernel",
    "ips",
    "load",
    "top_procs",
]

_SKIP_FS = {
    "tmpfs",
    "devtmpfs",
    "squashfs",
    "overlay",
    "efivarfs",
    "devpts",
    "proc",
    "sysfs",
    "cgroup",
    "cgroup2",
    "pstore",
    "bpf",
    "tracefs",
    "debugfs",
    "securityfs",
    "fusectl",
    "mqueue",
    "hugetlbfs",
    "rpc_pipefs",
    "binfmt_misc",
    "autofs",
    "nsfs",
}


def parse_cpu_percent(proc_stat: str) -> float | None:
    """Compute CPU usage % from a single ``/proc/stat`` cpu line (busy / total)."""
    for line in proc_stat.splitlines():
        if line.startswith("cpu "):
            parts = line.split()
            if len(parts) < 5:
                return None
            try:
                values = [int(x) for x in parts[1:]]
            except ValueError:
                return None
            total = sum(values)
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            if total <= 0:
                return None
            busy = total - idle
            return round(100.0 * busy / total, 1)
    return None


def parse_memory(free_b: str) -> dict[str, Any] | None:
    """Parse ``free -b`` into used/total/available and percent."""
    for line in free_b.splitlines():
        if not line.lower().startswith("mem:"):
            continue
        parts = line.split()
        if len(parts) < 7:
            return None
        try:
            total = int(parts[1])
            used = int(parts[2])
            available = int(parts[6])
        except ValueError:
            return None
        pct = round(100.0 * used / total, 1) if total else None
        return {
            "total_bytes": total,
            "used_bytes": used,
            "available_bytes": available,
            "used_percent": pct,
        }
    return None


def parse_disks(df_out: str) -> list[dict[str, Any]]:
    """Parse ``df -B1 -P`` into real mounted disks (skip virtual filesystems)."""
    disks: list[dict[str, Any]] = []
    seen_mounts: set[str] = set()
    for line in df_out.splitlines():
        if line.lower().startswith("filesystem") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        filesystem = parts[0]
        mount = parts[5]
        fs_name = filesystem.lower()
        if any(fs_name.startswith(skip) or skip in fs_name for skip in _SKIP_FS):
            continue
        if filesystem.startswith("overlay") or mount.startswith("/snap/"):
            continue
        if mount in seen_mounts:
            continue
        try:
            total = int(parts[1])
            used = int(parts[2])
            available = int(parts[3])
        except ValueError:
            continue
        if total <= 0:
            continue
        pct_raw = parts[4].rstrip("%")
        try:
            pct = float(pct_raw)
        except ValueError:
            pct = round(100.0 * used / total, 1)
        seen_mounts.add(mount)
        disks.append(
            {
                "filesystem": filesystem,
                "mount": mount,
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "used_percent": pct,
                "used": format_bytes(used),
                "total": format_bytes(total),
            }
        )
    disks.sort(key=lambda d: (d["mount"] != "/", d["mount"]))
    return disks


def parse_network(proc_net_dev: str) -> dict[str, int] | None:
    """Sum RX/TX bytes across non-loopback interfaces from ``/proc/net/dev``."""
    rx_total = 0
    tx_total = 0
    found = False
    for line in proc_net_dev.splitlines():
        if ":" not in line or line.strip().startswith("Inter") or "face" in line:
            continue
        name, _, rest = line.partition(":")
        iface = name.strip()
        if not iface or iface == "lo":
            continue
        cols = rest.split()
        if len(cols) < 10:
            continue
        try:
            rx_total += int(cols[0])
            tx_total += int(cols[8])
        except ValueError:
            continue
        found = True
    if not found:
        return None
    return {"rx_bytes": rx_total, "tx_bytes": tx_total}


def parse_cpu_count(nproc_out: str) -> int | None:
    text = (nproc_out or "").strip().splitlines()
    if not text:
        return None
    try:
        return int(text[0].strip())
    except ValueError:
        return None


def parse_uptime(proc_uptime: str) -> str | None:
    text = (proc_uptime or "").strip().split()
    if not text:
        return None
    try:
        seconds = int(float(text[0]))
    except ValueError:
        return None
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def parse_kernel(uname_out: str) -> str | None:
    text = (uname_out or "").strip()
    return text or None


def parse_ips(hostname_i: str) -> list[str]:
    return [p for p in (hostname_i or "").split() if p][:6]


def parse_load(loadavg: str) -> str | None:
    parts = (loadavg or "").split()
    if len(parts) < 3:
        return None
    return f"{parts[0]} {parts[1]} {parts[2]}"


def parse_top_procs(ps_out: str, *, limit: int = 3) -> list[dict[str, str]]:
    """Parse ``ps`` output into top CPU processes."""
    rows: list[dict[str, str]] = []
    for line in ps_out.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("pid"):
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, pcpu, pmem, comm = parts
        if not pid.isdigit():
            continue
        rows.append(
            {
                "pid": pid,
                "cpu": pcpu,
                "mem": pmem,
                "name": comm[:64],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def format_bytes(n: int | None) -> str:
    if n is None:
        return "—"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return str(n)


def _empty_metrics(status: str = "SSH failed", error: str | None = "SSH failed") -> dict[str, Any]:
    return {
        "status": status,
        "error": error,
        "cpu_count": None,
        "memory_total_info": None,
        "uptime": None,
        "kernel": None,
        "ips": [],
        "load": None,
        "cpu_percent": None,
        "top_procs": [],
        "memory_percent": None,
        "memory_used": None,
        "memory_total": None,
        "disks": [],
        "network_rx": None,
        "network_tx": None,
    }


def collect_host_metrics(server: dict[str, Any], app: Flask) -> dict[str, Any]:
    """Collect host facts and usage metrics via allowlisted SSH. Never raises."""
    host = server["hostname"]
    config = ssh_config_for_server(server, app)
    results = run_commands(host, _METRIC_KEYS, config)

    ok_cpu, cpu_out = results["cpu"]
    if not ok_cpu:
        return _empty_metrics()

    result = _empty_metrics(status="ok", error=None)
    result["cpu_percent"] = parse_cpu_percent(cpu_out)

    ok_mem, mem_out = results["memory"]
    if not ok_mem:
        return _empty_metrics()
    mem = parse_memory(mem_out)
    if mem:
        result["memory_percent"] = mem["used_percent"]
        result["memory_used"] = format_bytes(mem["used_bytes"])
        result["memory_total"] = format_bytes(mem["total_bytes"])
        result["memory_total_info"] = format_bytes(mem["total_bytes"])

    ok_disk, disk_out = results["disk"]
    if not ok_disk:
        return _empty_metrics()
    result["disks"] = parse_disks(disk_out)

    ok_net, net_out = results["network"]
    if not ok_net:
        return _empty_metrics()
    net = parse_network(net_out)
    if net:
        result["network_rx"] = format_bytes(net["rx_bytes"])
        result["network_tx"] = format_bytes(net["tx_bytes"])

    # Host facts / top processes — best effort
    ok, out = results["cpu_count"]
    if ok:
        result["cpu_count"] = parse_cpu_count(out)

    ok, out = results["uptime"]
    if ok:
        result["uptime"] = parse_uptime(out)

    ok, out = results["kernel"]
    if ok:
        result["kernel"] = parse_kernel(out)

    ok, out = results["ips"]
    if ok:
        result["ips"] = parse_ips(out)

    ok, out = results["load"]
    if ok:
        result["load"] = parse_load(out)

    ok, out = results["top_procs"]
    if ok:
        result["top_procs"] = parse_top_procs(out)

    return result


def attach_metrics(servers: list[dict], app: Flask) -> list[dict]:
    """Return server dicts enriched with a ``metrics`` key (no secrets)."""
    enriched = []
    for server in servers:
        row = {
            "id": server["id"],
            "hostname": server["hostname"],
            "label": server.get("label"),
            "created_at": server.get("created_at"),
            "ssh_username": server.get("ssh_username"),
        }
        row["metrics"] = collect_host_metrics(server, app)
        enriched.append(row)
    return enriched
