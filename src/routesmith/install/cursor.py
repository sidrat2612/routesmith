"""Cursor installer."""

from __future__ import annotations

from routesmith.install.base import BaseInstaller
from routesmith.types import InstallResult

CURSORULES_CONTENT = """\
# routesmith - Cursor Rules

This project uses routesmith for host-aware task routing.

## Principles

- Decompose mixed prompts into focused subtasks.
- Execute in dependency order: plan -> code -> test -> docs -> review.
- Model selection is user-controlled in Cursor.
- Use structured, clear prompts for each subtask.
- Do not assume cross-provider model access.

## Capability Mapping (advisory)

- Planning/Analysis/Review: Use strongest reasoning model available.
- Coding/Testing/Refactor: Use strongest coding model available.
- Documentation: Use balanced model.
- Formatting: Use fastest model.

## Task Delegation

- Fast tier: bulk mechanical work, formatting, renames.
- Balanced tier: summarization, scoped exploration, synthesis.
- Coding tier: implementation and test work.
- Deep reasoning tier: architecture and tradeoffs only.

### Spawn rules

- Fast-tier subtasks should not recurse. If they need more help, return to the parent.
- Max spawn depth: {max_spawn_depth}.
- Escalate back to the parent rather than switching tiers inside the subtask.

## Preferred Tools

- Prefer text fetch over screenshot-heavy browsing.
- Use browser automation only for dynamic or auth-walled content.
- Extract PDF text before using heavier readers.
- Turn repeated fetch flows into reusable tools.

## Context Management

- Use .cursorignore to exclude build outputs, generated assets, and large blobs.
- Prefer @file references for scoped context inclusion.
- Keep requests focused and decompose multi-step work into separate turns.
- Use persistent project rules instead of repeating broad instructions.

## Task Types

Recognized task types: planning, analysis, coding, testing, refactor, documentation, formatting, review.
"""


class CursorInstaller(BaseInstaller):
    """Install routesmith configuration for Cursor."""

    def install(self) -> InstallResult:
        files_created: list[str] = []

        path = self._write_file(
            ".cursorules",
            CURSORULES_CONTENT.replace("{max_spawn_depth}", str(self.config.max_spawn_depth)),
        )
        files_created.append(path)

        return InstallResult(
            target="cursor",
            success=True,
            files_created=files_created,
            messages=[
                "Created .cursorules with routesmith guidance.",
                "Cursor will use these rules for routing awareness.",
            ],
        )
