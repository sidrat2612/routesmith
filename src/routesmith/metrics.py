"""Route metrics - measures how routesmith helped the user."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from routesmith.types import (
    CapabilityClass,
    HostCapabilities,
    RoutePlan,
    TaskNode,
    TaskResult,
    TaskType,
)


# Relative token cost per capability class (normalized: deep_reasoning = 1.0)
CAPABILITY_COST_RATIO: dict[CapabilityClass, float] = {
    CapabilityClass.DEEP_REASONING: 1.0,
    CapabilityClass.CODING: 0.4,
    CapabilityClass.BALANCED: 0.4,
    CapabilityClass.FAST: 0.05,
}

# Estimated token budget per task type (approximate input+output)
TASK_TOKEN_ESTIMATE: dict[TaskType, int] = {
    TaskType.PLANNING: 2000,
    TaskType.ANALYSIS: 3000,
    TaskType.CODING: 5000,
    TaskType.TESTING: 4000,
    TaskType.REFACTOR: 4000,
    TaskType.DOCUMENTATION: 3000,
    TaskType.FORMATTING: 1000,
    TaskType.REVIEW: 2500,
}


class ModelUsage(BaseModel):
    """Token and task usage for a single model."""

    model: str
    tasks_handled: int = 0
    estimated_tokens: int = 0
    capability_class: str = ""


class RouteMetrics(BaseModel):
    """Comprehensive metrics for a routesmith run."""

    # Timing
    total_duration_ms: float = 0.0
    planning_duration_ms: float = 0.0
    routing_duration_ms: float = 0.0
    execution_duration_ms: float = 0.0

    # Task stats
    total_tasks: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_with_model_switch: int = 0
    tasks_with_prompt_strategy: int = 0

    # Model usage breakdown
    models_used: list[ModelUsage] = Field(default_factory=list)
    unique_models_count: int = 0

    # Token economics
    estimated_total_tokens: int = 0
    estimated_tokens_without_routing: int = 0
    estimated_tokens_saved: int = 0
    token_savings_percent: float = 0.0

    # Effectiveness
    decomposition_count: int = 0
    capability_classes_utilized: list[str] = Field(default_factory=list)
    switching_supported: bool = False
    switching_applied: bool = False
    prompt_strategy_applied: bool = False

    # Summary
    effectiveness_score: float = 0.0
    summary: str = ""


def compute_metrics(
    plan: RoutePlan,
    results: list[TaskResult],
    capabilities: HostCapabilities,
    timing: dict[str, float] | None = None,
) -> RouteMetrics:
    """Compute route metrics from a completed run."""
    timing = timing or {}

    # Task stats
    total_tasks = len(results)
    succeeded = sum(1 for r in results if r.success)
    failed = total_tasks - succeeded

    switched = sum(
        1 for r in results
        if r.model_used and not any("not available" in w for w in r.warnings)
    )
    prompt_strategy = sum(
        1 for r in results
        if any("prompt strategy" in w for w in r.warnings)
    )

    # Model usage breakdown
    model_tasks: dict[str, list[TaskResult]] = defaultdict(list)
    for result in results:
        key = result.model_used or "prompt_strategy"
        model_tasks[key].append(result)

    # Map task_ids to plan tasks for token estimation
    task_map = {t.id: t for t in plan.tasks}

    models_used: list[ModelUsage] = []
    for model_name, task_results in model_tasks.items():
        estimated_tokens = 0
        cap_class = ""
        for tr in task_results:
            task_node = task_map.get(tr.task_id)
            if task_node:
                estimated_tokens += TASK_TOKEN_ESTIMATE.get(task_node.type, 3000)
                cap_class = task_node.preferred_capability_class.value
        models_used.append(ModelUsage(
            model=model_name,
            tasks_handled=len(task_results),
            estimated_tokens=estimated_tokens,
            capability_class=cap_class,
        ))

    # Token economics
    # Without routing: all tasks use the most expensive model (deep_reasoning cost)
    estimated_without_routing = sum(
        TASK_TOKEN_ESTIMATE.get(t.type, 3000) for t in plan.tasks
    )
    # Cost-weighted: multiply token estimate by the capability cost ratio
    estimated_with_routing = 0
    for task in plan.tasks:
        base_tokens = TASK_TOKEN_ESTIMATE.get(task.type, 3000)
        cost_ratio = CAPABILITY_COST_RATIO.get(task.preferred_capability_class, 1.0)
        estimated_with_routing += int(base_tokens * cost_ratio)

    tokens_saved = estimated_without_routing - estimated_with_routing
    savings_percent = (tokens_saved / estimated_without_routing * 100) if estimated_without_routing > 0 else 0.0

    # Capability classes utilized
    cap_classes = list({t.preferred_capability_class.value for t in plan.tasks})

    # Effectiveness score (0-100)
    score = 0.0
    if total_tasks > 1:
        score += 30.0  # Decomposition value
    if switched > 0:
        score += 30.0  # Actual switching value
    elif prompt_strategy > 0:
        score += 15.0  # Prompt strategy still helps
    if succeeded == total_tasks:
        score += 20.0  # All tasks succeeded
    if len(cap_classes) > 1:
        score += 10.0  # Multiple capability classes = smart routing
    if tokens_saved > 0:
        score += 10.0  # Cost savings

    score = min(score, 100.0)

    # Summary
    summary_parts: list[str] = []
    if total_tasks > 1:
        summary_parts.append(f"Decomposed into {total_tasks} focused subtasks")
    if switched > 0:
        summary_parts.append(f"Switched models for {switched}/{total_tasks} tasks")
    elif prompt_strategy > 0:
        summary_parts.append(f"Applied prompt optimization for {prompt_strategy} tasks")
    if tokens_saved > 0:
        summary_parts.append(f"~{savings_percent:.0f}% token cost reduction via capability-matched routing")
    if len(set(m.model for m in models_used)) > 1:
        summary_parts.append(f"Used {len(set(m.model for m in models_used))} different models")

    summary = ". ".join(summary_parts) + "." if summary_parts else "Single task executed."

    return RouteMetrics(
        total_duration_ms=timing.get("total", 0.0),
        planning_duration_ms=timing.get("planning", 0.0),
        routing_duration_ms=timing.get("routing", 0.0),
        execution_duration_ms=timing.get("execution", 0.0),
        total_tasks=total_tasks,
        tasks_succeeded=succeeded,
        tasks_failed=failed,
        tasks_with_model_switch=switched,
        tasks_with_prompt_strategy=prompt_strategy,
        models_used=models_used,
        unique_models_count=len(set(m.model for m in models_used)),
        estimated_total_tokens=estimated_with_routing,
        estimated_tokens_without_routing=estimated_without_routing,
        estimated_tokens_saved=tokens_saved,
        token_savings_percent=savings_percent,
        decomposition_count=total_tasks,
        capability_classes_utilized=cap_classes,
        switching_supported=capabilities.supports_dynamic_switch,
        switching_applied=switched > 0,
        prompt_strategy_applied=prompt_strategy > 0,
        effectiveness_score=score,
        summary=summary,
    )
