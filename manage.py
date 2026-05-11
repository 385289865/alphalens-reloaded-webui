#!/usr/bin/env python3
"""Alphalens WebUI - Plugin-based Service Management CLI.

Auto-discovers all services from services/definitions/*.py and
services/registry.json.  3rd-party services can register via:
    python manage.py service register <name> <command_dev> --health-check ...

Usage:
    python manage.py service list               List all registered services
    python manage.py service register ...       Register a new service
    python manage.py service unregister <name>  Remove a registered service

    python manage.py start                       Start all services
    python manage.py start --prod                Production mode
    python manage.py stop [service]              Stop one or all services
    python manage.py restart [service]           Restart a service
    python manage.py status                      Show all service health
    python manage.py logs <service>              Tail service logs
    python manage.py ps                          List running processes
    python manage.py health                      Health check all services
    python manage.py db info                     Show DuckDB stats
    python manage.py db reset                    Drop and recreate DuckDB
    python manage.py init                        First-time setup
    python manage.py test                        Run tests
"""

import json
import os
import sys
import time
from pathlib import Path

import click

from services import (
    ServiceDef, PID_DIR, LOG_DIR, ROOT as SVC_ROOT,
    start_service as svc_start,
    stop_service as svc_stop,
    get_status as svc_status,
    _ensure_dirs,
    _pid_file, _read_pid, _is_running,
    _log_file, run_health_check,
)
from services.registry import discover_all, register_service, unregister_service


# ── Paths ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
ALPHALENS_DIR = ROOT / ".alphalens"
LOGS_DIR = ALPHALENS_DIR / "logs"
DB_PATH = ROOT / "db" / "alphalens.db"
RAW_DIR = ROOT / "db" / "raw"
FRONTEND_DIR = ROOT / "frontend"

SERVICES_CACHE = None


def get_services() -> dict[str, ServiceDef]:
    """Get all services (with caching for performance)."""
    global SERVICES_CACHE
    if SERVICES_CACHE is None:
        SERVICES_CACHE = discover_all()
    return SERVICES_CACHE


def invalidate_cache():
    global SERVICES_CACHE
    SERVICES_CACHE = None


def get_service_names() -> list[str]:
    return list(get_services().keys())


def get_sorted_services() -> list[ServiceDef]:
    return list(get_services().values())


# ── CLI Commands ───────────────────────────────────────────────────

@click.group()
def cli():
    """Alphalens WebUI - Service Management CLI."""
    _ensure_dirs()


# ── Service Registry Management ────────────────────────────────────

@cli.group()
def service():
    """Manage the service registry (list / register / unregister)."""


@service.command(name="list")
def service_list():
    """List all registered services with their metadata."""
    svcs = get_sorted_services()
    if not svcs:
        click.echo("No services registered.")
        return

    click.echo(f"{'Name':<16} {'Display Name':<22} {'Order':<8} {'Port':<8} {'Health Check':<30}")
    click.echo("-" * 90)
    for svc in svcs:
        click.echo(
            f"{svc.name:<16} {svc.display_name:<22} {svc.order:<8} "
            f"{svc.port if svc.port else '-':<8} {svc.health_check:<30}"
        )
    click.echo(f"\nTotal: {len(svcs)} services")


@service.command()
@click.argument("name")
@click.argument("command_dev", nargs=-1, required=True)
@click.option("--display-name", default="", help="Human-readable name")
@click.option("--description", default="", help="Service description")
@click.option("--command-prod", multiple=True, type=str, help="Production command tokens (repeatable)")
@click.option("--health-check", default="", help="Health check (tcp:host:port | http:url | file:path)")
@click.option("--depends-on", default="", help="Comma-separated dependency names")
@click.option("--order", default=50, type=int, help="Start order (lower = earlier)")
@click.option("--port", default=0, type=int, help="Service port")
@click.option("--persistent", is_flag=True, help="Runs in background (e.g., database)")
def register(name, command_dev, display_name, description, command_prod,
             health_check, depends_on, order, port, persistent):
    """Register a new service dynamically.

    NAME must be unique. COMMAND_DEV is the command to start the service.
    Example:
        python manage.py service register my-worker --order 35 \\
            --health-check "http:http://localhost:9000/health" \\
            -- python3 -m my_worker.server
    """
    existing = get_services().get(name)
    if existing:
        if not click.confirm(f"Service '{name}' already exists. Override?"):
            return

    svc = ServiceDef(
        name=name,
        display_name=display_name or name,
        description=description,
        command_dev=list(command_dev),
        command_prod=list(command_prod) if command_prod else list(command_dev),
        health_check=health_check,
        depends_on=[d.strip() for d in depends_on.split(",") if d.strip()],
        order=order,
        port=port,
        persistent=persistent,
    )
    result = register_service(svc)
    invalidate_cache()
    click.echo(f"  {result['name']}: {result['status']}")


@service.command()
@click.argument("name")
def unregister(name):
    """Remove a dynamically-registered service by name."""
    result = unregister_service(name)
    invalidate_cache()
    click.echo(f"  {result['name']}: {result['status']}")


# ── Process Management ─────────────────────────────────────────────

@cli.command()
@click.option("--prod", is_flag=True, help="Start in production mode")
@click.option("--test", is_flag=True, hidden=True, help="Test mode (no frontend)")
@click.option("--generate-test-data", is_flag=True,
              help="Generate test CSV files in db/test_data/")
@click.option("--generate-test-db", is_flag=True,
              help="Generate test data AND pre-load into DuckDB")
@click.argument("service_name", required=False, default=None)
def start(prod: bool, test: bool, generate_test_data: bool,
          generate_test_db: bool, service_name: str):
    """Start all services, or a specific service."""
    mode = "prod" if prod else "dev"
    click.echo(f"Alphalens WebUI ({mode} mode)")

    # ── Generate test data ──────────────────────────────────────
    output_dir = "db/test_data"
    if generate_test_data or generate_test_db:
        click.echo("\n── Generating test dataset ──")
        from backend.scripts.generate_test_data import generate_price_factor_dataset
        generate_price_factor_dataset(output_dir=output_dir)

    if generate_test_db:
        click.echo("\n── Loading test data into DuckDB ──")
        from backend.scripts.generate_test_data import load_csv_to_dataframes
        from backend.app.services.data_service import DataService
        from backend.app.config import Settings
        cfg = Settings()
        cfg.DB_PATH = str(DB_PATH)
        cfg.RAW_DATA_DIR = str(RAW_DIR)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if DB_PATH.exists():
            DB_PATH.unlink()
        ds = DataService(db_path=str(DB_PATH))
        session_id = ds.create_session(name="Price Factor Demo")
        factor_df, prices_df = load_csv_to_dataframes(output_dir=output_dir)
        factor_rows = ds.ingest_factor_csv(session_id, factor_df)
        price_rows, asset_count = ds.ingest_prices_csv(session_id, prices_df)
        ds.update_session_stats(
            session_id=session_id,
            row_count_factor=factor_rows,
            row_count_prices=price_rows,
            date_range_start=prices_df.iloc[:, 0].min().date(),
            date_range_end=prices_df.iloc[:, 0].max().date(),
            asset_count=asset_count,
        )
        click.echo(f"  Session: {session_id} ({factor_rows} factor / {price_rows} price rows)")

    # ── Start service(s) ────────────────────────────────────────
    if service_name:
        svc = get_services().get(service_name)
        if not svc:
            click.echo(f"Unknown service '{service_name}'. Use 'manage.py service list'")
            return
        result = svc_start(svc, mode)
        click.echo(f"  {svc.name}: {result}")
        return

    svcs = get_sorted_services()
    click.echo(f"\n── Starting {len(svcs)} services ──")
    for svc in svcs:
        if test and svc.name == "frontend":
            continue
        click.echo(f"  [{svc.order:02d}] {svc.name}: ", nl=False)
        result = svc_start(svc, mode)
        click.echo(result)
        time.sleep(1)

    # ── Health checks ───────────────────────────────────────────
    click.echo("\n── Health checks ──")
    failures = 0
    for svc in svcs:
        if test and svc.name == "frontend":
            continue
        click.echo(f"  {svc.name}: ", nl=False)
        for _ in range(15):
            if run_health_check(svc.health_check):
                click.echo("healthy")
                break
            time.sleep(1)
        else:
            click.echo("NOT healthy")
            failures += 1

    if failures:
        click.echo(f"\n{ failures} service(s) unhealthy. Check logs: python manage.py logs <service>")
    else:
        click.echo("\nAll services healthy.")


@cli.command()
@click.argument("service_name", required=False, default=None)
def stop(service_name: str):
    """Stop one or all services."""
    if service_name:
        result = svc_stop(service_name)
        click.echo(f"  {service_name}: {result}")
        return

    svcs = get_sorted_services()
    for svc in reversed(svcs):
        click.echo(f"  {svc.name}: ", nl=False)
        result = svc_stop(svc.name)
        click.echo(result)


@cli.command()
@click.argument("service_name", required=False, default=None)
def restart(service_name: str):
    """Restart one or all services."""
    if service_name:
        click.echo(f"  {service_name}: ", nl=False)
        click.echo(svc_stop(service_name, force=True))
        svc = get_services().get(service_name)
        if svc:
            click.echo(f"  {service_name}: ", nl=False)
            click.echo(svc_start(svc))
        return

    svcs = get_sorted_services()
    for svc in reversed(svcs):
        svc_stop(svc.name, force=True)
    for svc in svcs:
        click.echo(f"  {svc.name}: ", nl=False)
        click.echo(svc_start(svc))


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(as_json: bool):
    """Show health status of all services."""
    svcs = get_sorted_services()
    results = {}
    for svc in svcs:
        s = svc_status(svc)
        results[svc.name] = s

    if as_json:
        click.echo(json.dumps(results, indent=2, default=str))
        return

    click.echo(f"{'Service':<16} {'PID':<8} {'Running':<10} {'Healthy':<10}")
    click.echo("-" * 44)
    all_healthy = True
    for svc in svcs:
        s = results[svc.name]
        r = "✓" if s["running"] else "✗"
        h = "✓" if s["healthy"] else "✗"
        pid = str(s["pid"]) if s["pid"] else "-"
        click.echo(f"{svc.name:<16} {pid:<8} {r:<10} {h:<10}")
        if not s["healthy"]:
            all_healthy = False

    click.echo("")
    if all_healthy:
        click.echo("All services healthy.")
    else:
        click.echo("Some services are not healthy. Check logs with: python manage.py logs <service>")


@cli.command()
@click.argument("service_name")
@click.option("--lines", default=50, help="Number of lines to show")
def logs(service_name: str, lines: int):
    """Tail logs for a service."""
    log_f = _log_file(service_name)
    if not log_f.exists():
        click.echo(f"No logs found for '{service_name}'")
        return
    click.echo(f"=== {service_name} logs (last {lines} lines) ===")
    content = log_f.read_text().splitlines()
    for line in content[-lines:]:
        click.echo(line)


@cli.command()
def ps():
    """List running processes."""
    svcs = get_sorted_services()
    click.echo(f"{'Service':<16} {'PID':<8} {'Status':<10} {'Uptime':<12}")
    click.echo("-" * 46)
    for svc in svcs:
        s = svc_status(svc)
        if s["running"]:
            try:
                import psutil
                p = psutil.Process(s["pid"])
                uptime = time.time() - p.create_time()
                uptime_str = f"{uptime / 60:.0f}m" if uptime > 60 else f"{uptime:.0f}s"
            except (ImportError, Exception):
                uptime_str = "-"
            click.echo(f"{svc.name:<16} {s['pid']:<8} {'running':<10} {uptime_str:<12}")
        else:
            click.echo(f"{svc.name:<16} {'-':<8} {'stopped':<10} {'-':<12}")


@cli.command()
def health():
    """Run health checks for all services."""
    all_ok = True
    svcs = get_sorted_services()
    for svc in svcs:
        h = run_health_check(svc.health_check)
        status = "✓" if h else "✗"
        click.echo(f"  {svc.name}: {status}")
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
        click.echo("DuckDB not installed.")


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

    click.echo("\n1. Installing backend dependencies...")
    import subprocess
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[web]"],
        cwd=ROOT, capture_output=False,
    )

    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "package.json").exists():
        click.echo("\n2. Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, capture_output=False)
    else:
        click.echo("\n2. Frontend directory not found. Skipping npm install.")

    click.echo("\n3. Creating database directories...")
    os.makedirs(DB_PATH.parent, exist_ok=True)
    os.makedirs(ROOT / "db" / "jobs", exist_ok=True)

    # Show available services
    svcs = discover_all()
    click.echo(f"\n4. Registered services ({len(svcs)}):")
    for name, svc in svcs.items():
        click.echo(f"   - {name}: {svc.display_name} (order={svc.order})")

    click.echo("\nDone. Run 'python manage.py start' to start all services.")


# ── Test Commands ──────────────────────────────────────────────────

@cli.group()
def test():
    """Run tests."""


@test.command()
def contract():
    """Run API contract tests (pytest)."""
    import subprocess
    click.echo("Running API contract tests...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/", "-v", "-x"],
        cwd=ROOT,
    )
    sys.exit(result.returncode)


@test.command()
def e2e():
    """Run E2E Playwright tests."""
    import subprocess
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
    """Run all tests."""
    import subprocess
    click.echo("Running all tests...")
    cov_args = ["--cov=backend", "--cov-report=term"] if coverage else []
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "backend/tests/", "-v"] + cov_args,
        cwd=ROOT,
    )
    sys.exit(r.returncode)


if __name__ == "__main__":
    cli()
