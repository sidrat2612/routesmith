"""Install adapters for routesmith."""

from __future__ import annotations

from pathlib import Path

from routesmith.config import load_config
from routesmith.install.base import BaseInstaller
from routesmith.types import InstallResult, SkillConfig


def run_install(
    target: str,
    *,
    root: Path | None = None,
    config: SkillConfig | None = None,
) -> InstallResult:
    """Run install for a given target host."""
    installers: dict[str, type[BaseInstaller]] = _get_installers()

    target_lower = target.lower()
    installer_cls = installers.get(target_lower)

    if installer_cls is None:
        return InstallResult(
            target=target,
            success=False,
            warnings=[f"Unknown target: {target}. Supported: {', '.join(installers.keys())}"],
        )

    installer = installer_cls(root=root, config=config or load_config())
    return installer.install()


def _get_installers() -> dict[str, type[BaseInstaller]]:
    """Get all available installers."""
    from routesmith.install.claude import ClaudeInstaller
    from routesmith.install.codex import CodexInstaller
    from routesmith.install.gemini import GeminiInstaller
    from routesmith.install.copilot import CopilotInstaller
    from routesmith.install.cursor import CursorInstaller
    from routesmith.install.vscode import VSCodeInstaller
    from routesmith.install.aider import AiderInstaller
    from routesmith.install.generic import GenericInstaller

    return {
        "claude": ClaudeInstaller,
        "codex": CodexInstaller,
        "gemini": GeminiInstaller,
        "copilot": CopilotInstaller,
        "cursor": CursorInstaller,
        "vscode": VSCodeInstaller,
        "aider": AiderInstaller,
        "generic": GenericInstaller,
    }
