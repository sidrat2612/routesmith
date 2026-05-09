"""Advisory messages for routesmith."""

from __future__ import annotations

from routesmith.types import HostCapabilities, RoutePlan


PINNED_MODEL_ADVISORY = (
    "Pinned model execution is active. Auto mode is recommended for mixed tasks "
    "because routesmith can decompose planning, coding, testing, and documentation "
    "into separate steps and use the best available host-compatible model where supported."
)

NO_SWITCH_ADVISORY = (
    "This host does not support dynamic model switching. "
    "routesmith will optimize prompts and decompose tasks, but cannot change models."
)

SINGLE_TASK_ADVISORY = (
    "Single-task prompt detected. No multi-step decomposition needed."
)

DELEGATION_TIER_ADVISORY = (
    "Use the cheapest capability tier that can handle each subtask. "
    "Reserve deep reasoning for planning, architecture, and tradeoff decisions."
)

TASK_COMPLEXITY_ADVISORY = (
    "Complex plan may benefit from parallel delegation."
)

TOOL_COST_ADVISORY = (
    "Prefer low-cost tool alternatives: text-first web fetch over screenshot-heavy browsing, "
    "extracted PDF text over heavier readers, and reusable helpers for repeated fetch workflows."
)


def generate_advisory(
    plan: RoutePlan,
    capabilities: HostCapabilities,
    pinned_model: str | None = None,
    max_spawn_depth: int = 2,
) -> list[str]:
    """Generate advisory messages based on plan and host capabilities."""
    messages: list[str] = []
    capability_classes = {task.preferred_capability_class for task in plan.tasks}

    if pinned_model:
        messages.append(PINNED_MODEL_ADVISORY)

    if not capabilities.supports_dynamic_switch:
        messages.append(NO_SWITCH_ADVISORY)

    if len(plan.tasks) == 1:
        messages.append(SINGLE_TASK_ADVISORY)

    if len(capability_classes) > 1:
        messages.append(DELEGATION_TIER_ADVISORY)

    if len(plan.tasks) > 3:
        if not capabilities.supports_dynamic_switch:
            messages.append(
                f"Complex multi-step task ({len(plan.tasks)} steps) detected in a host "
                f"without model switching. Each step will use optimized prompts."
            )
        else:
            messages.append(
                f"{TASK_COMPLEXITY_ADVISORY} "
                f"Plan has {len(plan.tasks)} subtasks; "
                f"generated host configs limit subagent nesting to {max_spawn_depth} levels."
            )

    if capabilities.supports_context_management:
        messages.append(TOOL_COST_ADVISORY)

    return messages
