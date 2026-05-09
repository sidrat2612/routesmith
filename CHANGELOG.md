# Changelog

All notable changes to this project will be documented in this file.

## [0.1.8] - 2026-05-09

### Fixed
- Renamed base exception class from `RouterSmitError` to `RoutesmithError` (typo fix).
- Removed unused `import time` from `metrics.py` and `import os` from `state.py`.
- Moved `import math` from inside function body to module level in `planner.py`.
- Fixed TOML fallback parser not parsing float values (e.g. `7.5` stayed as a string).

### Changed
- `hosts/__init__.py` now exports all host adapters (Aider, ClaudeCode, Codex, Copilot, Cursor, GeminiCLI, Generic) instead of only GeminiCLI.

## [0.1.7] - 2026-05-09

### Added
- Token-efficient install guidance for Claude Code, Codex, Gemini CLI, Copilot, Cursor, VS Code, and Aider with delegation tiers, spawn depth rules, preferred tool selection, and context-management recommendations.
- Project-scoped Claude Code settings generation for `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` and `CLAUDE_CODE_DISABLE_1M_CONTEXT`, merged additively into `.claude/settings.json`.
- Concrete Aider context defaults for chat history limits, prompt caching, and repo-map size.
- New `SkillConfig` fields for `context_window_limit`, `autocompact_threshold`, and `max_spawn_depth`.
- New `HostCapabilities.supports_context_management` flag.
- Delegation-tier, task-complexity, and tool-cost advisories.
- Install adapter tests covering Claude, Codex, Gemini, Copilot, Cursor, and Aider token-saving config output.

### Changed
- Aider installs now write `.aider.conf.yml` when safe and fall back to `.aider.routesmith.yml` when an existing config is already present.

## [0.1.6] - Unreleased

### Added
- Performance-aware routing that uses tracked success and latency to de-prioritize weaker models by capability class.
- Expanded `routesmith stats` filters for host, capability, and telemetry source, plus top/bottom performer views and JSON export.
- New `routesmith.performance` MCP tool for exportable performance summaries.
- Configurable performance store settings for file location, routing enablement, record caps, and age-based pruning.

### Changed
- Performance telemetry now uses schema version 2 with host/source metadata, migration support, and source-aware pruning controls.
- Release workflow hardening now adds concurrency control, repo-explicit asset uploads, and idempotent PyPI reruns.

## [0.1.5] - 2026-05-07

### Added
- Real-time model performance tracking with rolling-window persistence.
- `PerformanceTracker` class records per-model task outcomes, durations, and success rates.
- `routesmith stats` CLI command to view model performance tables and advisory.
- Performance advisory automatically injected into run results when models underperform.
- `PerformanceTracker` exported from the public API.

### Fixed
- Gemini CLI adapter no longer returns a hardcoded fallback model when no environment is detected.
- `SkillConfig.routing_preference` now normalizes input strings (case-insensitive, dash/space tolerant).

## [0.1.4] - 2026-05-07

### Added
- GitHub Release badge and direct release asset links in the README.
- GitHub Release asset fallback install instructions for environments where PyPI is unavailable.
- Config-driven `policy_overrides` support in `.routesmith.toml` for task-type and capability remapping.
- Built-in `routing_preference` support for cost-aware and quality-first routing on the main router path.
- Python policy plugins loaded from `.routesmith.toml` import specs.
- Gemini CLI host detection, routing, and installer support.

### Changed
- Future GitHub Releases now automatically attach versioned artifacts plus stable `latest` asset aliases.
- Router resolution now applies configured policy overrides during `run` and `explain` flows.
- Package metadata and README host coverage now include Gemini CLI.

## [0.1.1] - 2026-05-07

### Changed
- Refreshed host model mappings and README examples to current public model lineups.
- Centralized runtime version reporting so package metadata and server responses stay in sync with `pyproject.toml`.

## [0.1.0] - 2026-05-07

### Added
- Host-aware auto-routing with capability-first model selection
- Host adapters: Claude Code, Codex, Copilot, Cursor, Aider, Generic
- Deterministic task planner with weighted scoring (no API calls needed)
- Dependency-aware execution loop with timing and metrics
- Persistent route state (save/load JSON)
- Configuration via `.routesmith.toml` and environment variables
- MCP-compatible JSON-RPC 2.0 stdio server
- Structured observability with JSON logging and `timed()` context manager
- Route metrics with token economics and effectiveness scoring
- CLI commands: `run`, `explain`, `detect-host`, `capabilities`, `serve`, `install`
- Install adapters for generating host-specific configs
- 155 tests, all passing without live API calls
