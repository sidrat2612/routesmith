"""Base installer interface."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from routesmith.types import SkillConfig
from routesmith.types import InstallResult


class BaseInstaller(ABC):
    """Abstract base class for install adapters."""

    def __init__(self, root: Path | None = None, config: SkillConfig | None = None) -> None:
        self.root = root or Path.cwd()
        self.config = config or SkillConfig()
        self._warnings: list[str] = []

    @abstractmethod
    def install(self) -> InstallResult:
        """Run the installation."""
        ...

    def _write_file(self, relative_path: str, content: str) -> str:
        """Write a file relative to root. Creates directories as needed."""
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _write_json_file(
        self,
        relative_path: str,
        payload: dict[str, Any],
        *,
        merge: bool = False,
    ) -> str:
        """Write a JSON file relative to root, optionally merging existing content."""
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {}
        if merge and path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    data = existing
            except (OSError, json.JSONDecodeError):
                self._warnings.append(
                    f"Existing {relative_path} is malformed JSON; overwriting with new content."
                )
                data = {}

        data = _deep_merge_dicts(data, payload) if merge else payload
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return str(path)


def _deep_merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge nested dictionaries without discarding unrelated keys."""
    merged: dict[str, Any] = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(existing, value)
        else:
            merged[key] = value
    return merged
