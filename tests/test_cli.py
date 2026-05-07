"""Tests for the CLI."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from routesmith.cli import app
from routesmith.performance import PerformanceTracker
from routesmith.types import CapabilityClass, RoutePlan, TaskNode, TaskResult, TaskType

runner = CliRunner()


def _seed_performance_store() -> None:
    tracker = PerformanceTracker()
    plan = RoutePlan(
        original_prompt="stats seed",
        tasks=[
            TaskNode(
                id="good",
                type=TaskType.CODING,
                title="Good coding task",
                preferred_capability_class=CapabilityClass.CODING,
            ),
            TaskNode(
                id="bad",
                type=TaskType.CODING,
                title="Bad coding task",
                preferred_capability_class=CapabilityClass.CODING,
            ),
        ],
    )
    for index in range(3):
        tracker.record_run(
            plan,
            [
                TaskResult(task_id="good", model_used="claude-haiku-4-5", success=True, duration_ms=100.0),
                TaskResult(task_id="bad", model_used="claude-sonnet-4-6", success=index == 0, duration_ms=6400.0),
            ],
            host_name="claude_code",
            source="runtime",
        )


class TestCLI:
    """Test CLI commands."""

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "routesmith" in result.output.lower() or "host-aware" in result.output.lower()

    def test_explain_command(self):
        result = runner.invoke(app, ["explain", "plan and implement a feature"])
        assert result.exit_code == 0
        assert "Route Plan" in result.output or "planning" in result.output.lower()

    def test_detect_host_command(self):
        result = runner.invoke(app, ["detect-host"])
        assert result.exit_code == 0
        assert "Host" in result.output

    def test_capabilities_command(self):
        result = runner.invoke(app, ["capabilities"])
        assert result.exit_code == 0
        assert "Capabilities" in result.output or "Model Family" in result.output

    def test_doctor_command(self):
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "routesmith" in result.output

    def test_run_command(self):
        result = runner.invoke(app, ["run", "implement a function"])
        assert result.exit_code == 0
        assert "Route Summary" in result.output or "Task Results" in result.output

    def test_run_with_model_pin(self):
        result = runner.invoke(app, ["run", "implement something", "--model", "test-model"])
        assert result.exit_code == 0
        # Should show pinned model advisory
        assert "Pinned" in result.output or "model" in result.output.lower()

    def test_explain_multi_task(self):
        result = runner.invoke(app, ["explain", "plan, implement, test, and document"])
        assert result.exit_code == 0
        # Should show multiple tasks
        assert "planning" in result.output.lower() or "coding" in result.output.lower()

    def test_stats_command_json_output_supports_filters(self):
        with runner.isolated_filesystem():
            _seed_performance_store()
            result = runner.invoke(
                app,
                [
                    "stats",
                    "--format",
                    "json",
                    "--host",
                    "claude_code",
                    "--capability",
                    "coding",
                    "--source",
                    "runtime",
                    "--top",
                    "1",
                ],
            )
            assert result.exit_code == 0
            payload = json.loads(result.output)
            assert payload["filters"]["host"] == "claude_code"
            assert payload["filters"]["capability"] == "coding"
            assert payload["top_performers"]

    def test_stats_command_shows_top_and_bottom_performers(self):
        with runner.isolated_filesystem():
            _seed_performance_store()
            result = runner.invoke(app, ["stats", "--top", "1", "--bottom", "1"])
            assert result.exit_code == 0
            assert "Top Performers" in result.output
            assert "Bottom Performers" in result.output
