"""Gemini CLI installer."""

from __future__ import annotations

from routesmith.install.base import BaseInstaller
from routesmith.types import InstallResult

GEMINI_MD_CONTENT = """\
# routesmith

This project uses routesmith for host-aware task routing in Gemini CLI.

## Rules

- routesmith works within Gemini CLI's native model-switching surface.
- Auto mode is the default for mixed prompts.
- Decompose work into planning, coding, testing, documentation, and review steps.
- Use stronger Gemini models for deep reasoning and balanced or fast models for lower-cost steps.
- Keep routing truthful: if a capability is downgraded for cost, say so.

## Task Delegation

When spawning subagents, use the cheapest Gemini model that can handle the task:
- Flash-Lite: bulk mechanical tasks - formatting, renames, simple transforms.
- Flash: summarization, scoped research, lightweight synthesis.
- Pro: planning, implementation, and tradeoff-heavy reasoning.

### Spawn rules
- Cheapest-tier subagents cannot spawn further subagents. If they need to, return to the parent.
- Max spawn depth: {max_spawn_depth}.
- If a subagent needs a stronger model, return to the parent instead of escalating directly.

## Preferred Tools (cheapest effective option first)

- Public pages: prefer text fetch tools.
- Dynamic pages: use browser tooling only when text fetch cannot reach the content.
- PDFs: extract text first.
- Wrap repeated fetch workflows as reusable tools.

## Context

- Use Gemini-family models only.
- Respect repo-level context in GEMINI.md.
- Prefer focused prompts for each subtask and report the chosen capability class.

## Context Management

- Prefer scoped file inclusion over loading the full repository.
- Use Flash-Lite for simple tasks to reduce token burn.
- Keep prompts focused - avoid dumping entire files when only sections are relevant.
- Use the -m flag to switch to cheaper models for mechanical subtasks.
"""


class GeminiInstaller(BaseInstaller):
    """Install routesmith configuration for Gemini CLI."""

    def install(self) -> InstallResult:
        files_created: list[str] = []

        path = self._write_file(
            "GEMINI.md",
            GEMINI_MD_CONTENT.replace("{max_spawn_depth}", str(self.config.max_spawn_depth)),
        )
        files_created.append(path)

        return InstallResult(
            target="gemini",
            success=True,
            files_created=files_created,
            messages=[
                "Created GEMINI.md with routesmith guidance.",
                "Gemini CLI will use this file as persistent project context.",
            ],
        )