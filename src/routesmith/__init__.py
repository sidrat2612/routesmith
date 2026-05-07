"""routesmith - Host-aware model routing for coding agents and agentic IDE hosts."""

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from routesmith.types import (
    CapabilityClass,
    HostCapabilities,
    HostDetectionResult,
    InstallResult,
    RoutingPreference,
    RoutePlan,
    RunResult,
    SkillConfig,
    TaskNode,
    TaskResult,
    TaskType,
)
from routesmith.executor import Executor
from routesmith.planner import Planner
from routesmith.performance import ModelRecord, ModelStats, PerformanceTracker
from routesmith.policy_plugins import BasePolicyPlugin, PolicyPluginContext, PolicyPluginResult
from routesmith.router import Router
from routesmith.hosts.detector import detect_host, get_host_capabilities


def _read_version_from_pyproject() -> str:
    """Fallback to pyproject.toml when package metadata is unavailable."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        for line in pyproject_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("version = "):
                return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return "0.1.1"


try:
    __version__ = package_version("routesmith")
except PackageNotFoundError:
    __version__ = _read_version_from_pyproject()

__all__ = [
    "run",
    "explain_route",
    "detect_host",
    "get_host_capabilities",
    "serve_stdio",
    "install",
    "CapabilityClass",
    "HostCapabilities",
    "HostDetectionResult",
    "InstallResult",
    "RoutingPreference",
    "RoutePlan",
    "RunResult",
    "SkillConfig",
    "TaskNode",
    "TaskResult",
    "TaskType",
    "BasePolicyPlugin",
    "PolicyPluginContext",
    "PolicyPluginResult",
    "Executor",
    "Planner",
    "ModelRecord",
    "ModelStats",
    "PerformanceTracker",
    "Router",
]


def run(
    prompt: str,
    mode: str = "auto",
    model: str | None = None,
    config: SkillConfig | None = None,
) -> RunResult:
    """Execute a prompt through routesmith's host-aware routing pipeline."""
    executor = Executor(config=config)
    return executor.run(prompt, mode=mode, model=model)


def explain_route(
    prompt: str,
    config: SkillConfig | None = None,
) -> RoutePlan:
    """Explain the route plan for a prompt without executing."""
    executor = Executor(config=config)
    return executor.explain(prompt)


def serve_stdio() -> None:
    """Start the stdio server for tool integration."""
    from routesmith.server.stdio import run_stdio_server
    run_stdio_server()


def install(target: str) -> InstallResult:
    """Install routesmith configuration for a target host."""
    from routesmith.install import run_install
    return run_install(target)
