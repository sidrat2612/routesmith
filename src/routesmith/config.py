"""Configuration loading for routesmith."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from routesmith.types import SkillConfig


def _find_config_file() -> Path | None:
    """Find .routesmith.toml in CWD or parents."""
    cwd = Path.cwd()
    for directory in [cwd, *cwd.parents]:
        config_path = directory / ".routesmith.toml"
        if config_path.exists():
            return config_path
        if directory == Path.home():
            break
    return None


def _parse_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file."""
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return _parse_toml_fallback(path)

    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("routesmith", data)


def _parse_toml_fallback(path: Path) -> dict[str, Any]:
    """Minimal TOML parser for simple key = value files."""
    result: dict[str, Any] = {}
    current_section: list[str] | None = None

    def _parse_value(raw_value: str) -> Any:
        value = raw_value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                return []
            return [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
        value = value.strip('"').strip("'")
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except ValueError:
            return value

    def _get_section_target(section: list[str]) -> dict[str, Any]:
        target = result
        for part in section:
            target = target.setdefault(part, {})
        return target

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            if section_name == "routesmith":
                current_section = []
            elif section_name.startswith("routesmith."):
                current_section = section_name.split(".")[1:]
            else:
                current_section = None
            continue

        if current_section is None:
            continue

        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            _get_section_target(current_section)[key] = _parse_value(value)
    return result


def load_config() -> SkillConfig:
    """Load configuration from .routesmith.toml + environment variables.

    Priority: env vars > config file > defaults.
    """
    file_config: dict[str, Any] = {}
    config_file: str | None = None

    config_path = _find_config_file()
    if config_path:
        file_config = _parse_toml(config_path)
        config_file = str(config_path)

    def _get(key: str, env_var: str, default: Any, cast: type = str) -> Any:
        env_val = os.environ.get(env_var)
        if env_val is not None:
            if cast == bool:
                return env_val.lower() in ("true", "1", "yes")
            if cast == list:
                return [item.strip() for item in env_val.split(",") if item.strip()]
            return cast(env_val)
        if key in file_config:
            return file_config[key]
        return default

    return SkillConfig(
        default_mode=_get("default_mode", "ROUTESMITH_DEFAULT_MODE", "auto"),
        allow_model_switch=_get("allow_model_switch", "ROUTESMITH_ALLOW_MODEL_SWITCH", True, bool),
        routing_preference=_get("routing_preference", "ROUTESMITH_ROUTING_PREFERENCE", "balanced"),
        debug=_get("debug", "ROUTESMITH_DEBUG", False, bool),
        telemetry_enabled=_get("telemetry_enabled", "ROUTESMITH_ENABLE_TELEMETRY", False, bool),
        forced_host=_get("forced_host", "ROUTESMITH_FORCE_HOST", None) or None,
        default_host=_get("default_host", "ROUTESMITH_DEFAULT_HOST", None) or None,
        show_metrics=_get("show_metrics", "ROUTESMITH_SHOW_METRICS", True, bool),
        save_routes=_get("save_routes", "ROUTESMITH_SAVE_ROUTES", False, bool),
        routes_dir=_get("routes_dir", "ROUTESMITH_ROUTES_DIR", ".routesmith/routes"),
        performance_routing_enabled=_get(
            "performance_routing_enabled",
            "ROUTESMITH_PERFORMANCE_ROUTING",
            True,
            bool,
        ),
        performance_store_file=_get(
            "performance_store_file",
            "ROUTESMITH_PERFORMANCE_FILE",
            ".routesmith/performance.json",
        ),
        performance_max_records=_get(
            "performance_max_records",
            "ROUTESMITH_PERFORMANCE_MAX_RECORDS",
            500,
            int,
        ),
        performance_max_age_days=_get(
            "performance_max_age_days",
            "ROUTESMITH_PERFORMANCE_MAX_AGE_DAYS",
            None,
            float,
        ),
        context_window_limit=_get(
            "context_window_limit",
            "ROUTESMITH_CONTEXT_WINDOW_LIMIT",
            True,
            bool,
        ),
        autocompact_threshold=_get(
            "autocompact_threshold",
            "ROUTESMITH_AUTOCOMPACT_THRESHOLD",
            80,
            int,
        ),
        max_spawn_depth=_get(
            "max_spawn_depth",
            "ROUTESMITH_MAX_SPAWN_DEPTH",
            2,
            int,
        ),
        config_file=config_file,
        policy_overrides=file_config.get("policy_overrides", {}),
        policy_plugins=_get("policy_plugins", "ROUTESMITH_POLICY_PLUGINS", [], list),
    )
