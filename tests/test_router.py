"""Tests for the router."""

import tempfile
from pathlib import Path

from routesmith.hosts.claude_code import ClaudeCodeHostAdapter
from routesmith.hosts.copilot import CopilotHostAdapter
from routesmith.hosts.generic import GenericHostAdapter
from routesmith.performance import PerformanceTracker
from routesmith.planner import Planner
from routesmith.router import Router
from routesmith.types import RoutePlan, TaskNode, TaskResult
from routesmith.types import CapabilityClass, RoutingPreference, TaskType


class TestRouterWithSwitchableHost:
    """Test router with a host that supports dynamic switching."""

    def setup_method(self):
        self.adapter = ClaudeCodeHostAdapter()
        self.router = Router(self.adapter)
        self.planner = Planner()

    def test_tasks_get_suggested_models(self):
        plan = self.planner.plan("plan and implement a feature", host_name="claude_code")
        resolved = self.router.resolve_plan(plan)

        for task in resolved.tasks:
            assert task.suggested_model is not None

    def test_planning_gets_deep_reasoning_model(self):
        plan = self.planner.plan("plan the architecture", host_name="claude_code")
        resolved = self.router.resolve_plan(plan)

        planning_tasks = [t for t in resolved.tasks if t.type == TaskType.PLANNING]
        if planning_tasks:
            expected = self.adapter.resolve_capability_class(CapabilityClass.DEEP_REASONING)
            assert planning_tasks[0].suggested_model == expected

    def test_coding_gets_coding_model(self):
        plan = self.planner.plan("implement a function", host_name="claude_code")
        resolved = self.router.resolve_plan(plan)

        coding_tasks = [t for t in resolved.tasks if t.type == TaskType.CODING]
        if coding_tasks:
            expected = self.adapter.resolve_capability_class(CapabilityClass.CODING)
            assert coding_tasks[0].suggested_model == expected

    def test_no_advisory_about_switching(self):
        plan = self.planner.plan("implement something", host_name="claude_code")
        resolved = self.router.resolve_plan(plan)

        for msg in resolved.advisory:
            assert "does not support dynamic model switching" not in msg

    def test_task_type_policy_override_changes_model(self):
        router = Router(self.adapter, policy_overrides={"planning": "balanced"})
        plan = self.planner.plan("plan the architecture", host_name="claude_code")
        resolved = router.resolve_plan(plan)

        planning_tasks = [t for t in resolved.tasks if t.type == TaskType.PLANNING]
        assert planning_tasks
        assert planning_tasks[0].preferred_capability_class == CapabilityClass.BALANCED
        assert planning_tasks[0].suggested_model == self.adapter.resolve_capability_class(
            CapabilityClass.BALANCED
        )
        assert any("Applied policy override for planning" in msg for msg in resolved.advisory)

    def test_capability_override_changes_model(self):
        router = Router(self.adapter, policy_overrides={"deep_reasoning": "coding"})
        plan = self.planner.plan("plan the architecture", host_name="claude_code")
        resolved = router.resolve_plan(plan)

        planning_tasks = [t for t in resolved.tasks if t.type == TaskType.PLANNING]
        assert planning_tasks
        assert planning_tasks[0].preferred_capability_class == CapabilityClass.CODING
        assert planning_tasks[0].suggested_model == self.adapter.resolve_capability_class(
            CapabilityClass.CODING
        )
        assert any(
            "Applied capability override for deep_reasoning" in msg
            for msg in resolved.advisory
        )

    def test_cost_routing_downgrades_planning_to_balanced(self):
        router = Router(self.adapter, routing_preference=RoutingPreference.COST)
        plan = self.planner.plan("plan the architecture", host_name="claude_code")
        resolved = router.resolve_plan(plan)

        planning_tasks = [t for t in resolved.tasks if t.type == TaskType.PLANNING]
        assert planning_tasks
        assert planning_tasks[0].preferred_capability_class == CapabilityClass.BALANCED
        assert planning_tasks[0].suggested_model == self.adapter.resolve_capability_class(
            CapabilityClass.BALANCED
        )
        assert any("Applied cost-aware routing for planning" in msg for msg in resolved.advisory)

    def test_python_policy_plugin_can_override_model(self):
        router = Router(
            self.adapter,
            policy_plugins=["tests.sample_policy_plugin:PreferFastClaudeCodingPlugin"],
        )
        plan = self.planner.plan("implement a function", host_name="claude_code")
        resolved = router.resolve_plan(plan)

        coding_tasks = [t for t in resolved.tasks if t.type == TaskType.CODING]
        assert coding_tasks
        assert coding_tasks[0].suggested_model == "claude-haiku-4-5"
        assert any("[prefer_fast_claude_coding]" in msg for msg in resolved.advisory)

    def test_performance_aware_routing_deprioritizes_low_success_default_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "performance.json")
            for run_index in range(4):
                plan = RoutePlan(
                    original_prompt=f"synthetic run {run_index}",
                    tasks=[
                        TaskNode(
                            id=f"sonnet-{run_index}",
                            type=TaskType.CODING,
                            title="Coding task",
                            preferred_capability_class=CapabilityClass.CODING,
                        ),
                        TaskNode(
                            id=f"haiku-{run_index}",
                            type=TaskType.CODING,
                            title="Coding task",
                            preferred_capability_class=CapabilityClass.CODING,
                        ),
                    ],
                )
                tracker.record_run(
                    plan,
                    [
                        TaskResult(
                            task_id=f"sonnet-{run_index}",
                            model_used="claude-sonnet-4-6",
                            success=run_index == 0,
                            duration_ms=6200,
                        ),
                        TaskResult(
                            task_id=f"haiku-{run_index}",
                            model_used="claude-haiku-4-5",
                            success=True,
                            duration_ms=1200,
                        ),
                    ],
                )

            router = Router(self.adapter, performance_tracker=tracker)
            plan = self.planner.plan("implement a function", host_name="claude_code")
            resolved = router.resolve_plan(plan)

            coding_tasks = [t for t in resolved.tasks if t.type == TaskType.CODING]
            assert coding_tasks
            assert coding_tasks[0].suggested_model == "claude-haiku-4-5"
            assert any("Performance-aware routing selected claude-haiku-4-5" in msg for msg in resolved.advisory)


class TestRouterWithNonSwitchableHost:
    """Test router with a host that does NOT support dynamic switching."""

    def setup_method(self):
        self.adapter = CopilotHostAdapter()
        self.router = Router(self.adapter)
        self.planner = Planner()

    def test_tasks_have_no_suggested_model(self):
        plan = self.planner.plan("plan and implement", host_name="copilot")
        resolved = self.router.resolve_plan(plan)

        for task in resolved.tasks:
            assert task.suggested_model is None

    def test_advisory_about_no_switching(self):
        plan = self.planner.plan("implement something", host_name="copilot")
        resolved = self.router.resolve_plan(plan)

        assert any("does not support dynamic model switching" in msg for msg in resolved.advisory)

    def test_strategies_use_prompt_optimization(self):
        plan = self.planner.plan("implement and test", host_name="copilot")
        resolved = self.router.resolve_plan(plan)
        strategies = self.router.get_strategies(resolved)

        for strategy in strategies:
            assert strategy["strategy"] == "prompt_optimization"

    def test_policy_override_changes_prompt_strategy_target(self):
        router = Router(self.adapter, policy_overrides={"documentation": "fast"})
        plan = self.planner.plan("write docs for this feature", host_name="copilot")
        resolved = router.resolve_plan(plan)

        documentation_tasks = [t for t in resolved.tasks if t.type == TaskType.DOCUMENTATION]
        assert documentation_tasks
        assert documentation_tasks[0].preferred_capability_class == CapabilityClass.FAST
        assert any("Applied policy override for documentation" in msg for msg in resolved.advisory)

    def test_quality_routing_upgrades_docs_capability(self):
        router = Router(self.adapter, routing_preference=RoutingPreference.QUALITY)
        plan = self.planner.plan("write docs for this feature", host_name="copilot")
        resolved = router.resolve_plan(plan)

        documentation_tasks = [t for t in resolved.tasks if t.type == TaskType.DOCUMENTATION]
        assert documentation_tasks
        assert documentation_tasks[0].preferred_capability_class == CapabilityClass.CODING
        assert any("Applied quality-first routing for documentation" in msg for msg in resolved.advisory)


class TestRouterWithGenericHost:
    """Test router with generic fallback host."""

    def setup_method(self):
        self.adapter = GenericHostAdapter()
        self.router = Router(self.adapter)
        self.planner = Planner()

    def test_no_model_assigned(self):
        plan = self.planner.plan("implement a feature", host_name="generic")
        resolved = self.router.resolve_plan(plan)

        for task in resolved.tasks:
            assert task.suggested_model is None

    def test_strategy_is_prompt_only(self):
        plan = self.planner.plan("implement and test", host_name="generic")
        resolved = self.router.resolve_plan(plan)
        strategies = self.router.get_strategies(resolved)

        for strategy in strategies:
            assert strategy["strategy"] == "prompt_only"

    def test_no_fake_model_switching(self):
        """Generic host must never claim models were switched."""
        plan = self.planner.plan("plan, implement, test", host_name="generic")
        resolved = self.router.resolve_plan(plan)

        for task in resolved.tasks:
            assert task.suggested_model is None
