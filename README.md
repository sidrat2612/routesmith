<p align="center">
  <h1 align="center">routesmit</h1>
  <p align="center">
    <strong>Host-aware auto-routing for coding agents</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/routesmit/"><img src="https://img.shields.io/pypi/v/routesmit?color=blue&label=PyPI" alt="PyPI version"></a>
    <a href="https://github.com/sidrat2612/routesmith/actions/workflows/ci.yml"><img src="https://github.com/sidrat2612/routesmith/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://pypi.org/project/routesmit/"><img src="https://img.shields.io/pypi/pyversions/routesmit" alt="Python versions"></a>
    <a href="https://github.com/sidrat2612/routesmith/blob/main/LICENSE"><img src="https://img.shields.io/github/license/sidrat2612/routesmith" alt="License"></a>
    <a href="https://github.com/sidrat2612/routesmith/stargazers"><img src="https://img.shields.io/github/stars/sidrat2612/routesmith?style=social" alt="Stars"></a>
  </p>
</p>

---

**routesmit** automatically routes coding agent tasks to the best available model in your IDE — no manual model picking, no cross-provider hacks.

> Give it a mixed prompt like *"Plan this feature, implement it, add tests, write docs"* and it decomposes, routes each step to the right capability class, and executes using your host's native model switching.

## Why?

Most coding agents are stuck on one model. Mixed tasks (plan → code → test → document) benefit from different model strengths. But each IDE host (Claude Code, Codex, Copilot, Cursor, Aider) has different model families and switching capabilities.

**routesmit solves this** by being host-aware:

| Host | Models | Strategy |
|------|--------|----------|
| Claude Code | Opus / Sonnet / Haiku | Dynamic model switching |
| Codex | o3 / codex-mini / GPT-4.1 | Dynamic model switching |
| Copilot | Host-controlled | Prompt optimization |
| Cursor | User-controlled | Prompt optimization |
| Aider | Multi-provider | Dynamic model switching |

## Quickstart

```bash
pip install routesmit
```

```python
import routesmit

# Auto-detect host, decompose, route, execute
result = routesmit.run("Plan and implement a REST API with tests")

# Just see the plan without executing
plan = routesmit.explain_route("Refactor the database layer")

# Check what you're running on
host = routesmit.detect_host()
caps = routesmit.get_host_capabilities()
```

### CLI

```bash
# Route a prompt
routesmit run "Plan this feature, implement it, add tests, and write docs"

# Preview the route plan
routesmit explain "Refactor auth module and add integration tests"

# Diagnostics
routesmit detect-host
routesmit capabilities
routesmit doctor
```

## How It Works

routesmit is an **advisory routing layer** — it plans and recommends, it does not replace your host's execution engine.

```
┌─────────────────────────────────────────┐
│           Your Prompt                   │
├─────────────────────────────────────────┤
│  1. Detect host (Claude Code? Copilot?) │
│  2. Decompose into typed subtasks       │
│  3. Map tasks → capability classes      │
│  4. Resolve to host-native models       │
│  5. Switch models or optimize prompts   │
│  6. Report metrics & effectiveness      │
└─────────────────────────────────────────┘
```

### What it does

- **Decomposes** mixed prompts into discrete, typed subtasks
- **Routes** each subtask to the best capability class (`deep_reasoning`, `coding`, `balanced`, `fast`)
- **Switches models** when the host supports it (Claude Code, Codex, Aider)
- **Falls back to prompt optimization** when the host controls model selection
- **Reports** timing, token estimates, effectiveness scores

### What it does NOT do

- Does **not** make LLM API calls — the host handles execution
- Does **not** bypass host constraints — works within your IDE's limits
- Does **not** fake model switches — tells you honestly what happened

### Design Philosophy

Coding agents run inside a host that owns the LLM connection. routesmit sits *alongside* the host as a skill layer that makes smarter routing decisions. It's the routing brain, not the execution muscle.

## Capability Classes

Instead of hardcoding model names, routesmit uses abstract capability classes:

| Class | Use Case | Example Models |
|-------|----------|----------------|
| `deep_reasoning` | Planning, architecture, review | Claude Opus, o3 |
| `coding` | Implementation, testing, refactoring | Claude Sonnet, codex-mini |
| `balanced` | Documentation, general tasks | Claude Sonnet, GPT-4.1 |
| `fast` | Formatting, simple transforms | Claude Haiku, GPT-4.1-mini |

Each host adapter maps these to actual available models.

## Task Types

routesmit classifies prompts into: `planning`, `analysis`, `coding`, `testing`, `refactor`, `documentation`, `formatting`, `review`

Dependencies are resolved automatically — tests wait for code, docs wait for implementation.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ROUTESMIT_DEFAULT_MODE` | Execution mode | `auto` |
| `ROUTESMIT_ALLOW_MODEL_SWITCH` | Allow model switching | `true` |
| `ROUTESMIT_FORCE_HOST` | Force a specific host | — |
| `ROUTESMIT_DEBUG` | Enable debug output | `false` |

### Config File

Create `.routesmit.toml` in your project root:

```toml
[routesmit]
default_mode = "auto"
allow_model_switch = true
```

## MCP / Stdio Server

routesmit exposes an MCP-compatible JSON-RPC 2.0 server for tool integration:

```bash
routesmit serve-stdio
```

This lets IDE extensions and agents call routesmit as a tool.

## Install Configs for Hosts

Generate host-specific configuration files:

```bash
routesmit install claude    # Writes CLAUDE.md
routesmit install codex     # Writes AGENTS.md
routesmit install copilot   # Writes .github/copilot-instructions.md
routesmit install cursor    # Writes .cursorrules
routesmit install aider     # Writes .aider.conf.yml
```

## Auto Mode (Default)

Auto mode is the default. For a single mixed prompt, routesmit:

1. Detects the host environment
2. Classifies the prompt into task types
3. Splits into ordered subtasks with dependency resolution
4. Chooses the best host-compatible model per subtask
5. Executes (or recommends) the route
6. Returns metrics and advisory messages

### Truthful Switching

- If the host supports dynamic switching → routesmit switches
- If the host does NOT support switching → routesmit uses prompt strategy
- The result always tells you exactly what happened — no black boxes

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/sidrat2612/routesmith.git
cd routesmith
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Roadmap

- [x] Host detection and capability mapping
- [x] Weighted task decomposition planner
- [x] Dependency-aware execution loop
- [x] Persistent route state
- [x] MCP stdio server
- [x] Structured observability
- [ ] Real-time model performance tracking
- [ ] Cost-aware routing
- [ ] Custom policy plugins
- [ ] Additional host adapters

## License

[MIT](LICENSE) — use it anywhere.

---

<p align="center">
  <sub>Built for the multi-model future of coding agents.</sub>
</p>
