"""Codex installer."""

from __future__ import annotations

from routesmith.install.base import BaseInstaller
from routesmith.types import InstallResult

AGENTS_MD_CONTENT = """\
# routesmith

This project uses routesmith for host-aware task routing.

## Rules

- routesmith is a host-aware skill layer.
- In Codex/OpenAI environments, only OpenAI-family models are available.
- Auto mode is the default. Tasks are decomposed and routed to the best available OpenAI model.
- Model routing respects host constraints.
- Capability mapping:
    - Deep reasoning (planning, analysis, review) -> strongest reasoning model (e.g., gpt-5.5; fall back to gpt-5.4)
    - Coding (implement, test, refactor) -> strongest coding model (e.g., gpt-5.3-codex)
    - Documentation -> balanced model (e.g., gpt-5.4)
    - Formatting -> fastest model (e.g., gpt-5.4-mini)

## Task Delegation

When spawning subagents, use the cheapest model that can handle the task:
- gpt-5.4-mini: bulk mechanical tasks - formatting, renames, small transforms.
- gpt-5.3-codex: implementation, test fixes, scoped code edits.
- gpt-5.4: synthesis, summarization, moderate research.
- gpt-5.5: architecture, ambiguous requirements, high-stakes tradeoffs only.

### Spawn rules
- Cheapest-tier subagents cannot spawn further subagents. If they need to, return to the parent.
- Max spawn depth: {max_spawn_depth}.
- If a subagent needs a smarter model, return to the parent instead of escalating on its own.

## Preferred Tools (cheapest effective option first)

- Public pages: use text-first fetch tools.
- Dynamic or auth-walled pages: use browser automation only when text fetch is insufficient.
- PDFs: extract text first instead of using image-heavy readers.
- When the same fetch pattern repeats more than twice, wrap it as a reusable tool.

## Context Management

- Prefer focused file inclusion over loading the whole repository into context.
- Use subagents for isolated subtasks so each agent keeps a lean context.
- Codex has built-in compaction; scoped prompts reduce how often it needs to compact.
- Use the cheapest tier that can complete the task reliably.

## Task Decomposition

For mixed prompts, routesmith splits work into ordered subtasks.
Each step targets the most appropriate model from the OpenAI family.
"""


class CodexInstaller(BaseInstaller):
    """Install routesmith configuration for Codex."""

    def install(self) -> InstallResult:
        files_created: list[str] = []

        path = self._write_file(
            "AGENTS.md",
            AGENTS_MD_CONTENT.replace("{max_spawn_depth}", str(self.config.max_spawn_depth)),
        )
        files_created.append(path)

        return InstallResult(
            target="codex",
            success=True,
            files_created=files_created,
            messages=[
                "Created AGENTS.md with routesmith instructions.",
                "Codex will use these instructions for routing guidance.",
            ],
        )
