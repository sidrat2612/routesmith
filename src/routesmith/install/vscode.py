"""VS Code installer."""

from __future__ import annotations

from routesmith.install.base import BaseInstaller
from routesmith.types import InstallResult

COPILOT_INSTRUCTIONS_CONTENT = """\
# routesmith - VS Code / Copilot Instructions

This workspace uses routesmith for host-aware task routing.

## How it works

- routesmith decomposes mixed prompts into focused subtasks.
- Each task type maps to a capability class (deep_reasoning, coding, balanced, fast).
- In VS Code/Copilot, model switching is host-controlled.
- routesmith provides structured prompts and task decomposition instead.

## Usage

For any mixed-task prompt, routesmith will:
1. Classify the prompt into task types
2. Create a dependency-ordered task graph
3. Recommend the ideal capability class per step
4. Execute with optimized prompts per subtask

## Task Delegation

- `fast` for mechanical edits and formatting
- `balanced` for summaries and scoped exploration
- `coding` for implementation and tests
- `deep_reasoning` only for planning and tradeoffs

### Spawn Rules

- Fast-tier subtasks should not recurse.
- Max spawn depth: {max_spawn_depth}.
- If a subtask needs deeper reasoning, return to the parent instead of escalating internally.

## Preferred Tools

- Public pages -> text-first fetch
- Dynamic pages -> browser automation only when needed
- PDFs -> text extraction first
- Repeated fetches -> reusable tools

## Context Management

- Use #file references to keep context scoped.
- Avoid pulling build outputs, generated files, or large artifacts into context.
- Keep requests focused and split multi-step work into separate turns when needed.
"""


class VSCodeInstaller(BaseInstaller):
    """Install routesmith configuration for VS Code."""

    def install(self) -> InstallResult:
        files_created: list[str] = []

        path = self._write_file(
            ".github/copilot-instructions.md",
            COPILOT_INSTRUCTIONS_CONTENT.replace("{max_spawn_depth}", str(self.config.max_spawn_depth)),
        )
        files_created.append(path)

        return InstallResult(
            target="vscode",
            success=True,
            files_created=files_created,
            messages=[
                "Created .github/copilot-instructions.md for VS Code / Copilot.",
            ],
        )
