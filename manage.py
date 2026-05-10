#!/usr/bin/env python3
"""Alphalens WebUI - Service Management CLI.

Unified command to start, stop, restart, and monitor all services:
- FastAPI backend (uvicorn)
- Celery worker
- Redis (via docker or system redis-server)
- Vite frontend dev server (npm run dev)

Usage:
    python manage.py start              Start all services (dev mode)
    python manage.py start --prod       Start in production mode
    python manage.py stop               Stop all services gracefully
    python manage.py stop backend       Stop specific service
    python manage.py restart            Restart all services
    python manage.py status             Show health status of all services
    python manage.py logs backend       Tail logs for a service
    python manage.py ps                 List running processes
    python manage.py health             Health check for all services
    python manage.py db info            Show DuckDB stats
    python manage.py db reset           Drop and recreate DuckDB
    python manage.py init               First-time setup
    python manage.py test               Run all tests
    python manage.py test contract      Run API contract tests only
    python manage.py test e2e           Run E2E Playwright tests only
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click

# ── Paths ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
ALPHALENS_DIR = ROOT / ".alphalens"
LOGS_DIR = ALPHALENS_DIR / "logs"
PID_DIR = ALPHALENS_DIR / "pids"
DB_PATH = ROOT / "db" / "alphalens.db"
RAW_DIR = ROOT / "db" / "raw"
FRONTEND_DIR = ROOT / "frontend"

SERVICES_ORDER = ["redis", "backend", "celery", "frontend"]

SERVICE_COMMANDS = {
    "redis": {
        "dev": ["redis-server", "--port", "6379"],
        "prod": ["docker", "run", "--rm", "-p", "6379:6379", "redis:7-alpine"],
        "health": lambda: _tcp_check("localhost", 6379),
    },
    "backend": {
        "dev": [
            sys.executable, "-m", "uvicorn",
            "backend.app.main:app",
            "--host", "0.0.0.0", "--port", "8000", "--reload",
        ],
        "prod": [
            sys.executable, "-m", "uvicorn",
            "backend.app.main:app",
            "--host", "0.0.0.0", "--port", "8000",
            "--workers", "4",
        ],
        "health": lambda: _http_check("http://localhost:8000/api/v1/health"),
    },
    "celery": {
        "dev": [
            sys.executable, "-m", "celery",
            "-A", "backend.app.celery_app", "worker",
            "--loglevel=info", "--concurrency=2",
        ],
        "prod": [
            sys.executable, "-m", "celery",
            "-A", "backend.app.celery_app", "worker",
            "--loglevel=info", "--concurrency=4",
        ],
        "health": lambda: _file_check(DB_PATH),
    },
    "frontend": {
        "dev": ["npm", "run", "dev", "--prefix", str(FRONTEND_DIR)],
        "prod": ["npm", "run", "build", "--prefix", str(FRONTEND_DIR)],
        "health": lambda: _http_check("http://localhost:5173"),
    },
}


# ── Helpers ────────────────────────────────────────────────────────

def _ensure_dirs():
    ALPHALENS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    PID_DIR.mkdir(parents=True, exist_ok=True)
    os.makedirs(DB_PATH.parent, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)


def _pid_file(service: str) -> Path:
    return PID_DIR / f"{service}.pid"


def _log_file(service: str) -> Path:
    return LOGS_DIR / f"{service}.log"


def _save_pid(service: str, pid: int):
    _pid_file(service).write_text(str(pid))


def _read_pid(service: str) -> Optional[int]:
    pf = _pid_file(service)
    if pf.exists():
        try:
            return int(pf.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def _remove_pid(service: str):
    _pid_file(service).unlink(missing_ok=True)


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    import socket
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (OSError, socket.error):
        return False


def _http_check(url: str, timeout: float = 3.0) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def _file_check(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _start_service(service: str, mode: str = "dev"):
    """Launch a service as a subprocess with PID tracking and logging."""
    if _get_service_status(service)["running"]:
        click.echo(f"  {service}: already running (PID {_read_pid(service)})")
        return

    cmd_info = SERVICE_COMMANDS[service]
    cmd = cmd_info[mode]
    log_f = _log_file(service)

    click.echo(f"  {service}: starting... ", nl=False)

    try:
        with open(log_f, "a") as log:
            proc = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=log,
                cwd=ROOT,
                start_new_session=True,
            )
        _save_pid(service, proc.pid)
        click.echo(f"PID {proc.pid}")
    except FileNotFoundError as e:
        click.echo(f"FAILED - {e}")


def _stop_service(service: str, force: bool = False):
    """Stop a service gracefully, then force kill after timeout."""
    status = _get_service_status(service)
    if not status["running"]:
        click.echo(f"  {service}: not running")
        return

    pid = status["pid"]
    click.echo(f"  {service}: stopping PID {pid}... ", nl=False)

    # Try graceful shutdown
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(25):  # 5s timeout
            if not _is_running(pid):
                click.echo("stopped")
                _remove_pid(service)
                return
            time.sleep(0.2)
        # Force kill
        if force or click.confirm("Graceful shutdown timeout. Force kill?", default=True):
            os.kill(pid, signal.SIGKILL)
            click.echo("force killed")
        else:
            click.echo("timeout")
    except ProcessLookupError:
        click.echo("not found")
    finally:
        _remove_pid(service)


def _get_service_status(service: str) -> dict:
    pid = _read_pid(service)
    running = pid is not None and _is_running(pid)
    health_fn = SERVICE_COMMANDS[service]["health"]
    return {
        "service": service,
        "pid": pid,
        "running": running,
        "healthy": health_fn() if running else False,
    }


# ── CLI Commands ───────────────────────────────────────────────────

@click.group()
def cli():
    """Alphalens WebUI - Service Management CLI."""
    _ensure_dirs()


@cli.command()
@click.option("--prod", is_flag=True, help="Start in production mode")
@click.option("--test", is_flag=True, hidden=True, help="Start in test mode (no frontend)")
def start(prod: bool, test: bool):
    """Start all services in order: redis → backend → celery → frontend."""
    mode = "prod" if prod else "dev"
    click.echo(f"Starting Alphalens WebUI ({mode} mode)...")

    for svc in SERVICES_ORDER:
        if test and svc == "frontend":
            continue  # Skip frontend in test mode
        _start_service(svc, mode)
        time.sleep(1)

    click.echo("\nWaiting for services to become healthy...")
    for svc in SERVICES_ORDER:
        if test and svc == "frontend":
            continue
        health_fn = SERVICE_COMMANDS[svc]["health"]
        for i in range(15):
            if health_fn():
                click.echo(f"  {svc}: healthy")
                break
            time.sleep(1)
        else:
            click.echo(f"  {svc}: NOT healthy (check logs)")

    click.echo("\nDone. Use 'python manage.py status' to check all services.")


@cli.command()
@click.argument("service", type=click.Choice(SERVICES_ORDER + ["all"]), default="all")
def stop(service: str):
    """Stop one or all services (reverse order)."""
    svcs = SERVICES_ORDER[::-1] if service == "all" else [service]
    for svc in svcs:
        _stop_service(svc)


@cli.command()
@click.argument("service", type=click.Choice(SERVICES_ORDER + ["all"]), default="all")
def restart(service: str):
    """Restart one or all services."""
    svcs = SERVICES_ORDER[::-1] if service == "all" else [service]
    for svc in svcs:
        _stop_service(svc, force=True)
    for svc in (svcs[::-1] if service != "all" else SERVICES_ORDER):
        _start_service(svc)


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(as_json: bool):
    """Show health status of all services."""
    results = {}
    for svc in SERVICES_ORDER:
        s = _get_service_status(svc)
        results[svc] = s

    if as_json:
        click.echo(json.dumps(results, indent=2, default=str))
        return

    click.echo(f"{'Service':<12} {'PID':<8} {'Running':<10} {'Healthy':<10}")
    click.echo("-" * 42)
    all_healthy = True
    for svc in SERVICES_ORDER:
        s = results[svc]
        r = "✓" if s["running"] else "✗"
        h = "✓" if s["healthy"] else "✗"
        pid = str(s["pid"]) if s["pid"] else "-"
        click.echo(f"{svc:<12} {pid:<8} {r:<10} {h:<10}")
        if not s["healthy"]:
            all_healthy = False

    click.echo("")
    if all_healthy:
        click.echo("All services healthy.")
    else:
        click.echo("Some services are not healthy. Check logs with: python manage.py logs <service>")


@cli.command()
@click.argument("service", type=click.Choice(SERVICES_ORDER))
@click.option("--lines", default=50, help="Number of lines to show")
def logs(service: str, lines: int):
    """Tail logs for a service."""
    log_f = _log_file(service)
    if not log_f.exists():
        click.echo(f"No logs found for {service}")
        return
    click.echo(f"=== {service} logs (last {lines} lines) ===")
    content = log_f.read_text().splitlines()
    for line in content[-lines:]:
        click.echo(line)


@cli.command()
def ps():
    """List running processes managed by alphalensctl."""
    click.echo(f"{'Service':<12} {'PID':<8} {'Status':<10} {'Uptime':<12}")
    click.echo("-" * 44)
    for svc in SERVICES_ORDER:
        s = _get_service_status(svc)
        if s["running"]:
            try:
                import psutil
                p = psutil.Process(s["pid"])
                uptime = time.time() - p.create_time()
                uptime_str = f"{uptime / 60:.0f}m" if uptime > 60 else f"{uptime:.0f}s"
            except (ImportError, psutil.NoSuchProcess):
                uptime_str = "-"
            click.echo(f"{svc:<12} {s['pid']:<8} {'running':<10} {uptime_str:<12}")
        else:
            click.echo(f"{svc:<12} {'-':<8} {'stopped':<10} {'-':<12}")


@cli.command()
def health():
    """Run health checks for all services."""
    all_ok = True
    for svc in SERVICES_ORDER:
        h = SERVICE_COMMANDS[svc]["health"]()
        status = "✓" if h else "✗"
        click.echo(f"  {svc}: {status}")
        if not h:
            all_ok = False
    return 0 if all_ok else 1


# ── DB Commands ────────────────────────────────────────────────────

@cli.group()
def db():
    """Database management commands."""


@db.command()
def info():
    """Show DuckDB database info."""
    if not DB_PATH.exists():
        click.echo("Database does not exist yet.")
        return
    try:
        import duckdb
        conn = duckdb.connect(str(DB_PATH))
        size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        click.echo(f"Database: {DB_PATH}")
        click.echo(f"Size: {size_mb:.2f} MB")

        tables = conn.execute(
            "SELECT table_name, (SELECT count(*) FROM information_schema.columns "
            "WHERE table_name = t.table_name AND table_schema = 'main') as cols "
            "FROM (SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main') t ORDER BY table_name"
        ).fetchall()
        click.echo(f"\nTables ({len(tables)}):")
        for tbl, cols in tables:
            try:
                row_count = conn.execute(f"SELECT count(*) FROM \"{tbl}\"").fetchone()[0]
                click.echo(f"  {tbl:<35} {row_count:>8} rows  {cols} cols")
            except Exception:
                click.echo(f"  {tbl:<35} {'?':>8} rows  {cols} cols")
        conn.close()
    except ImportError:
        click.echo("DuckDB not installed. Install with: pip install duckdb")


@db.command()
@click.confirmation_option(prompt="This will delete ALL data. Continue?")
def reset():
    """Drop and recreate the DuckDB database."""
    if DB_PATH.exists():
        DB_PATH.unlink()
        click.echo("Database deleted.")
    click.echo("Database will be recreated on next service start.")


# ── Init Command ───────────────────────────────────────────────────

@cli.command()
def init():
    """First-time setup: install dependencies, create directories."""
    click.echo("Initializing Alphalens WebUI...")
    _ensure_dirs()

    # Backend dependencies
    click.echo("\n1. Installing backend dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[web]"],
        cwd=ROOT, capture_output=False,
    )

    # Frontend dependencies
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "package.json").exists():
        click.echo("\n2. Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, capture_output=False)
    else:
        click.echo("\n2. Frontend directory not found. Skipping npm install.")

    click.echo("\n3. Creating database directory...")
    os.makedirs(DB_PATH.parent, exist_ok=True)

    click.echo("\nDone. Run 'python manage.py start' to start all services.")


# ── Test Commands ──────────────────────────────────────────────────

@cli.group()
def test():
    """Run tests."""


@test.command()
def contract():
    """Run API contract tests (pytest)."""
    click.echo("Running API contract tests...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/", "-v", "-x"],
        cwd=ROOT,
    )
    sys.exit(result.returncode)


@test.command()
def e2e():
    """Run E2E Playwright tests."""
    e2e_dir = ROOT / "e2e"
    if not (e2e_dir / "playwright.config.ts").exists():
        click.echo("E2E tests not configured. Skipping.")
        return
    click.echo("Running E2E tests...")
    result = subprocess.run(
        ["npx", "playwright", "test", "--config", "e2e/playwright.config.ts"],
        cwd=ROOT,
    )
    sys.exit(result.returncode)


@test.command()
@click.option("--coverage", is_flag=True, help="Run with coverage")
def all_tests(coverage: bool):
    """Run all tests: contract + frontend + e2e."""
    click.echo("Running all tests...")
    errors = 0

    # API Contract tests
    click.echo("\n=== API Contract Tests ===")
    cov_args = ["--cov=backend", "--cov-report=term"] if coverage else []
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/", "-v"] + cov_args,
        cwd=ROOT,
    )
    if r.returncode != 0:
        errors += 1

    sys.exit(errors)


if __name__ == "__main__":
    cli()
