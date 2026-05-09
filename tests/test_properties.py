"""Property-based tests for routesmith planner using hypothesis-like patterns."""

import string

import pytest

from routesmith.planner import Planner, classify_prompt, CONFIDENCE_THRESHOLD
from routesmith.types import CapabilityClass, HostCapabilities, SkillConfig, TaskType


class TestPlannerProperties:
    """Property-based tests ensuring planner invariants hold."""

    def setup_method(self):
        self.planner = Planner()

    @pytest.mark.parametrize("prompt", [
        "implement a REST API",
        "plan, implement, test, document everything",
        "refactor and optimize the code",
        "review the pull request and add tests",
        "analyze performance and fix bottlenecks",
        "format code, write docs, run linter",
        "do something random",
        "",
        "a",
        "x" * 1000,
    ])
    def test_planner_never_crashes(self, prompt):
        """Planner must produce a valid plan for any input."""
        plan = self.planner.plan(prompt)
        assert plan is not None
        assert len(plan.tasks) >= 1
        assert plan.mode == "auto"

    @pytest.mark.parametrize("prompt", [
        "implement a REST API",
        "plan, implement, test, document everything",
        "refactor and optimize the code",
        "review the pull request",
    ])
    def test_all_tasks_have_valid_capability_class(self, prompt):
        """Every task must map to a valid capability class."""
        plan = self.planner.plan(prompt)
        for task in plan.tasks:
            assert task.preferred_capability_class in CapabilityClass

    @pytest.mark.parametrize("prompt", [
        "plan and implement",
        "test and review",
        "analyze, code, document",
    ])
    def test_task_ids_are_unique(self, prompt):
        """All task IDs in a plan must be unique."""
        plan = self.planner.plan(prompt)
        ids = [t.id for t in plan.tasks]
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize("prompt", [
        "plan and implement a feature",
        "implement and then test",
        "analyze, plan, implement, test, review, document",
    ])
    def test_dependencies_reference_existing_tasks(self, prompt):
        """Dependencies must reference task IDs that exist in the plan."""
        plan = self.planner.plan(prompt)
        all_ids = {t.id for t in plan.tasks}
        for task in plan.tasks:
            for dep in task.dependencies:
                assert dep in all_ids, f"Task {task.id} depends on non-existent {dep}"

    def test_classify_always_returns_at_least_one(self):
        """Classification must always return at least one task type."""
        prompts = ["", "xyzzy", "a b c", "12345", "!!!"]
        for prompt in prompts:
            result = classify_prompt(prompt)
            assert len(result) >= 1

    def test_confidence_scores_in_range(self):
        """All confidence scores must be in (0, 1]."""
        prompts = [
            "implement a REST API",
            "plan and test everything",
            "random words here",
        ]
        for prompt in prompts:
            result = classify_prompt(prompt)
            for _, conf in result:
                assert 0 < conf <= 1.0

    def test_explicit_markers_override_patterns(self):
        """Explicit markers like [code] should force that classification."""
        result = classify_prompt("[test] implement the feature")
        types = [tt for tt, _ in result]
        assert TaskType.TESTING in types

    def test_plan_is_deterministic(self):
        """Same input should always produce same plan."""
        plan1 = self.planner.plan("implement and test a feature")
        plan2 = self.planner.plan("implement and test a feature")
        assert len(plan1.tasks) == len(plan2.tasks)
        for t1, t2 in zip(plan1.tasks, plan2.tasks):
            assert t1.id == t2.id
            assert t1.type == t2.type
            assert t1.confidence == t2.confidence

    def test_priorities_are_positive(self):
        """All task priorities must be positive integers."""
        plan = self.planner.plan("plan, implement, test, document everything")
        for task in plan.tasks:
            assert task.priority >= 1


class TestTypeProperties:
    """Property checks for core configuration types."""

    def test_skill_config_defaults_include_context_controls(self):
        config = SkillConfig()
        assert config.context_window_limit is True
        assert config.autocompact_threshold == 80
        assert config.max_spawn_depth == 2

    def test_host_capabilities_context_management_defaults_false(self):
        capabilities = HostCapabilities(host_name="test")
        assert capabilities.supports_context_management is False

    def test_autocompact_threshold_clamps_below_zero(self):
        config = SkillConfig(autocompact_threshold=-10)
        assert config.autocompact_threshold == 0

    def test_autocompact_threshold_clamps_above_hundred(self):
        config = SkillConfig(autocompact_threshold=200)
        assert config.autocompact_threshold == 100

    def test_autocompact_threshold_accepts_valid_value(self):
        config = SkillConfig(autocompact_threshold=50)
        assert config.autocompact_threshold == 50

    def test_max_spawn_depth_clamps_below_one(self):
        config = SkillConfig(max_spawn_depth=-3)
        assert config.max_spawn_depth == 1

    def test_max_spawn_depth_clamps_zero_to_one(self):
        config = SkillConfig(max_spawn_depth=0)
        assert config.max_spawn_depth == 1

    def test_max_spawn_depth_accepts_valid_value(self):
        config = SkillConfig(max_spawn_depth=5)
        assert config.max_spawn_depth == 5
