# routesmith - Copilot Instructions

This repository contains `routesmith`, a host-aware auto-routing skill library for IDEs and coding agents.

## Core Architecture Rule

routesmith is a HOST-AWARE skill layer, NOT a universal cross-provider broker.

- In Claude Code: only Claude-family models are managed.
- In Codex/OpenAI: only OpenAI-family models are managed.
- In Copilot: model switching is host-controlled; use prompt optimization.
- Never assume a host can use models from another provider family.

## Key Design Principles

1. **Auto mode is default** — Users should not manually choose models per step.
2. **Capability-first routing** — Map task types to capability classes, then resolve to host models.
3. **Truthful switching** — Never claim a model was switched unless confirmed.
4. **Graceful fallback** — If switching is unsupported, use prompt strategy.
5. **Deterministic planning** — Planner works without API calls.

## Versioning Rule

- Any code change must also update the package version in `pyproject.toml`.
- Do not leave behavior-changing code edits at the same published version.
- When making code changes, treat the version bump as part of the same change.

## Description Alignment Rule

The package description must stay in sync across all three surfaces when releasing:

| Surface | Location | Current canonical description |
|---------|----------|-------------------------------|
| PyPI | `pyproject.toml` → `description` field | `Auto-route coding agent tasks to the best model in your IDE. Python library + MCP server for Claude Code, Codex, Copilot, Cursor, and Aider.` |
| GitHub repo | Repository description (set via `gh api -X PATCH repos/sidrat2612/routesmith -f description='…'`) | `Host-aware model routing for coding agents. Python library + MCP server for Claude Code, Codex, Copilot, Cursor, and Aider.` |
| GitHub topics | Repository topics (set via `gh api -X PUT repos/sidrat2612/routesmith/topics`) | See current topic list in repo settings |

- If you change the PyPI `description` in `pyproject.toml`, update the GitHub repo description via `gh` in the same PR/commit.
- `pyproject.toml` keywords must stay aligned with the GitHub repository topics.
- Do not change one surface without updating the other two.

## Package Structure

- `src/routesmith/` — Main package
- `src/routesmith/hosts/` — Host adapters (detect, capabilities, switch)
- `src/routesmith/install/` — Install adapters for generating host configs
- `src/routesmith/server/` — Stdio server for tool integration
- `tests/` — Test suite (no live API calls required)

## Testing

Tests must run without live API calls. Use mocked behavior for provider-dependent flows.
Host detection, planning, and routing must work without any API keys.
