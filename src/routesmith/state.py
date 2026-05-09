"""Persistent route state - save/load/resume route plans."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from routesmith.types import RoutePlan, TaskResult

_route_counter = 0


def save_route(
    plan: RoutePlan,
    results: list[TaskResult],
    metrics: Any,
    routes_dir: str = ".routesmith/routes",
) -> Path:
    """Save a completed route to the routes directory.

    Returns the path to the saved route file.
    """
    global _route_counter
    _route_counter += 1

    routes_path = Path(routes_dir)
    routes_path.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time() * 1000)
    filename = f"route_{timestamp}_{_route_counter}.json"
    filepath = routes_path / filename

    route_data = {
        "timestamp": timestamp,
        "plan": plan.model_dump(),
        "results": [r.model_dump() for r in results],
        "metrics": metrics.model_dump() if hasattr(metrics, "model_dump") else metrics,
    }

    filepath.write_text(json.dumps(route_data, indent=2, default=str))
    return filepath


def load_route(filepath: str | Path) -> dict[str, Any]:
    """Load a saved route from file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Route file not found: {filepath}")
    return json.loads(path.read_text())


def list_routes(routes_dir: str = ".routesmith/routes") -> list[dict[str, Any]]:
    """List all saved routes with summary info."""
    routes_path = Path(routes_dir)
    if not routes_path.exists():
        return []

    routes: list[dict[str, Any]] = []
    for filepath in sorted(routes_path.glob("route_*.json"), reverse=True):
        try:
            data = json.loads(filepath.read_text())
            routes.append({
                "file": str(filepath),
                "timestamp": data.get("timestamp", 0),
                "prompt": data.get("plan", {}).get("original_prompt", "")[:80],
                "host": data.get("plan", {}).get("host", "unknown"),
                "tasks": len(data.get("results", [])),
                "succeeded": sum(
                    1 for r in data.get("results", []) if r.get("success")
                ),
            })
        except (json.JSONDecodeError, KeyError):
            continue

    return routes


def get_last_route(routes_dir: str = ".routesmith/routes") -> dict[str, Any] | None:
    """Get the most recent saved route."""
    routes = list_routes(routes_dir)
    return routes[0] if routes else None
