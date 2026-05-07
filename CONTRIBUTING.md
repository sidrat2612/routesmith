# Contributing to routesmit

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/sidrat2612/routesmith.git
cd routesmith
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Guidelines

### Code Style

- Python 3.10+ with type annotations
- Use `pydantic` for data models
- Keep functions focused and small
- No unnecessary abstractions

### Testing

- All tests must pass without live API calls
- Use mocked behavior for provider-dependent flows
- Host detection, planning, and routing must work without API keys
- Run the full suite before submitting: `pytest`

### Commits

- Use clear, descriptive commit messages
- One logical change per commit
- Reference issue numbers where applicable

## What to Contribute

### Good First Issues

Look for issues labeled [`good first issue`](https://github.com/sidrat2612/routesmith/labels/good%20first%20issue).

### Ideas Welcome

- New host adapters (Windsurf, Zed, etc.)
- Improved task classification patterns
- Better capability-to-model mappings
- Documentation improvements
- Performance optimizations

## Pull Request Process

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Add or update tests as needed
4. Ensure `pytest` passes
5. Open a PR with a clear description of what and why

## Architecture Notes

- `src/routesmit/hosts/` — Host adapters (one file per host)
- `src/routesmit/planner.py` — Task decomposition (deterministic, no API calls)
- `src/routesmit/router.py` — Capability-to-model resolution
- `src/routesmit/executor.py` — Orchestration loop
- `src/routesmit/server/` — MCP stdio server
- `tests/` — Test suite

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful and constructive.

## Questions?

Open a [discussion](https://github.com/sidrat2612/routesmith/discussions) or file an issue.
