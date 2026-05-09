"""Tests for advisory messages."""

import pytest

from routesmith.advisory import (
    DELEGATION_TIER_ADVISORY,
    NO_SWITCH_ADVISORY,
    PINNED_MODEL_ADVISORY,
    SINGLE_TASK_ADVISORY,
    TASK_COMPLEXITY_ADVISORY,
    TOOL_COST_ADVISORY,
    generate_advisory,
)
from routesmith.planner import Planner
from routesmith.types import HostCapabilities, RoutePlan, TaskNode, TaskType, CapabilityClass


def _make_capabilities(supports_switch: bool = False) -> HostCapabilities:
    return HostCapabilities(
        host_name="test",
        detected=True,
        supports_dynamic_switch=supports_switch,
        model_family="test",
    )


def _make_plan(num_tasks: int = 1, task_types: list[TaskType] | None = None) -> RoutePlan:
    task_types = task_types or [TaskType.CODING] * num_tasks
    tasks = [
        TaskNode(
            id=f"task_{i}",
            type=task_type,
            title=f"Task {i}",
            preferred_capability_class=(
                CapabilityClass.DEEP_REASONING
                if task_type in {TaskType.PLANNING, TaskType.ANALYSIS, TaskType.REVIEW}
                else CapabilityClass.FAST
                if task_type == TaskType.FORMATTING
                else CapabilityClass.CODING
            ),
        )
        for i, task_type in enumerate(task_types)
    ]
    return RoutePlan(original_prompt="test", tasks=tasks)


class TestAdvisory:
    """Test advisory message generation."""

    def test_pinned_model_advisory(self):
        plan = _make_plan(2)
        caps = _make_capabilities(supports_switch=True)
        messages = generate_advisory(plan, caps, pinned_model="some-model")
        assert PINNED_MODEL_ADVISORY in messages

    def test_no_pinned_model_no_advisory(self):
        plan = _make_plan(2)
        caps = _make_capabilities(supports_switch=True)
        messages = generate_advisory(plan, caps, pinned_model=None)
        assert PINNED_MODEL_ADVISORY not in messages

    def test_no_switch_advisory(self):
        plan = _make_plan(2)
        caps = _make_capabilities(supports_switch=False)
        messages = generate_advisory(plan, caps)
        assert NO_SWITCH_ADVISORY in messages

    def test_switch_supported_no_advisory(self):
        plan = _make_plan(2)
        caps = _make_capabilities(supports_switch=True)
        messages = generate_advisory(plan, caps)
        assert NO_SWITCH_ADVISORY not in messages

    def test_single_task_advisory(self):
        plan = _make_plan(1)
        caps = _make_capabilities(supports_switch=True)
        messages = generate_advisory(plan, caps)
        assert SINGLE_TASK_ADVISORY in messages

    def test_complex_task_no_switch_advisory(self):
        plan = _make_plan(5)
        caps = _make_capabilities(supports_switch=False)
        messages = generate_advisory(plan, caps)
        assert any("Complex multi-step" in msg for msg in messages)

    def test_delegation_tier_advisory_for_mixed_capabilities(self):
        plan = _make_plan(task_types=[TaskType.PLANNING, TaskType.CODING, TaskType.FORMATTING])
        caps = _make_capabilities(supports_switch=True)
        messages = generate_advisory(plan, caps)
        assert DELEGATION_TIER_ADVISORY in messages

    def test_tool_cost_advisory_for_context_management_hosts(self):
        plan = _make_plan(2)
        caps = HostCapabilities(
            host_name="test",
            detected=True,
            supports_dynamic_switch=True,
            supports_context_management=True,
            model_family="test",
        )
        messages = generate_advisory(plan, caps)
        assert TOOL_COST_ADVISORY in messages

    def test_tool_cost_advisory_absent_without_context_management(self):
        plan = _make_plan(2)
        caps = HostCapabilities(
            host_name="test",
            detected=True,
            supports_dynamic_switch=True,
            supports_prompt_files=True,
            supports_context_management=False,
            model_family="test",
        )
        messages = generate_advisory(plan, caps)
        assert TOOL_COST_ADVISORY not in messages

    def test_no_duplicate_complexity_for_no_switch_host(self):
        plan = _make_plan(5)
        caps = _make_capabilities(supports_switch=False)
        messages = generate_advisory(plan, caps)
        complexity_msgs = [m for m in messages if "Complex" in m or TASK_COMPLEXITY_ADVISORY in m]
        assert len(complexity_msgs) == 1
        assert any("Complex multi-step" in msg for msg in messages)
        assert not any(TASK_COMPLEXITY_ADVISORY in msg for msg in messages)

    def test_task_complexity_advisory_when_plan_is_large(self):
        plan = _make_plan(4)
        caps = _make_capabilities(supports_switch=True)
        messages = generate_advisory(plan, caps, max_spawn_depth=2)
        assert any(TASK_COMPLEXITY_ADVISORY in msg for msg in messages)
        assert any("nesting to 2 levels" in msg for msg in messages)
