#!/usr/bin/env python3
"""Agent Linux leger pour envoyer les metriques et services au backend Django."""

import argparse
import json
import os
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


AGENT_VERSION = "1.1.0"


def read_first_line(path, default=""):
    try:
        return Path(path).read_text(encoding="utf-8").splitlines()[0]
    except (FileNotFoundError, IndexError, PermissionError):
        return default


def get_primary_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_cpu_usage(interval=0.2):
    def read_cpu():
        values = [int(value) for value in read_first_line("/proc/stat").split()[1:]]
        idle = values[3] + values[4]
        total = sum(values)
        return idle, total

    idle_1, total_1 = read_cpu()
    time.sleep(interval)
    idle_2, total_2 = read_cpu()
    idle_delta = idle_2 - idle_1
    total_delta = total_2 - total_1
    if total_delta <= 0:
        return 0
    return round((1 - idle_delta / total_delta) * 100, 2)


def get_memory_usage():
    values = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw_value = line.split(":", 1)
            values[key] = int(raw_value.strip().split()[0])
    except (FileNotFoundError, PermissionError, ValueError):
        return 0

    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    if not total:
        return 0
    return round(((total - available) / total) * 100, 2)


def get_disk_usage(path="/"):
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bavail * stat.f_frsize
    if not total:
        return 0
    return round(((total - free) / total) * 100, 2)


def get_latency(host="8.8.8.8"):
    started = time.monotonic()
    try:
        with socket.create_connection((host, 53), timeout=2):
            return round((time.monotonic() - started) * 1000, 2)
    except OSError:
        return 999


def command_succeeds(command):
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=3)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def port_is_open(host, port):
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            return True
    except OSError:
        return False


def service_status(name, port=None, host="127.0.0.1"):
    checks = []
    if port:
        checks.append(port_is_open(host, port))
    checks.append(command_succeeds(["systemctl", "is-active", "--quiet", name]))
    checks.append(command_succeeds(["pgrep", "-f", name]))

    return "running" if any(checks) else "stopped"


def parse_services(raw_services):
    services = []
    for raw_item in raw_services.split(","):
        item = raw_item.strip()
        if not item:
            continue

        parts = item.split(":")
        name = parts[0]
        port = int(parts[1]) if len(parts) > 1 and parts[1] else None
        protocol = parts[2] if len(parts) > 2 and parts[2] else "tcp"
        criticality = parts[3] if len(parts) > 3 and parts[3] else "medium"
        services.append(
            {
                "name": name,
                "port": port,
                "protocol": protocol,
                "criticality": criticality,
                "status": service_status(name, port),
            }
        )
    return services


def build_payload(args):
    hostname = args.hostname or socket.gethostname()
    return {
        "hostname": hostname,
        "ip_address": args.ip_address or get_primary_ip(),
        "os_family": platform.platform(),
        "environment": args.environment,
        "owner": args.owner,
        "location": args.location,
        "agent_name": args.agent_name or f"agent-{hostname}",
        "agent_version": AGENT_VERSION,
        "metrics": {
            "cpu_usage": get_cpu_usage(),
            "memory_usage": get_memory_usage(),
            "disk_usage": get_disk_usage(args.disk_path),
            "network_latency": get_latency(args.latency_host),
        },
        "services": parse_services(args.services),
    }


def post_payload(api_url, token, payload):
    request = urllib.request.Request(
        api_url.rstrip("/") + "/agents/ingest/",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Agent-Token": token,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read().decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Agent de monitoring Linux pour Supervision IA.")
    parser.add_argument("--api-url", default=os.getenv("SUPERVISION_API_URL", "http://127.0.0.1:8000/api"))
    parser.add_argument("--token", default=os.getenv("AGENT_INGEST_TOKEN", ""))
    parser.add_argument("--hostname", default=os.getenv("AGENT_HOSTNAME", ""))
    parser.add_argument("--ip-address", default=os.getenv("AGENT_IP_ADDRESS", ""))
    parser.add_argument("--environment", default=os.getenv("AGENT_ENVIRONMENT", "production"))
    parser.add_argument("--owner", default=os.getenv("AGENT_OWNER", ""))
    parser.add_argument("--location", default=os.getenv("AGENT_LOCATION", ""))
    parser.add_argument("--agent-name", default=os.getenv("AGENT_NAME", ""))
    parser.add_argument("--disk-path", default=os.getenv("AGENT_DISK_PATH", "/"))
    parser.add_argument("--latency-host", default=os.getenv("AGENT_LATENCY_HOST", "8.8.8.8"))
    parser.add_argument(
        "--services",
        default=os.getenv("MONITOR_SERVICES", "apache2:80:tcp:critical"),
        help="Format: nom:port:protocole:criticite,exemple apache2:80:tcp:critical",
    )
    parser.add_argument("--once", action="store_true", help="Envoie une seule mesure puis quitte.")
    parser.add_argument("--interval", type=int, default=int(os.getenv("AGENT_INTERVAL", "60")))
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("AGENT_INGEST_TOKEN est obligatoire.")

    while True:
        payload = build_payload(args)
        try:
            status_code, response_body = post_payload(args.api_url, args.token, payload)
            print(f"OK {status_code}: {response_body}")
        except urllib.error.HTTPError as exc:
            print(f"ERREUR HTTP {exc.code}: {exc.read().decode('utf-8')}")
        except urllib.error.URLError as exc:
            print(f"ERREUR RESEAU: {exc.reason}")

        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
