"""Unit tests for metrics parsing and SSH collection (mocked)."""

from unittest.mock import patch

from app.metrics import (
    attach_metrics,
    collect_host_metrics,
    parse_cpu_count,
    parse_cpu_percent,
    parse_disks,
    parse_ips,
    parse_kernel,
    parse_load,
    parse_memory,
    parse_network,
    parse_top_procs,
    parse_uptime,
)

SAMPLE_CPU = "cpu  100 0 100 800 0 0 0 0 0 0\n"
SAMPLE_MEM = (
    "              total        used        free      shared  buff/cache   available\n"
    "Mem:     8589934592  4294967296  1073741824           0  3221225472  3221225472\n"
)
SAMPLE_DISK = (
    "Filesystem     1024-blocks      Used Available Capacity Mounted on\n"
    "/dev/sda1     107374182400 53687091200 48318382080      53% /\n"
    "tmpfs            104857600          0  104857600       0% /run\n"
    "/dev/sdb1      21474836480 10737418240  9663676416      50% /data\n"
)
SAMPLE_NET = """Inter-|   Receive                                                Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
  eth0: 2048       20    0    0    0     0          0         0     4096      30    0    0    0     0       0          0
"""
SAMPLE_PROCS = """  PID %CPU %MEM COMMAND
    1  0.0  0.1 systemd
  42  12.5  1.2 python
  99   8.0  0.5 nginx
 100   3.0  0.2 sshd
"""

SERVER = {
    "id": 1,
    "hostname": "10.0.0.1",
    "label": "demo",
    "ssh_username": "monitor",
    "ssh_password": None,
    "ssh_key_path": "/tmp/fake_key",
    "ssh_port": 22,
}


def test_parse_cpu_percent():
    assert parse_cpu_percent(SAMPLE_CPU) == 20.0


def test_parse_memory():
    mem = parse_memory(SAMPLE_MEM)
    assert mem["used_percent"] == 50.0


def test_parse_disks_skips_tmpfs():
    disks = parse_disks(SAMPLE_DISK)
    assert len(disks) == 2
    assert disks[0]["mount"] == "/"
    assert disks[1]["mount"] == "/data"
    assert disks[1]["used_percent"] == 50.0


def test_parse_network():
    assert parse_network(SAMPLE_NET) == {"rx_bytes": 2048, "tx_bytes": 4096}


def test_parse_host_facts():
    assert parse_cpu_count("8\n") == 8
    assert parse_uptime("90061.12 123.4") == "1d 1h 1m"
    assert parse_kernel("6.8.0-generic\n") == "6.8.0-generic"
    assert parse_ips("10.0.0.5 fe80::1") == ["10.0.0.5", "fe80::1"]
    assert parse_load("0.10 0.20 0.30 1/100 1") == "0.10 0.20 0.30"


def test_parse_top_procs():
    procs = parse_top_procs(SAMPLE_PROCS)
    assert len(procs) == 3
    assert procs[0]["name"] == "systemd"
    assert procs[1]["cpu"] == "12.5"


def test_collect_host_metrics_success(app):
    outputs = {
        "cpu": (True, SAMPLE_CPU),
        "memory": (True, SAMPLE_MEM),
        "disk": (True, SAMPLE_DISK),
        "network": (True, SAMPLE_NET),
        "cpu_count": (True, "4\n"),
        "uptime": (True, "3661.0 1.0\n"),
        "kernel": (True, "6.8.0\n"),
        "ips": (True, "10.0.0.8\n"),
        "load": (True, "0.1 0.2 0.3 1/2 3\n"),
        "top_procs": (True, SAMPLE_PROCS),
    }
    with patch("app.metrics.run_commands", return_value=outputs):
        result = collect_host_metrics(SERVER, app)
    assert result["status"] == "ok"
    assert result["cpu_count"] == 4
    assert result["uptime"] == "1h 1m"
    assert result["kernel"] == "6.8.0"
    assert result["ips"] == ["10.0.0.8"]
    assert result["load"] == "0.1 0.2 0.3"
    assert len(result["disks"]) == 2
    assert len(result["top_procs"]) == 3


def test_collect_host_metrics_ssh_failure(app):
    failed = {k: (False, "SSH connection failed") for k in (
        "cpu", "memory", "disk", "network", "cpu_count", "uptime",
        "kernel", "ips", "load", "top_procs",
    )}
    with patch("app.metrics.run_commands", return_value=failed):
        result = collect_host_metrics(SERVER, app)
    assert result["status"] == "SSH failed"


def test_attach_metrics_enriches_servers(app):
    with patch(
        "app.metrics.collect_host_metrics",
        return_value={"status": "ok", "cpu_percent": 1.0},
    ):
        rows = attach_metrics([SERVER], app)
    assert rows[0]["metrics"]["cpu_percent"] == 1.0


def test_api_metrics_requires_login(client):
    response = client.get("/api/metrics")
    assert response.status_code == 302


def test_dashboard_shows_host_details(auth_client):
    with patch(
        "app.routes.attach_metrics",
        return_value=[
            {
                "id": 1,
                "hostname": "host.example.com",
                "label": "Demo",
                "metrics": {
                    "status": "ok",
                    "cpu_count": 8,
                    "memory_total_info": "16.0 GiB",
                    "uptime": "2d 3h 0m",
                    "kernel": "6.8.0",
                    "ips": ["10.0.0.1"],
                    "load": "0.1 0.2 0.3",
                    "cpu_percent": 10.0,
                    "top_procs": [
                        {"pid": "1", "cpu": "1.0", "mem": "0.1", "name": "systemd"}
                    ],
                    "memory_percent": 20.0,
                    "memory_used": "1.0 GiB",
                    "memory_total": "8.0 GiB",
                    "disks": [
                        {
                            "filesystem": "/dev/sda1",
                            "mount": "/",
                            "used_percent": 40.0,
                            "used": "40.0 GiB",
                            "total": "100.0 GiB",
                        }
                    ],
                    "network_rx": "1.0 GiB",
                    "network_tx": "2.0 GiB",
                },
            }
        ],
    ):
        response = auth_client.get("/")
    assert response.status_code == 200
    body = response.data
    assert b"CPUs" in body
    assert b"Uptime" in body
    assert b"Kernel" in body
    assert b"Top processes" in body
    assert b"Disk Usage" in body
    assert b"systemd" in body
