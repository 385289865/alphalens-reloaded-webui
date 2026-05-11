"""Service management framework.

Each service is defined as a ServiceDef instance in services/definitions/.
The registry auto-discovers all definitions and provides CRUD operations.
"""

from __future__ import annotations
import json
import os
import signal
import subprocess
import sys
import time
import socket
import urllib.request
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional


ROOT = Path(__file__).resolve().parent.parent
DEFINITIONS_DIR = ROOT / "services" / "definitions"
REGISTRY_FILE = ROOT / "services" / "registry.json"
PID_DIR = ROOT / ".alphalens" / "pids"
LOG_DIR = ROOT / ".alphalens" / "logs"


@dataclass
class ServiceDef:
    """Definition of a managed service."""
    name: str
    display_name: str = ""
    description: str = ""
    command_dev: list[str] = field(default_factory=list)
    command_prod: list[str] = field(default_factory=list)
    health_check: str = ""  # "tcp:host:port", "http:url", "file:path"
    depends_on: list[str] = field(default_factory=list)
    order: int = 50  # lower = starts earlier
    port: int = 0
    persistent: bool = False  # False = runs in foreground in dev mode


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (OSError, OSError):
        return False


def _http_check(url: str, timeout: float = 3.0) -> bool:
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def _file_check(path: str) -> bool:
    return Path(path).expanduser().exists()


def run_health_check(check: str) -> bool:
    """Run a health check string. Format: tcp:host:port, http:url, file:path."""
    if not check:
        return True
    if check.startswith("tcp:"):
        parts = check.split(":")
        return _tcp_check(parts[1], int(parts[2]))
    if check.startswith("http:"):
        return _http_check(check[5:])
    if check.startswith("file:"):
        return _file_check(check[5:])
    return True


# ── PID / Process Management ─────────────────────────────────────────

def _ensure_dirs():
    PID_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _pid_file(name: str) -> Path:
    return PID_DIR / f"{name}.pid"


def _log_file(name: str) -> Path:
    return LOG_DIR / f"{name}.log"


def _save_pid(name: str, pid: int):
    _pid_file(name).write_text(str(pid))


def _read_pid(name: str) -> Optional[int]:
    pf = _pid_file(name)
    if pf.exists():
        try:
            return int(pf.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def _remove_pid(name: str):
    _pid_file(name).unlink(missing_ok=True)


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def start_service(svc: ServiceDef, mode: str = "dev"):
    """Launch a service as a subprocess with PID tracking."""
    pid = _read_pid(svc.name)
    if pid and _is_running(pid):
        return f"already running (PID {pid})"

    cmd = svc.command_prod if mode == "prod" else svc.command_dev
    if not cmd:
        return "no command defined"

    log_f = _log_file(svc.name)
    _ensure_dirs()

    try:
        with open(log_f, "a") as log:
            proc = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=log,
                cwd=ROOT,
                start_new_session=True,
            )
        _save_pid(svc.name, proc.pid)
        return f"started (PID {proc.pid})"
    except FileNotFoundError as e:
        return f"FAILED - {e}"


def stop_service(name: str, force: bool = False) -> str:
    """Stop a service."""
    pid = _read_pid(name)
    if not pid or not _is_running(pid):
        _remove_pid(name)
        return "not running"

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(25):
            if not _is_running(pid):
                _remove_pid(name)
                return "stopped"
            time.sleep(0.2)
        os.kill(pid, signal.SIGKILL)
        _remove_pid(name)
        return "force killed"
    except ProcessLookupError:
        _remove_pid(name)
        return "not found"


def get_status(svc: ServiceDef) -> dict:
    """Get running status of a service."""
    pid = _read_pid(svc.name)
    running = pid is not None and _is_running(pid)
    healthy = run_health_check(svc.health_check) if running else False
    return {
        "name": svc.name,
        "display_name": svc.display_name or svc.name,
        "pid": pid,
        "running": running,
        "healthy": healthy,
        "order": svc.order,
    }
