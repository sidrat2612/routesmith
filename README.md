<p align="center">
  <h1 align="center">RouteSmith</h1>
  <p align="center">
    <strong>Host-aware auto-routing for coding agents</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/routesmith/"><img src="https://img.shields.io/pypi/v/routesmith?color=blue&label=PyPI" alt="PyPI version"></a>
    <a href="https://github.com/sidrat2612/routesmith/releases/latest"><img src="https://img.shields.io/github/v/release/sidrat2612/routesmith?display_name=tag&label=GitHub%20Release" alt="GitHub Release"></a>
    <a href="https://github.com/sidrat2612/routesmith/actions/workflows/ci.yml"><img src="https://github.com/sidrat2612/routesmith/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://pypi.org/project/routesmith/"><img src="https://img.shields.io/pypi/pyversions/routesmith" alt="Python versions"></a>
    <a href="https://github.com/sidrat2612/routesmith/blob/main/LICENSE"><img src="https://img.shields.io/github/license/sidrat2612/routesmith" alt="License"></a>
    <a href="https://github.com/sidrat2612/routesmith/stargazers"><img src="https://img.shields.io/github/stars/sidrat2612/routesmith?style=social" alt="Stars"></a>
  </p>
</p>

---

**routesmith** automatically routes coding agent tasks to the best available model in your IDE — no manual model picking, no cross-provider hacks.

> Give it a mixed prompt like *"Plan this feature, implement it, add tests, write docs"* and it decomposes, routes each step to the right capability class, and executes using your host's native model switching.

![RouteSmith hero — one prompt branches into multiple task-specific workstreams](https://raw.githubusercontent.com/sidrat2612/routesmith/main/assets/hero.png)

## Why?

Most coding agents are stuck on one model. Mixed tasks (plan -> code -> test -> document) benefit from different model strengths. But each IDE host (Claude Code, Codex, Gemini CLI, Copilot, Cursor, Aider) has different model families and switching capabilities.

**routesmith solves this** by being host-aware:

| Host | Models | Strategy |
|------|--------|----------|
| Claude Code | Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5 | Dynamic model switching |
| Codex | GPT-5.5 / GPT-5.4 / GPT-5.3-Codex | Dynamic model switching |
| Gemini CLI | Gemini 3.1 Pro / Flash / Flash-Lite | Dynamic model switching |
| Copilot | Claude 4.7 / GPT-5.5 / Gemini 3.1 Pro (plan-dependent) | Prompt optimization |
| Cursor | Claude 4.7 / GPT-5.5 / GPT-5.3-Codex / Gemini 3.1 Pro | Prompt optimization |
| Aider | Claude 4.7 / GPT-5.5 / Gemini 3.1 Pro | Dynamic model switching |

![Where RouteSmith fits — agent products, routing layer, API gateway infrastructure](https://raw.githubusercontent.com/sidrat2612/routesmith/main/assets/positioning.png)

## Quickstart

Install from PyPI with `pip install routesmith`.

If PyPI is unavailable or you want to install from the GitHub-hosted release artifacts instead, use the latest release source archive:

Use `pip install https://github.com/sidrat2612/routesmith/releases/latest/download/routesmith-latest.tar.gz`.

Direct downloads:

- [Latest GitHub release page](https://github.com/sidrat2612/routesmith/releases/latest)
- [Latest wheel asset](https://github.com/sidrat2612/routesmith/releases/latest/download/routesmith-latest-py3-none-any.whl)
- [Latest source asset](https://github.com/sidrat2612/routesmith/releases/latest/download/routesmith-latest.tar.gz)

Core Python entry points:

- `routesmith.run(...)` auto-detects the host, decomposes the prompt, and executes the route.
- `routesmith.explain_route(...)` shows the route plan without execution.
- `routesmith.detect_host()` and `routesmith.get_host_capabilities()` expose the detected environment.

### CLI

Common CLI commands:

- Route a mixed task prompt with `routesmith run "Plan this feature, implement it, add tests, and write docs"`.
- Preview the route plan with `routesmith explain "Refactor auth module and add integration tests"`.
- Inspect the environment with `routesmith detect-host`, `routesmith capabilities`, and `routesmith doctor`.
- View performance stats with `routesmith stats`, filter with `--host`, `--capability`, `--source`, or export with `--format json`.
- Show top/bottom performers with `routesmith stats --top 5 --bottom 3`.
- Prune old telemetry with `routesmith stats --prune --max-age-days 30`.

## How It Works

routesmith is an **advisory routing layer** — it plans and recommends, it does not replace your host's execution engine.

Execution flow:

1. Detect the active host, such as Claude Code or Copilot.
2. Decompose the prompt into typed subtasks.
3. Map each task to a capability class.
4. Resolve those capabilities to host-native models.
5. Switch models when possible, or optimize prompts when not.
6. Report metrics, advisory messages, and effectiveness.

![RouteSmith routing flow — detect host, classify prompt, map capability, route, execute, telemetry feedback](https://raw.githubusercontent.com/sidrat2612/routesmith/main/assets/flow.png)

### What it does

- **Decomposes** mixed prompts into discrete, typed subtasks
- **Routes** each subtask to the best capability class (`deep_reasoning`, `coding`, `balanced`, `fast`)
- **Switches models** when the host supports it (Claude Code, Codex, Gemini CLI, Aider)
- **Applies routing preferences** such as `cost` or `quality` on the same router path
- **Runs Python policy plugins** when you need logic beyond static remaps
- **Falls back to prompt optimization** when the host controls model selection
- **Reports** timing, token estimates, effectiveness scores

### What it does NOT do

- Does **not** make LLM API calls — the host handles execution
- Does **not** bypass host constraints — works within your IDE's limits
- Does **not** fake model switches — tells you honestly what happened

### Design Philosophy

Coding agents run inside a host that owns the LLM connection. routesmith sits *alongside* the host as a skill layer that makes smarter routing decisions. It's the routing brain, not the execution muscle.

## Capability Classes

Instead of hardcoding model names, routesmith uses abstract capability classes:

| Class | Use Case | Example Models |
|-------|----------|----------------|
| `deep_reasoning` | Planning, architecture, review | Claude Opus 4.7, GPT-5.5 |
| `coding` | Implementation, testing, refactoring | Claude Sonnet 4.6, GPT-5.3-Codex |
| `balanced` | Documentation, general tasks | Claude Sonnet 4.6, GPT-5.4 |
| `fast` | Formatting, simple transforms | Claude Haiku 4.5, GPT-5.4-mini |

Each host adapter maps these to actual available models.

## Task Types

routesmith classifies prompts into: `planning`, `analysis`, `coding`, `testing`, `refactor`, `documentation`, `formatting`, `review`

Dependencies are resolved automatically — tests wait for code, docs wait for implementation.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ROUTESMITH_DEFAULT_MODE` | Execution mode | `auto` |
| `ROUTESMITH_ALLOW_MODEL_SWITCH` | Allow model switching | `true` |
| `ROUTESMITH_FORCE_HOST` | Force a specific host | — |
| `ROUTESMITH_DEBUG` | Enable debug output | `false` |
| `ROUTESMITH_PERFORMANCE_ROUTING` | Enable performance-aware model selection | `true` |
| `ROUTESMITH_PERFORMANCE_FILE` | Performance telemetry store path | `.routesmith/performance.json` |
| `ROUTESMITH_PERFORMANCE_MAX_RECORDS` | Max stored telemetry records | `500` |
| `ROUTESMITH_PERFORMANCE_MAX_AGE_DAYS` | Optional age-based pruning window | — |
| `ROUTESMITH_CONTEXT_WINDOW_LIMIT` | Prefer leaner context defaults for supported hosts | `true` |
| `ROUTESMITH_AUTOCOMPACT_THRESHOLD` | Auto-compaction threshold percentage for supported hosts | `80` |
| `ROUTESMITH_MAX_SPAWN_DEPTH` | Advisory max subagent nesting depth written into host configs | `2` |

### Config File

Create `.routesmith.toml` in your project root:

Example:

```toml
[routesmith]
default_mode = "auto"
allow_model_switch = true
routing_preference = "cost"

# Performance-aware routing
performance_routing_enabled = true
performance_store_file = ".routesmith/performance.json"
performance_max_records = 500
performance_max_age_days = 30

# Token-efficiency knobs
context_window_limit = true
autocompact_threshold = 80
max_spawn_depth = 2

# Optional Python hooks
policy_plugins = [
  "my_project.routing:plugin",
  "my_project.routing:CustomPlugin",
]

[routesmith.policy_overrides]
planning = "balanced"
documentation = "fast"
```

What the new knobs do:

- `context_window_limit = true` tells install adapters to prefer leaner context defaults when the host exposes a real setting. Today this produces concrete settings for Claude Code and advisory guidance for the other hosts.
- `autocompact_threshold = 80` lowers the context usage percentage at which auto-compaction should kick in for hosts that support it. Today Claude Code uses this to write `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`.
- `max_spawn_depth = 2` controls the advisory spawn-depth limit written into generated host instruction files so subagents do not recurse into wasteful coordination trees.

Recommended config shape:

- Add a `[routesmith]` section with values such as `default_mode = "auto"`, `allow_model_switch = true`, and `routing_preference = "cost"` when you want cheaper model selection.
- Add token-efficiency settings such as `context_window_limit`, `autocompact_threshold`, and `max_spawn_depth` when you want generated host configs to bias toward smaller contexts and shallower delegation.
- Add a `[routesmith.policy_overrides]` section when you want static remaps such as `planning = "balanced"` or `documentation = "fast"`.
- Add a `policy_plugins` list when you want importable Python hooks such as `my_project.routing:plugin` or `my_project.routing:CustomPlugin` to participate in route resolution.
- Add performance settings such as `performance_routing_enabled = true`, `performance_store_file = ".routesmith/performance.json"`, `performance_max_records = 500`, and `performance_max_age_days = 30` when you want tighter telemetry control.

Built-in routing preferences are `balanced`, `cost`, and `quality`. `policy_overrides` handles static remaps, while `policy_plugins` lets you run real Python logic that can adjust capability classes, force explicit models, and attach advisory messages.

## MCP / Stdio Server

routesmith exposes an MCP-compatible JSON-RPC 2.0 server for tool integration:

Start it with `routesmith serve-stdio`.

This lets IDE extensions and agents call routesmith as a tool.

The MCP surface now includes `routesmith.performance`, which returns filtered performance summaries for CLI and agent consumers.

## Performance Tracking

routesmith records per-model task outcomes across runs, including duration, success or failure, capability class, host, and telemetry source. Data is stored in `.routesmith/performance.json`, uses schema versioning with migration support, and separates runtime telemetry from synthetic test data.

Performance-aware routing now promotes tracker data from passive advisory to an active routing signal. When a default model shows weak success or latency for a capability and a better host-available alternative has enough evidence, routesmith will switch to the stronger performer.

View stats with `routesmith stats`. You can filter by model, host, capability, and telemetry source; show top and bottom performers; export JSON summaries; and prune old records with max-record or max-age controls.

When a model's historical success rate drops below 70% or average latency exceeds 5 seconds, routesmith still injects performance advisory messages into run results automatically.

## Install Configs for Hosts

Generate host-specific configuration files:

- `routesmith install claude` writes `CLAUDE.md` and merges token-saving settings into `.claude/settings.json`.
- `routesmith install codex` writes `AGENTS.md`.
- `routesmith install gemini` writes `GEMINI.md`.
- `routesmith install copilot` writes `.github/copilot-instructions.md`.
- `routesmith install cursor` writes `.cursorules`.
- `routesmith install aider` writes `.aider.conf.yml`, or `.aider.routesmith.yml` if an existing Aider config is already present.

## Auto Mode (Default)

Auto mode is the default. For a single mixed prompt, routesmith:

1. Detects the host environment
2. Classifies the prompt into task types
3. Splits into ordered subtasks with dependency resolution
4. Chooses the best host-compatible model per subtask
5. Executes (or recommends) the route
6. Returns metrics and advisory messages

### Truthful Switching

- If the host supports dynamic switching → routesmith switches
- If the host does NOT support switching → routesmith uses prompt strategy
- The result always tells you exactly what happened — no black boxes

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Development setup:

1. Clone the repository from `https://github.com/sidrat2612/routesmith.git`.
2. Change into the `routesmith` directory.
3. Create and activate a virtual environment with `python -m venv .venv` and `source .venv/bin/activate`.
4. Install dev dependencies with `pip install -e ".[dev]"`.
5. Run the test suite with `pytest`.

## Roadmap

- [x] Host detection and capability mapping
- [x] Weighted task decomposition planner
- [x] Dependency-aware execution loop
- [x] Persistent route state
- [x] MCP stdio server
- [x] Structured observability
- [x] Config-driven policy overrides
- [x] Cost-aware routing
- [x] Python policy plugins
- [x] Gemini CLI host adapter
- [x] Real-time model performance tracking
- [x] Performance-aware routing (active model switching based on tracked data)
- [x] Expanded stats UX (host/capability/source filters, JSON export, ranked performers)
- [x] Data store hardening (schema v2, migration, source-aware pruning)
- [x] Release workflow hardening (concurrency, idempotent publish)
- [ ] Additional host adapters

## License

[MIT](LICENSE) — use it anywhere.

---

<p align="center">
  <sub>Built for the multi-model future of coding agents.</sub>
</p>
