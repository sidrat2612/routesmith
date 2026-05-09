"""Aider installer."""

from __future__ import annotations

from routesmith.install.base import BaseInstaller
from routesmith.types import InstallResult

AIDER_CONF_CONTENT = """\
# routesmith aider configuration
# Concrete context management settings
max-chat-history-tokens: 4000
cache-prompts: true
map-tokens: 1024

# Leave the main model unset so routesmith can recommend or switch by task.
# Uncomment and set weak-model to match your provider:
# weak-model: claude-haiku-4-5   # Anthropic
# weak-model: gpt-4o-mini        # OpenAI

# Task delegation
# - Fast tier: claude-haiku-4-5 for mechanical transforms and formatting.
# - Balanced tier: claude-sonnet-4-6 for summaries and scoped exploration.
# - Coding tier: gpt-5.3-codex for implementation and tests.
# - Deep reasoning tier: claude-opus-4-7 for architecture and tradeoffs only.
#
# Spawn rules
# - Cheapest-tier subtasks cannot spawn further subtasks.
# - Max spawn depth: {max_spawn_depth}.
# - Escalate back to the parent instead of changing tiers inside the subtask.
#
# Preferred tools
# - Public pages: text-first fetch.
# - Dynamic/auth-walled pages: browser automation only when needed.
# - PDFs: extract text first.
# - Repeated fetch patterns: wrap as reusable tooling.
"""


class AiderInstaller(BaseInstaller):
    """Install routesmith configuration for Aider."""

    def install(self) -> InstallResult:
        files_created: list[str] = []

        config_path = ".aider.conf.yml"
        messages = [
            "Created .aider.conf.yml with routesmith delegation and token-saving defaults.",
            "Aider supports model switching via --model flag.",
            "Use routesmith explain to see recommended models per task.",
        ]

        if (self.root / config_path).exists():
            config_path = ".aider.routesmith.yml"
            messages[0] = (
                "Created .aider.routesmith.yml because .aider.conf.yml already exists. "
                "Pass --config .aider.routesmith.yml to use these defaults."
            )

        path = self._write_file(
            config_path,
            AIDER_CONF_CONTENT.replace("{max_spawn_depth}", str(self.config.max_spawn_depth)),
        )
        files_created.append(path)

        return InstallResult(
            target="aider",
            success=True,
            files_created=files_created,
            messages=messages,
        )
