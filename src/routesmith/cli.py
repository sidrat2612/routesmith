"""CLI for routesmith."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from routesmith.config import load_config
from routesmith.types import SkillConfig

app = typer.Typer(
    name="routesmith",
    help="Host-aware auto-routing skill library for IDEs and coding agents.",
    no_args_is_help=True,
)
console = Console()

# Sub-apps for host-specific install commands
install_app = typer.Typer(help="Install routesmith configuration for a target host.")
app.add_typer(install_app, name="install", invoke_without_command=True)


@app.command()
def run(
    prompt: str = typer.Argument(..., help="The prompt to route and execute."),
    mode: str = typer.Option("auto", "--mode", "-m", help="Execution mode (auto, manual)."),
    model: str | None = typer.Option(None, "--model", help="Pin a specific model."),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output."),
    no_metrics: bool = typer.Option(False, "--no-metrics", help="Suppress metrics output."),
) -> None:
    """Run a prompt through routesmith's host-aware routing pipeline."""
    config = load_config()
    if debug:
        config.debug = True

    from routesmith.executor import Executor

    executor = Executor(config=config)
    result = executor.run(prompt, mode=mode, model=model)

    # Display route summary
    console.print(Panel(result.route_summary, title="Route Summary", border_style="blue"))

    # Display advisory
    if result.advisory:
        console.print()
        for msg in result.advisory:
            console.print(f"  [yellow]⚠[/yellow] {msg}")

    # Display task results
    if result.tasks:
        console.print()
        table = Table(title="Task Results")
        table.add_column("Task", style="cyan")
        table.add_column("Model", style="green")
        table.add_column("Status", style="bold")
        table.add_column("Time", style="dim")
        table.add_column("Warnings")

        for task in result.tasks:
            status = "[green]✓[/green]" if task.success else "[red]✗[/red]"
            warnings = "; ".join(task.warnings) if task.warnings else ""
            duration = f"{task.duration_ms:.1f}ms" if task.duration_ms else ""
            table.add_row(
                task.task_id,
                task.model_used or "N/A",
                status,
                duration,
                warnings,
            )
        console.print(table)

    # Display metrics
    if not no_metrics and config.show_metrics and result.metrics:
        _display_metrics(result.metrics)


@app.command()
def explain(
    prompt: str = typer.Argument(..., help="The prompt to explain routing for."),
) -> None:
    """Explain the route plan for a prompt without executing."""
    config = load_config()

    from routesmith.executor import Executor

    executor = Executor(config=config)
    plan = executor.explain(prompt)

    console.print(Panel(f"[bold]{plan.host}[/bold]", title="Detected Host"))
    console.print()

    # Task tree
    tree = Tree("[bold]Route Plan[/bold]")
    for task in plan.tasks:
        model_info = task.suggested_model or "prompt strategy"
        deps = f" (depends: {', '.join(task.dependencies)})" if task.dependencies else ""
        conf = f" [{task.confidence:.0%}]" if task.confidence < 1.0 else ""
        node = tree.add(
            f"[cyan]{task.type.value}[/cyan]: {task.title} "
            f"-> [green]{model_info}[/green]{deps}{conf}"
        )

    console.print(tree)
    console.print()

    # Rationale
    console.print(f"[dim]Rationale: {plan.rationale}[/dim]")

    # Advisory
    if plan.advisory:
        console.print()
        for msg in plan.advisory:
            console.print(f"  [yellow]⚠[/yellow] {msg}")


@app.command("detect-host")
def detect_host_cmd() -> None:
    """Detect the current host environment."""
    config = load_config()

    from routesmith.hosts.detector import detect_host

    result = detect_host(config)

    table = Table(title="Host Detection")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Host", result.host_name)
    table.add_row("Confidence", f"{result.confidence:.0%}")
    table.add_row("Method", result.detection_method)
    table.add_row("Root Path", result.root_path or "N/A")

    console.print(table)


@app.command()
def capabilities() -> None:
    """Show capabilities of the detected host."""
    config = load_config()

    from routesmith.hosts.detector import get_host_capabilities

    caps = get_host_capabilities(config)

    table = Table(title=f"Host Capabilities: {caps.host_name}")
    table.add_column("Capability", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Detected", str(caps.detected))
    table.add_row("Current Model", caps.current_model or "N/A")
    table.add_row("Model Family", caps.model_family)
    table.add_row("Dynamic Switch", "✓" if caps.supports_dynamic_switch else "✗")
    table.add_row("Prompt Files", "✓" if caps.supports_prompt_files else "✗")
    table.add_row("Repo Instructions", "✓" if caps.supports_repo_instructions else "✗")
    table.add_row("Settings Edit", "✓" if caps.supports_settings_edit else "✗")
    table.add_row("Env Override", "✓" if caps.supports_env_override else "✗")

    console.print(table)

    if caps.available_models:
        console.print()
        console.print("[bold]Available Models:[/bold]")
        for model in caps.available_models:
            console.print(f"  • {model}")

    if caps.notes:
        console.print()
        for note in caps.notes:
            console.print(f"  [dim]{note}[/dim]")


@app.command()
def doctor() -> None:
    """Run diagnostics on the routesmith environment."""
    import os
    import sys

    console.print(Panel("[bold]routesmith doctor[/bold]", border_style="blue"))
    console.print()

    # Python version
    console.print(f"  Python: {sys.version.split()[0]}")

    # Package version
    from routesmith import __version__
    console.print(f"  routesmith: {__version__}")

    # Environment variables
    console.print()
    console.print("[bold]Environment:[/bold]")
    env_vars = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "ROUTESMITH_DEFAULT_MODE",
        "ROUTESMITH_FORCE_HOST",
        "ROUTESMITH_DEBUG",
    ]
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Mask secrets
            if "KEY" in var:
                display = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display = value
            console.print(f"  {var}: [green]{display}[/green]")
        else:
            console.print(f"  {var}: [dim]not set[/dim]")

    # Host detection
    console.print()
    console.print("[bold]Host Detection:[/bold]")
    config = load_config()

    from routesmith.hosts.detector import detect_host, get_host_capabilities

    detection = detect_host(config)
    console.print(f"  Host: {detection.host_name} ({detection.confidence:.0%} confidence)")

    caps = get_host_capabilities(config)
    console.print(f"  Model Family: {caps.model_family}")
    console.print(f"  Dynamic Switch: {'✓' if caps.supports_dynamic_switch else '✗'}")

    console.print()
    console.print("[green]✓ Diagnostics complete[/green]")


@app.command("serve-stdio")
def serve_stdio_cmd() -> None:
    """Start the stdio server for tool integration."""
    from routesmith.server.stdio import run_stdio_server
    console.print("[dim]Starting stdio server...[/dim]")
    run_stdio_server()


@app.command("stats")
def stats_cmd(
    model: str | None = typer.Option(None, "--model", "-m", help="Filter stats by model name."),
    host: str | None = typer.Option(None, "--host", help="Filter stats by host name."),
    capability: str | None = typer.Option(None, "--capability", help="Filter stats by capability class."),
    source: str = typer.Option("runtime", "--source", help="Filter by telemetry source: runtime, synthetic, or all."),
    top: int = typer.Option(3, "--top", help="Show the top N performers."),
    bottom: int = typer.Option(3, "--bottom", help="Show the bottom N performers."),
    output_format: str = typer.Option("table", "--format", help="Output format: table or json."),
    clear: bool = typer.Option(False, "--clear", help="Clear all tracked performance data."),
    prune: bool = typer.Option(False, "--prune", help="Prune stored performance records before showing stats."),
    max_records: int | None = typer.Option(None, "--max-records", help="Keep only the newest N records when pruning."),
    max_age_days: float | None = typer.Option(None, "--max-age-days", help="Prune records older than N days."),
) -> None:
    """Show real-time model performance statistics."""
    from routesmith.performance import PerformanceTracker

    config = load_config()
    tracker = _create_performance_tracker(config)

    normalized_format = output_format.strip().lower()
    if normalized_format not in {"table", "json"}:
        raise typer.BadParameter("--format must be either 'table' or 'json'.")

    if clear:
        removed = tracker.clear(source=source)
        console.print(f"[green]Cleared {removed} performance record(s) from source={source}.[/green]")
        return

    resolved_max_age_seconds = None
    if max_age_days is not None:
        resolved_max_age_seconds = max_age_days * 86400

    if prune:
        removed = tracker.prune(
            max_records=max_records if max_records is not None else tracker.max_records,
            max_age_seconds=resolved_max_age_seconds if resolved_max_age_seconds is not None else tracker.max_age_seconds,
            source=source,
        )
        console.print(f"[green]Pruned {removed} performance record(s).[/green]")

    summary = tracker.summary_dict(
        model=model,
        host_name=host,
        capability=capability,
        source=source,
        top=top,
        bottom=bottom,
    )

    if normalized_format == "json":
        console.print(json.dumps(summary, indent=2, default=str))
        return

    stats = summary["models"]
    if not stats:
        console.print("[dim]No performance data recorded yet. Run some tasks first.[/dim]")
        return

    filter_bits = [f"source={summary['filters']['source']}"]
    if summary["filters"]["host"]:
        filter_bits.append(f"host={summary['filters']['host']}")
    if summary["filters"]["capability"]:
        filter_bits.append(f"capability={summary['filters']['capability']}")
    if summary["filters"]["model"]:
        filter_bits.append(f"model={summary['filters']['model']}")
    console.print(f"[dim]Filters: {', '.join(filter_bits)}[/dim]")
    console.print()

    table = Table(title="Model Performance")
    table.add_column("Model", style="cyan")
    table.add_column("Tasks", justify="right")
    table.add_column("Success", justify="right", style="green")
    table.add_column("Fail", justify="right", style="red")
    table.add_column("Rate", justify="right")
    table.add_column("Avg (ms)", justify="right")
    table.add_column("Min (ms)", justify="right")
    table.add_column("Max (ms)", justify="right")

    for s in stats:
        rate_color = "green" if s["success_rate"] >= 0.9 else ("yellow" if s["success_rate"] >= 0.7 else "red")
        table.add_row(
            s["model"],
            str(s["total_tasks"]),
            str(s["successes"]),
            str(s["failures"]),
            f"[{rate_color}]{s['success_rate']:.0%}[/{rate_color}]",
            f"{s['avg_duration_ms']:.1f}",
            f"{s['min_duration_ms']:.1f}",
            f"{s['max_duration_ms']:.1f}",
        )

    console.print(table)

    if summary["by_host"] and len(summary["by_host"]) > 1:
        console.print()
        host_table = Table(title="Host Breakdown")
        host_table.add_column("Host", style="cyan")
        host_table.add_column("Tasks", justify="right")
        host_table.add_column("Rate", justify="right")
        host_table.add_column("Avg (ms)", justify="right")
        host_table.add_column("Models", justify="right")
        for host_name, host_stats in summary["by_host"].items():
            host_table.add_row(
                host_name,
                str(host_stats["total_tasks"]),
                f"{host_stats['success_rate']:.0%}",
                f"{host_stats['avg_duration_ms']:.1f}",
                str(len(host_stats["models_used"])),
            )
        console.print(host_table)

    if len(stats) > 1 and summary["top_performers"]:
        console.print()
        _display_ranked_models("Top Performers", summary["top_performers"])

    if len(stats) > 1 and summary["bottom_performers"]:
        console.print()
        _display_ranked_models("Bottom Performers", summary["bottom_performers"])

    # Show advisory if any
    advisory = summary["advisory"]
    if advisory:
        console.print()
        for msg in advisory:
            console.print(f"  [yellow]⚠[/yellow] {msg}")


# Install sub-commands
@install_app.callback(invoke_without_command=True)
def install_default(
    ctx: typer.Context,
    target: str | None = typer.Argument(None, help="Target host (claude, codex, gemini, copilot, cursor, vscode, aider)."),
) -> None:
    """Install routesmith configuration for a target host."""
    if ctx.invoked_subcommand is not None:
        return
    if target is None:
        console.print("[yellow]Specify a target: claude, codex, gemini, copilot, cursor, vscode, aider[/yellow]")
        raise typer.Exit(1)
    _run_install(target)


@install_app.command("claude")
def install_claude() -> None:
    """Install routesmith for Claude Code."""
    _run_install("claude")


@install_app.command("codex")
def install_codex() -> None:
    """Install routesmith for Codex."""
    _run_install("codex")


@install_app.command("gemini")
def install_gemini() -> None:
    """Install routesmith for Gemini CLI."""
    _run_install("gemini")


@install_app.command("copilot")
def install_copilot() -> None:
    """Install routesmith for GitHub Copilot."""
    _run_install("copilot")


@install_app.command("cursor")
def install_cursor() -> None:
    """Install routesmith for Cursor."""
    _run_install("cursor")


@install_app.command("vscode")
def install_vscode() -> None:
    """Install routesmith for VS Code."""
    _run_install("vscode")


@install_app.command("aider")
def install_aider() -> None:
    """Install routesmith for Aider."""
    _run_install("aider")


def _run_install(target: str) -> None:
    """Execute install for a target."""
    from routesmith.install import run_install

    result = run_install(target)

    if result.success:
        console.print(f"[green]✓ Installed routesmith for {target}[/green]")
        if result.files_created:
            console.print()
            console.print("[bold]Files created:[/bold]")
            for f in result.files_created:
                console.print(f"  • {f}")
        for msg in result.messages:
            console.print(f"  [dim]{msg}[/dim]")
    else:
        console.print(f"[red]✗ Install failed for {target}[/red]")
        for w in result.warnings:
            console.print(f"  [yellow]⚠[/yellow] {w}")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of routes to display."),
) -> None:
    """Show recent route execution history."""
    from routesmith.state import list_routes

    config = load_config()
    routes = list_routes(config.routes_dir)[:limit]

    if not routes:
        console.print("[dim]No route history found. Enable with --save-routes or save_routes = true in .routesmith.toml[/dim]")
        return

    table = Table(title="Route History")
    table.add_column("#", style="dim")
    table.add_column("Host", style="cyan")
    table.add_column("Tasks", style="green")
    table.add_column("Prompt", style="white")

    for i, route in enumerate(routes, 1):
        table.add_row(
            str(i),
            route["host"],
            f"{route['succeeded']}/{route['tasks']}",
            route["prompt"][:60] + ("..." if len(route["prompt"]) > 60 else ""),
        )

    console.print(table)


def _create_performance_tracker(config: SkillConfig):
    max_age_seconds = None
    if config.performance_max_age_days is not None:
        max_age_seconds = config.performance_max_age_days * 86400
    from routesmith.performance import PerformanceTracker

    return PerformanceTracker(
        path=config.performance_store_file,
        max_records=config.performance_max_records,
        max_age_seconds=max_age_seconds,
    )


def _display_ranked_models(title: str, ranked_models: list[dict]) -> None:
    table = Table(title=title, border_style="blue")
    table.add_column("Model", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Rate", justify="right")
    table.add_column("Avg (ms)", justify="right")
    table.add_column("Tasks", justify="right")

    for stat in ranked_models:
        table.add_row(
            stat["model"],
            f"{stat['score']:.3f}",
            f"{stat['success_rate']:.0%}",
            f"{stat['avg_duration_ms']:.1f}",
            str(stat["total_tasks"]),
        )
    console.print(table)


def _display_metrics(metrics: dict) -> None:
    """Display route metrics in a rich panel."""
    console.print()

    # Metrics table
    table = Table(title="Route Metrics", border_style="magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Duration", f"{metrics.get('total_duration_ms', 0):.1f}ms")
    table.add_row("Planning", f"{metrics.get('planning_duration_ms', 0):.1f}ms")
    table.add_row("Routing", f"{metrics.get('routing_duration_ms', 0):.1f}ms")
    table.add_row("Execution", f"{metrics.get('execution_duration_ms', 0):.1f}ms")
    table.add_row("", "")
    table.add_row("Tasks Total", str(metrics.get("total_tasks", 0)))
    table.add_row("Tasks Succeeded", str(metrics.get("tasks_succeeded", 0)))
    table.add_row("Model Switches", str(metrics.get("tasks_with_model_switch", 0)))
    table.add_row("", "")
    table.add_row("Est. Tokens (routed)", f"{metrics.get('estimated_total_tokens', 0):,}")
    table.add_row("Est. Tokens (unrouted)", f"{metrics.get('estimated_tokens_without_routing', 0):,}")
    table.add_row("Tokens Saved", f"{metrics.get('estimated_tokens_saved', 0):,}")
    table.add_row("Savings", f"{metrics.get('token_savings_percent', 0):.1f}%")
    table.add_row("", "")
    table.add_row("Effectiveness Score", f"{metrics.get('effectiveness_score', 0):.0f}/100")

    console.print(table)

    # Model usage breakdown
    models_used = metrics.get("models_used", [])
    if models_used:
        console.print()
        model_table = Table(title="Model Usage", border_style="blue")
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Tasks", style="green")
        model_table.add_column("Est. Tokens", style="yellow")
        model_table.add_column("Capability", style="dim")

        for m in models_used:
            model_table.add_row(
                m.get("model", "unknown"),
                str(m.get("tasks_handled", 0)),
                f"{m.get('estimated_tokens', 0):,}",
                m.get("capability_class", ""),
            )
        console.print(model_table)

    # Summary
    summary = metrics.get("summary", "")
    if summary:
        console.print()
        console.print(f"  [dim]{summary}[/dim]")


def app_entry() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    app_entry()
