"""Integration tests for routesmith - end-to-end pipeline tests with mocked filesystem."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from routesmith.config import load_config
from routesmith.executor import Executor
from routesmith.hosts.claude_code import ClaudeCodeHostAdapter
from routesmith.metrics import RouteMetrics, compute_metrics
from routesmith.planner import Planner
from routesmith.state import list_routes, save_route
from routesmith.types import CapabilityClass, HostDetectionResult, SkillConfig, TaskType
from routesmith.types import RoutingPreference


class TestEndToEndPipeline:
    """Full pipeline integration tests."""

    def test_run_returns_metrics(self):
        config = SkillConfig(show_metrics=True)
        executor = Executor(config=config)
        result = executor.run("implement a REST API")
        assert result.metrics is not None
        assert result.metrics["total_tasks"] >= 1
        assert result.metrics["effectiveness_score"] >= 0

    def test_run_multi_task_has_multiple_models(self):
        config = SkillConfig()
        executor = Executor(config=config)
        result = executor.run("plan, implement, test, and review a feature")
        assert result.metrics is not None
        assert result.metrics["total_tasks"] >= 3
        assert result.metrics["decomposition_count"] >= 3

    def test_run_with_pinned_model(self):
        config = SkillConfig()
        executor = Executor(config=config)
        result = executor.run("implement a function", model="claude-sonnet-4-6")
        # When host supports switching: model_used matches. Otherwise: advisory mentions pinned model.
        has_model = any("claude-sonnet-4-6" in (task.model_used or "") for task in result.tasks)
        has_advisory = any("Pinned model" in msg for msg in result.advisory)
        assert has_model or has_advisory

    def test_explain_produces_plan(self):
        config = SkillConfig()
        executor = Executor(config=config)
        plan = executor.explain("refactor and test the database module")
        assert len(plan.tasks) >= 2
        types = [t.type for t in plan.tasks]
        assert TaskType.REFACTOR in types
        assert TaskType.TESTING in types

    def test_timing_is_recorded(self):
        config = SkillConfig()
        executor = Executor(config=config)
        result = executor.run("implement something")
        assert result.metrics["total_duration_ms"] > 0
        assert result.metrics["planning_duration_ms"] >= 0

    def test_task_duration_tracked(self):
        config = SkillConfig()
        executor = Executor(config=config)
        result = executor.run("implement a function")
        for task in result.tasks:
            assert task.duration_ms >= 0

    def test_explain_applies_configured_policy_overrides(self):
        config = SkillConfig(policy_overrides={"planning": "balanced"})
        executor = Executor(config=config)
        adapter = ClaudeCodeHostAdapter()

        with (
            patch(
                "routesmith.executor.detect_host",
                return_value=HostDetectionResult(
                    host_name="claude_code",
                    confidence=1.0,
                    detection_method="test",
                ),
            ),
            patch("routesmith.executor.get_host_adapter", return_value=adapter),
        ):
            plan = executor.explain("plan the architecture")

        planning_tasks = [task for task in plan.tasks if task.type == TaskType.PLANNING]
        assert planning_tasks
        assert planning_tasks[0].preferred_capability_class == CapabilityClass.BALANCED
        assert planning_tasks[0].suggested_model == adapter.resolve_capability_class(
            CapabilityClass.BALANCED
        )

    def test_run_applies_routing_preference(self):
        config = SkillConfig(forced_host="generic", routing_preference=RoutingPreference.COST)
        executor = Executor(config=config)
        result = executor.run("plan and implement a feature")

        planning_tasks = [task for task in result.raw_plan.tasks if task.type == TaskType.PLANNING]
        assert planning_tasks
        assert planning_tasks[0].preferred_capability_class == CapabilityClass.BALANCED

    def test_explain_applies_python_policy_plugins(self):
        config = SkillConfig(
            policy_plugins=["tests.sample_policy_plugin:PreferBalancedPlanningPlugin"],
        )
        executor = Executor(config=config)
        adapter = ClaudeCodeHostAdapter()

        with (
            patch(
                "routesmith.executor.detect_host",
                return_value=HostDetectionResult(
                    host_name="claude_code",
                    confidence=1.0,
                    detection_method="test",
                ),
            ),
            patch("routesmith.executor.get_host_adapter", return_value=adapter),
        ):
            plan = executor.explain("plan the architecture")

        planning_tasks = [task for task in plan.tasks if task.type == TaskType.PLANNING]
        assert planning_tasks
        assert planning_tasks[0].preferred_capability_class == CapabilityClass.BALANCED
        assert any("[prefer_balanced_planning]" in msg for msg in plan.advisory)


class TestPersistentState:
    """Test route saving/loading with temp directories."""

    def test_save_and_list_routes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SkillConfig(save_routes=True, routes_dir=str(Path(tmpdir) / "routes"))
            executor = Executor(config=config)
            executor.run("implement a function")

            routes = list_routes(config.routes_dir)
            assert len(routes) == 1
            assert routes[0]["host"] in (
                "claude_code",
                "codex",
                "gemini_cli",
                "copilot",
                "aider",
                "unknown",
            )

    def test_multiple_routes_saved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = SkillConfig(save_routes=True, routes_dir=str(Path(tmpdir) / "routes"))
            executor = Executor(config=config)
            executor.run("implement a function")
            executor.run("test the function")

            routes = list_routes(config.routes_dir)
            assert len(routes) == 2


class TestConfigFile:
    """Test .routesmith.toml config loading."""

    def test_loads_from_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = """[routesmith]
default_mode = "plan"
debug = true
show_metrics = false
"""
            config_path = Path(tmpdir) / ".routesmith.toml"
            config_path.write_text(config_content)

            with patch("routesmith.config.Path.cwd", return_value=Path(tmpdir)):
                config = load_config()
                assert config.default_mode == "plan"
                assert config.debug is True
                assert config.show_metrics is False

    def test_env_overrides_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = """[routesmith]
default_mode = "plan"
"""
            config_path = Path(tmpdir) / ".routesmith.toml"
            config_path.write_text(config_content)

            with (
                patch("routesmith.config.Path.cwd", return_value=Path(tmpdir)),
                patch.dict(os.environ, {"ROUTESMITH_DEFAULT_MODE": "fast"}),
            ):
                config = load_config()
                assert config.default_mode == "fast"

    def test_loads_policy_overrides_from_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = """[routesmith]
default_mode = "auto"

[routesmith.policy_overrides]
planning = "balanced"
deep_reasoning = "coding"
"""
            config_path = Path(tmpdir) / ".routesmith.toml"
            config_path.write_text(config_content)

            with patch("routesmith.config.Path.cwd", return_value=Path(tmpdir)):
                config = load_config()
                assert config.policy_overrides == {
                    "planning": "balanced",
                    "deep_reasoning": "coding",
                }

    def test_loads_routing_preference_and_plugins_from_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = """[routesmith]
routing_preference = "cost"
policy_plugins = ["tests.sample_policy_plugin:PreferBalancedPlanningPlugin"]
"""
            config_path = Path(tmpdir) / ".routesmith.toml"
            config_path.write_text(config_content)

            with patch("routesmith.config.Path.cwd", return_value=Path(tmpdir)):
                config = load_config()
                assert config.routing_preference == RoutingPreference.COST
                assert config.policy_plugins == [
                    "tests.sample_policy_plugin:PreferBalancedPlanningPlugin"
                ]

    def test_loads_performance_store_settings_from_toml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = """[routesmith]
performance_routing_enabled = false
performance_store_file = ".routesmith/custom-performance.json"
performance_max_records = 42
performance_max_age_days = 7
"""
            config_path = Path(tmpdir) / ".routesmith.toml"
            config_path.write_text(config_content)

            with patch("routesmith.config.Path.cwd", return_value=Path(tmpdir)):
                config = load_config()
                assert config.performance_routing_enabled is False
                assert config.performance_store_file == ".routesmith/custom-performance.json"
                assert config.performance_max_records == 42
                assert config.performance_max_age_days == 7


class TestMetricsComputation:
    """Test the metrics module directly."""

    def test_token_savings_calculated(self):
        from routesmith.types import RoutePlan, TaskNode, TaskResult, HostCapabilities
        from routesmith.types import CapabilityClass

        plan = RoutePlan(
            original_prompt="plan and implement",
            tasks=[
                TaskNode(
                    id="planning_0", type=TaskType.PLANNING,
                    title="Plan", preferred_capability_class=CapabilityClass.DEEP_REASONING,
                ),
                TaskNode(
                    id="coding_1", type=TaskType.CODING,
                    title="Code", preferred_capability_class=CapabilityClass.CODING,
                ),
            ],
        )
        results = [
            TaskResult(task_id="planning_0", model_used="opus", success=True),
            TaskResult(task_id="coding_1", model_used="sonnet", success=True),
        ]
        caps = HostCapabilities(
            host_name="test", model_family="anthropic",
            supports_dynamic_switch=True,
        )

        metrics = compute_metrics(plan, results, caps)
        assert metrics.estimated_tokens_saved > 0
        assert metrics.token_savings_percent > 0
        assert metrics.total_tasks == 2

    def test_effectiveness_score(self):
        from routesmith.types import RoutePlan, TaskNode, TaskResult, HostCapabilities
        from routesmith.types import CapabilityClass

        plan = RoutePlan(
            original_prompt="implement",
            tasks=[
                TaskNode(
                    id="coding_0", type=TaskType.CODING,
                    title="Code", preferred_capability_class=CapabilityClass.CODING,
                ),
            ],
        )
        results = [
            TaskResult(task_id="coding_0", model_used="sonnet", success=True),
        ]
        caps = HostCapabilities(
            host_name="test", model_family="anthropic",
            supports_dynamic_switch=True,
        )

        metrics = compute_metrics(plan, results, caps)
        # Single task, successful: base score
        assert metrics.effectiveness_score >= 0
