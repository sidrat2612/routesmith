"""Claude Code host adapter."""

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


class ClaudeCodeHostAdapter(BaseHostAdapter):
    """Adapter for Claude Code (Anthropic's coding agent)."""

    # Claude-family model mapping by capability class
    MODEL_MAP: dict[CapabilityClass, str] = {
        CapabilityClass.DEEP_REASONING: "claude-opus-4-7",
        CapabilityClass.CODING: "claude-sonnet-4-6",
        CapabilityClass.BALANCED: "claude-sonnet-4-6",
        CapabilityClass.FAST: "claude-haiku-4-5",
    }

    AVAILABLE_MODELS = [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    ]

    def detect(self) -> HostDetectionResult:
        """Detect Claude Code environment."""
        confidence = 0.0
        method_parts: list[str] = []

        # Check for CLAUDE_CODE env var or similar indicators
        if os.environ.get("CLAUDE_CODE"):
            confidence += 0.5
            method_parts.append("CLAUDE_CODE env")

        # Check for ~/.claude directory
        claude_dir = Path.home() / ".claude"
        if claude_dir.exists():
            confidence += 0.3
            method_parts.append(".claude dir")

        # Check for CLAUDE.md in workspace
        cwd = Path.cwd()
        if (cwd / "CLAUDE.md").exists():
            confidence += 0.2
            method_parts.append("CLAUDE.md")

        # Check for anthropic API key as weak signal
        if os.environ.get("ANTHROPIC_API_KEY"):
            confidence += 0.1
            method_parts.append("ANTHROPIC_API_KEY")

        return HostDetectionResult(
            host_name="claude_code",
            confidence=min(confidence, 1.0),
            detection_method=", ".join(method_parts) if method_parts else "none",
            root_path=str(cwd),
        )

    def get_capabilities(self) -> HostCapabilities:
        """Get Claude Code capabilities."""
        return HostCapabilities(
            host_name="claude_code",
            detected=self.detect().confidence > 0.3,
            current_model=self._detect_current_model(),
            available_models=self.AVAILABLE_MODELS,
            supports_dynamic_switch=True,
            supports_prompt_files=True,
            supports_repo_instructions=True,
            supports_settings_edit=True,
            supports_env_override=True,
            supports_context_management=True,
            model_family="anthropic",
            notes=[
                "Claude Code supports Claude-family models only.",
                "Model switching is supported via settings and flags.",
                "CLAUDE.md repo instructions are supported.",
            ],
        )

    def get_current_model(self) -> str | None:
        """Get current Claude model if detectable."""
        return self._detect_current_model()

    def _detect_current_model(self) -> str | None:
        """Try to detect the current model from env or config."""
        model = os.environ.get("CLAUDE_MODEL")
        if model:
            return model
        # Default assumption for Claude Code
        return "claude-sonnet-4-6"

    def get_available_models(self) -> list[str]:
        """Get available Claude models."""
        return self.AVAILABLE_MODELS.copy()

    def supports_dynamic_switch(self) -> bool:
        """Claude Code supports model switching."""
        return True

    def set_model(self, model_name: str) -> bool:
        """Attempt to switch model in Claude Code.

        Writes to ~/.claude/settings.json if the model is valid.
        """
        if model_name not in self.AVAILABLE_MODELS:
            return False

        import json
        settings_path = Path.home() / ".claude" / "settings.json"
        try:
            settings: dict = {}
            if settings_path.exists():
                settings = json.loads(settings_path.read_text())

            settings["model"] = model_name
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps(settings, indent=2))
            return True
        except (OSError, json.JSONDecodeError):
            return False

    def resolve_capability_class(self, capability: CapabilityClass) -> str | None:
        """Resolve capability class to Claude model."""
        return self.MODEL_MAP.get(capability)

    def apply_prompt_strategy(self, task: TaskNode) -> dict:
        """Generate Claude-specific prompt strategy."""
        model = self.resolve_capability_class(task.preferred_capability_class)
        return {
            "task_id": task.id,
            "task_type": task.type.value,
            "strategy": "model_switch",
            "target_model": model,
            "hints": [
                f"Use {model} for {task.type.value} tasks.",
                f"Claude Code supports switching to this model.",
            ],
        }
