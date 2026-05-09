"""Claude Code installer."""

from __future__ import annotations

from routesmith.install.base import BaseInstaller
from routesmith.types import InstallResult

CLAUDE_MD_CONTENT = """\
# routesmith

This project uses routesmith for host-aware task routing.

## Rules

- routesmith is a host-aware skill layer, not a cross-provider broker.
- In Claude Code, only Claude-family models are available.
- Auto mode is the default. Tasks are decomposed and routed to the best available Claude model.
- Model routing respects host constraints: no fake cross-provider switching.
- If model switching is supported, use the best model per task type:
  - Deep reasoning tasks (planning, analysis, review) -> strongest reasoning model
  - Coding tasks (implement, test, refactor) -> strongest coding model
  - Documentation -> balanced model
  - Formatting -> fastest model

## Task Delegation

When spawning subagents, use the cheapest model that can handle the task:
- Haiku: bulk mechanical tasks - file ops, formatting, renaming, simple transforms. No judgment needed.
- Sonnet: scoped research, code exploration, summarization, synthesis across sources.
- Opus: only when real planning or tradeoffs are involved - architecture, ambiguous requirements, high-stakes decisions.

### Spawn rules
- Haiku subagents cannot spawn further subagents. If they need to, return to the parent.
- Max spawn depth: {max_spawn_depth}.
- If a subagent needs a smarter model, it returns to the parent instead of escalating on its own.

## Preferred Tools (cheapest effective option first)

- Public pages: use WebFetch - free, text-only, fast.
- Dynamic pages or auth-walled content: use agent-browser CLI instead of screenshot-based browsing.
- PDFs: use pdftotext instead of the Read tool.
- When the same fetch pattern repeats more than twice, wrap it as a reusable tool.

## Context Management

- Context auto-compaction is set to trigger at {autocompact_threshold}% capacity instead of the default near-full threshold.
{context_window_note}- For further tuning, lower effort for routine tasks or cap the effective compaction window explicitly.

## Task Decomposition

For mixed prompts, routesmith splits work into subtasks:
1. Planning
2. Implementation
3. Testing
4. Documentation
5. Review

Each step uses the most appropriate model from the Claude family.
"""

class ClaudeInstaller(BaseInstaller):
    """Install routesmith configuration for Claude Code."""

    def _build_settings_content(self) -> dict[str, dict[str, str]]:
        env = {
            "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": str(self.config.autocompact_threshold),
        }
        if self.config.context_window_limit:
            env["CLAUDE_CODE_DISABLE_1M_CONTEXT"] = "1"
        return {"env": env}

    def install(self) -> InstallResult:
        files_created: list[str] = []

        # Write CLAUDE.md
        context_window_note = (
            "- 1M context window support is disabled to avoid loading "
            "unnecessary long-context variants for routine work.\n"
            if self.config.context_window_limit
            else ""
        )
        path = self._write_file(
            "CLAUDE.md",
            CLAUDE_MD_CONTENT
                .replace("{max_spawn_depth}", str(self.config.max_spawn_depth))
                .replace("{autocompact_threshold}", str(self.config.autocompact_threshold))
                .replace("{context_window_note}", context_window_note),
        )
        files_created.append(path)

        path = self._write_json_file(
            ".claude/settings.json",
            self._build_settings_content(),
            merge=True,
        )
        files_created.append(path)

        return InstallResult(
            target="claude",
            success=True,
            files_created=files_created,
            messages=[
                "Created CLAUDE.md with routesmith instructions.",
                "Updated .claude/settings.json with token-saving context controls.",
                "Claude Code will use these instructions for routing guidance.",
            ],
            warnings=self._warnings,
        )
