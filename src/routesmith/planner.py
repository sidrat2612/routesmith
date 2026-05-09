"""Prompt decomposition and task planning."""

from __future__ import annotations

import math
import re
from typing import Sequence

from routesmith.types import CapabilityClass, RoutePlan, TaskNode, TaskType
from routesmith.policy import get_capability_class, get_task_dependencies, get_task_priority


# Verb/phrase patterns mapped to task types with weights
TASK_PATTERNS: dict[TaskType, list[tuple[str, float]]] = {
    TaskType.PLANNING: [
        (r"\bplan\b", 0.8), (r"\bdesign\b", 0.7), (r"\barchitect", 0.9),
        (r"\bblueprint\b", 0.8), (r"\bstrateg", 0.7), (r"\bpropos", 0.5),
    ],
    TaskType.ANALYSIS: [
        (r"\banalyz", 0.9), (r"\banalys", 0.9), (r"\binvestigat", 0.8),
        (r"\bresearch\b", 0.7), (r"\bexplor", 0.6), (r"\bunderstand\b", 0.5),
        (r"\bdiagnos", 0.8),
    ],
    TaskType.CODING: [
        (r"\bimplement", 0.9), (r"\bbuild\b", 0.8), (r"\bcode\b", 0.8),
        (r"\bcreate\b", 0.7), (r"\bwrite\b(?!.*doc)", 0.6),
        (r"\bdevelop", 0.8), (r"\badd\b(?!.*test)", 0.5), (r"\bintegrat", 0.7),
    ],
    TaskType.TESTING: [
        (r"\btest", 0.9), (r"\bverif", 0.8), (r"\bvalidat", 0.7),
        (r"\bassert", 0.7), (r"\bcheck\b", 0.4), (r"\bensure\b", 0.3),
    ],
    TaskType.REFACTOR: [
        (r"\brefactor", 0.95), (r"\brestructur", 0.9), (r"\bclean\s*up", 0.8),
        (r"\boptimiz", 0.7), (r"\bimprove\b(?!.*doc)", 0.5), (r"\bsimplif", 0.7),
    ],
    TaskType.DOCUMENTATION: [
        (r"\bdoc(?:ument)?", 0.8), (r"\bwrite\s+doc", 0.9), (r"\breadme\b", 0.9),
        (r"\bcomment", 0.5), (r"\bexplain\b.*(?:code|function|method)", 0.6),
    ],
    TaskType.FORMATTING: [
        (r"\bformat", 0.9), (r"\blint", 0.9), (r"\bstyle\b", 0.6),
        (r"\bprettier\b", 0.9), (r"\bindent", 0.7),
    ],
    TaskType.REVIEW: [
        (r"\breview\b", 0.9), (r"\baudit\b", 0.9), (r"\binspect\b", 0.7),
        (r"\bfeedback\b", 0.6), (r"\bcritique\b", 0.7),
    ],
}

# Explicit markers: [plan], [code], [test], [review], [refactor], [docs], [format], [analyze]
EXPLICIT_MARKERS: dict[str, TaskType] = {
    "plan": TaskType.PLANNING,
    "code": TaskType.CODING,
    "implement": TaskType.CODING,
    "test": TaskType.TESTING,
    "review": TaskType.REVIEW,
    "refactor": TaskType.REFACTOR,
    "docs": TaskType.DOCUMENTATION,
    "doc": TaskType.DOCUMENTATION,
    "format": TaskType.FORMATTING,
    "lint": TaskType.FORMATTING,
    "analyze": TaskType.ANALYSIS,
    "analysis": TaskType.ANALYSIS,
}

# Confidence threshold for including a task type
CONFIDENCE_THRESHOLD = 0.3


def classify_prompt(prompt: str) -> list[tuple[TaskType, float]]:
    """Classify a prompt into task types with confidence scores.

    Returns list of (TaskType, confidence) tuples sorted by confidence descending.
    """
    prompt_lower = prompt.lower()

    # First check explicit markers: [plan], [code], [test], etc.
    explicit_types: list[tuple[TaskType, float]] = []
    marker_pattern = r"\[(\w+)\]"
    markers = re.findall(marker_pattern, prompt_lower)
    for marker in markers:
        if marker in EXPLICIT_MARKERS:
            task_type = EXPLICIT_MARKERS[marker]
            explicit_types.append((task_type, 1.0))

    if explicit_types:
        # Deduplicate, keep highest confidence
        seen: dict[TaskType, float] = {}
        for tt, conf in explicit_types:
            seen[tt] = max(seen.get(tt, 0), conf)
        return sorted(seen.items(), key=lambda x: x[1], reverse=True)

    # Weighted scoring: sum weights of all matching patterns per type
    scores: dict[TaskType, float] = {}
    for task_type, patterns in TASK_PATTERNS.items():
        type_score = 0.0
        match_count = 0
        for pattern, weight in patterns:
            if re.search(pattern, prompt_lower):
                type_score += weight
                match_count += 1
        if match_count > 0:
            # Normalize: average weight * (1 + log bonus for multiple matches)
            normalized = (type_score / match_count) * (1 + 0.2 * math.log(1 + match_count))
            scores[task_type] = min(normalized, 1.0)

    # Filter by threshold
    detected = [
        (tt, score) for tt, score in scores.items()
        if score >= CONFIDENCE_THRESHOLD
    ]

    # If nothing detected, default to coding
    if not detected:
        detected = [(TaskType.CODING, 0.5)]

    # Sort by confidence
    detected.sort(key=lambda x: x[1], reverse=True)
    return detected


def _make_task_id(task_type: TaskType, index: int) -> str:
    """Generate a deterministic task ID."""
    return f"{task_type.value}_{index}"


def _build_task_node(
    task_type: TaskType,
    index: int,
    all_types: list[TaskType],
    prompt: str,
    confidence: float = 1.0,
) -> TaskNode:
    """Build a TaskNode for a given type."""
    deps = get_task_dependencies(task_type, all_types)
    dep_ids = [_make_task_id(d, all_types.index(d)) for d in deps if d in all_types]

    title_map = {
        TaskType.PLANNING: "Plan and design the approach",
        TaskType.ANALYSIS: "Analyze requirements and context",
        TaskType.CODING: "Implement the solution",
        TaskType.TESTING: "Write and run tests",
        TaskType.REFACTOR: "Refactor and improve code quality",
        TaskType.DOCUMENTATION: "Write documentation",
        TaskType.FORMATTING: "Apply formatting and style fixes",
        TaskType.REVIEW: "Review and validate the work",
    }

    desc_map = {
        TaskType.PLANNING: "Break down the requirements and design the approach before implementation.",
        TaskType.ANALYSIS: "Analyze the existing code, requirements, and context to inform the solution.",
        TaskType.CODING: "Write the implementation code based on the plan.",
        TaskType.TESTING: "Create tests to verify the implementation works correctly.",
        TaskType.REFACTOR: "Improve code structure without changing behavior.",
        TaskType.DOCUMENTATION: "Document the implementation for users and maintainers.",
        TaskType.FORMATTING: "Apply consistent formatting and linting fixes.",
        TaskType.REVIEW: "Review all work for correctness, completeness, and quality.",
    }

    return TaskNode(
        id=_make_task_id(task_type, index),
        type=task_type,
        title=title_map.get(task_type, f"Execute {task_type.value} task"),
        description=desc_map.get(task_type, ""),
        dependencies=dep_ids,
        preferred_capability_class=get_capability_class(task_type),
        priority=get_task_priority(task_type),
        confidence=confidence,
    )


class Planner:
    """Decomposes prompts into task graphs."""

    def plan(self, prompt: str, host_name: str = "unknown") -> RoutePlan:
        """Create a route plan from a prompt.

        This is a deterministic, keyword-based planner that does not require
        API calls. It classifies the prompt, creates task nodes, infers
        dependencies, and produces a rationale.
        """
        classified = classify_prompt(prompt)
        task_types = [tt for tt, _ in classified]
        tasks: list[TaskNode] = []

        for i, (task_type, confidence) in enumerate(classified):
            node = _build_task_node(task_type, i, task_types, prompt, confidence)
            tasks.append(node)

        # Sort by priority
        tasks.sort(key=lambda t: t.priority)

        # Build rationale
        if len(tasks) == 1:
            conf_str = f" (confidence: {classified[0][1]:.0%})"
            rationale = (
                f"Single-task prompt detected: {tasks[0].type.value}{conf_str}. "
                f"No decomposition needed."
            )
        else:
            type_names = ", ".join(
                f"{t.type.value}({c:.0%})" for t, (_, c) in zip(tasks, classified)
            )
            rationale = (
                f"Multi-task prompt detected with {len(tasks)} steps: {type_names}. "
                f"Tasks ordered by dependency and priority."
            )

        return RoutePlan(
            mode="auto",
            original_prompt=prompt,
            host=host_name,
            tasks=tasks,
            rationale=rationale,
        )
