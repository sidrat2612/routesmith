"""Aider host adapter."""

from __future__ import annotations

import os
from pathlib import Path

from routesmith.hosts.base import BaseHostAdapter
from routesmith.types import (
    CapabilityClass,
    HostCapabilities,
    HostDetectionResult,
    TaskNode,
)


class AiderHostAdapter(BaseHostAdapter):
    """Adapter for Aider coding assistant."""

    MODEL_MAP: dict[CapabilityClass, str] = {
        CapabilityClass.DEEP_REASONING: "claude-opus-4-7",
        CapabilityClass.CODING: "gpt-5.3-codex",
        CapabilityClass.BALANCED: "claude-sonnet-4-6",
        CapabilityClass.FAST: "claude-haiku-4-5",
    }

    AVAILABLE_MODELS = [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
        "gpt-5.5",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.3-codex",
        "gemini-3.1-pro",
    ]

    def detect(self) -> HostDetectionResult:
        """Detect Aider environment."""
        confidence = 0.0
        method_parts: list[str] = []

        if os.environ.get("AIDER_ENV") or os.environ.get("AIDER"):
            confidence += 0.5
            method_parts.append("AIDER env")

        # Check for .aider files
        cwd = Path.cwd()
        if (cwd / ".aider.conf.yml").exists():
            confidence += 0.3
            method_parts.append(".aider.conf.yml")

        if (cwd / ".aiderignore").exists():
            confidence += 0.2
            method_parts.append(".aiderignore")

        return HostDetectionResult(
            host_name="aider",
            confidence=min(confidence, 1.0),
            detection_method=", ".join(method_parts) if method_parts else "none",
            root_path=str(cwd),
        )

    def get_capabilities(self) -> HostCapabilities:
        """Get Aider capabilities."""
        return HostCapabilities(
            host_name="aider",
            detected=self.detect().confidence > 0.3,
            current_model=self._detect_current_model(),
            available_models=self.AVAILABLE_MODELS,
            supports_dynamic_switch=True,
            supports_prompt_files=False,
            supports_repo_instructions=True,
            supports_settings_edit=True,
            supports_env_override=True,
            supports_context_management=True,
            model_family="mixed",
            notes=[
                "Aider supports multiple providers (Anthropic, OpenAI, etc.).",
                "Model can be set via --model flag or config.",
                "Supports both Claude and OpenAI families.",
            ],
        )

    def get_current_model(self) -> str | None:
        """Detect current Aider model."""
        return self._detect_current_model()

    def _detect_current_model(self) -> str | None:
        """Detect from environment."""
        return os.environ.get("AIDER_MODEL")

    def get_available_models(self) -> list[str]:
        """Get available models in Aider."""
        return self.AVAILABLE_MODELS.copy()

    def supports_dynamic_switch(self) -> bool:
        """Aider supports model switching via config."""
        return True

    def set_model(self, model_name: str) -> bool:
        """Attempt to switch model in Aider via .aider.conf.yml."""
        if model_name not in self.AVAILABLE_MODELS:
            return False

        from pathlib import Path
        # Write to .aider.conf.yml in CWD
        config_path = Path.cwd() / ".aider.conf.yml"
        try:
            lines: list[str] = []
            if config_path.exists():
                lines = config_path.read_text().splitlines()

            # Update or add model line
            model_line = f"model: {model_name}"
            found = False
            for i, line in enumerate(lines):
                if line.startswith("model:"):
                    lines[i] = model_line
                    found = True
                    break
            if not found:
                lines.append(model_line)

            config_path.write_text("\n".join(lines) + "\n")
            return True
        except OSError:
            return False

    def resolve_capability_class(self, capability: CapabilityClass) -> str | None:
        """Resolve capability class for Aider."""
        return self.MODEL_MAP.get(capability)

    def apply_prompt_strategy(self, task: TaskNode) -> dict:
        """Generate Aider-specific strategy."""
        model = self.resolve_capability_class(task.preferred_capability_class)
        return {
            "task_id": task.id,
            "task_type": task.type.value,
            "strategy": "model_switch",
            "target_model": model,
            "hints": [
                f"Use --model {model} for {task.type.value} tasks.",
                "Aider supports model switching via CLI flags.",
            ],
        }
