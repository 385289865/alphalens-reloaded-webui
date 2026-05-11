"""Service registry — auto-discovers service definitions and provides CRUD.

Services are auto-discovered from:
1. services/definitions/*.py — Python modules exporting a `service` attribute
2. services/registry.json — JSON file for 3rd-party / dynamic registrations
"""

from __future__ import annotations
import importlib.util
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from services import ServiceDef, DEFINITIONS_DIR, REGISTRY_FILE


def _load_python_definitions() -> dict[str, ServiceDef]:
    """Load all .py service definitions from services/definitions/."""
    result = {}
    if not DEFINITIONS_DIR.exists():
        return result

    sys.path.insert(0, str(DEFINITIONS_DIR.parent.parent))  # project root
    for f in sorted(DEFINITIONS_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        mod_name = f"services.definitions.{f.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, f)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "service") and isinstance(mod.service, ServiceDef):
                    svc = mod.service
                    result[svc.name] = svc
        except Exception as e:
            print(f"  [warn] failed to load service '{f.name}': {e}")
    sys.path.pop(0)
    return result


def _load_json_registrations() -> dict[str, ServiceDef]:
    """Load 3rd-party / dynamic registrations from registry.json."""
    result = {}
    if not REGISTRY_FILE.exists():
        return result
    try:
        data = json.loads(REGISTRY_FILE.read_text())
        for entry in data:
            svc = ServiceDef(**entry)
            result[svc.name] = svc
    except Exception as e:
        print(f"  [warn] failed to load registry.json: {e}")
    return result


def discover_all() -> dict[str, ServiceDef]:
    """Discover all services: Python definitions + JSON registrations.

    JSON registrations override Python definitions if names collide.
    Returns ordered dict (by ServiceDef.order).
    """
    services = _load_python_definitions()
    services.update(_load_json_registrations())
    # Sort by order
    return dict(sorted(services.items(), key=lambda item: item[1].order))


def register_service(svc: ServiceDef) -> dict:
    """Register a new service in registry.json (3rd-party / dynamic)."""
    services = _load_json_registrations()
    services[svc.name] = svc
    data = [asdict(s) for s in services.values()]
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(data, indent=2, default=str))
    return {"name": svc.name, "status": "registered"}


def unregister_service(name: str) -> dict:
    """Remove a service from registry.json."""
    services = _load_json_registrations()
    if name not in services:
        return {"name": name, "status": "not_found"}
    del services[name]
    data = [asdict(s) for s in services.values()]
    REGISTRY_FILE.write_text(json.dumps(data, indent=2, default=str))
    return {"name": name, "status": "unregistered"}


def get_service(name: str) -> Optional[ServiceDef]:
    """Get a single service by name."""
    return discover_all().get(name)


def from_dict(d: dict) -> ServiceDef:
    """Create ServiceDef from dict (for JSON deserialization)."""
    return ServiceDef(**d)
