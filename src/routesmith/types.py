"""Core domain types for routesmith."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TaskType(str, Enum):
    """Abstract task types recognized by routesmith."""

    PLANNING = "planning"
    ANALYSIS = "analysis"
    CODING = "coding"
    TESTING = "testing"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    FORMATTING = "formatting"
    REVIEW = "review"


class CapabilityClass(str, Enum):
    """Capability classes that map to host-specific models."""

    DEEP_REASONING = "deep_reasoning"
    CODING = "coding"
    BALANCED = "balanced"
    FAST = "fast"


class RoutingPreference(str, Enum):
    """Built-in routing preferences that shape model selection."""

    BALANCED = "balanced"
    COST = "cost"
    QUALITY = "quality"


class TaskNode(BaseModel):
    """A single task in a route plan."""

    id: str
    type: TaskType
    title: str
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)
    preferred_capability_class: CapabilityClass
    suggested_model: str | None = None
    priority: int = 1
    confidence: float = 1.0


class RoutePlan(BaseModel):
    """A complete route plan for a prompt."""

    mode: str = "auto"
    original_prompt: str
    host: str = "unknown"
    tasks: list[TaskNode] = Field(default_factory=list)
    advisory: list[str] = Field(default_factory=list)
    rationale: str = ""


class TaskResult(BaseModel):
    """Result of executing a single task."""

    task_id: str
    model_used: str | None = None
    output_text: str = ""
    artifacts: list[str] = Field(default_factory=list)
    success: bool = True
    warnings: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0


class RunResult(BaseModel):
    """Result of a full routesmith run."""

    final_output: str = ""
    route_summary: str = ""
    advisory: list[str] = Field(default_factory=list)
    tasks: list[TaskResult] = Field(default_factory=list)
    raw_plan: RoutePlan | None = None
    host: str = "unknown"
    metrics: Any = None  # RouteMetrics (forward ref to avoid circular import)


class HostCapabilities(BaseModel):
    """Capabilities of a detected host environment."""

    host_name: str
    detected: bool = False
    current_model: str | None = None
    available_models: list[str] = Field(default_factory=list)
    supports_dynamic_switch: bool = False
    supports_prompt_files: bool = False
    supports_repo_instructions: bool = False
    supports_settings_edit: bool = False
    supports_env_override: bool = False
    model_family: str = "unknown"
    notes: list[str] = Field(default_factory=list)


class HostDetectionResult(BaseModel):
    """Result of host detection."""

    host_name: str
    confidence: float = 0.0
    detection_method: str = ""
    root_path: str | None = None


class InstallResult(BaseModel):
    """Result of an install operation."""

    target: str
    success: bool = True
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SkillConfig(BaseModel):
    """Configuration for routesmith."""

    default_mode: str = "auto"
    allow_model_switch: bool = True
    routing_preference: RoutingPreference = RoutingPreference.BALANCED

    @field_validator("routing_preference", mode="before")
    @classmethod
    def _normalize_routing_preference(cls, v: Any) -> str:
        if isinstance(v, RoutingPreference):
            return v.value
        normalized = str(v).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized not in {p.value for p in RoutingPreference}:
            return RoutingPreference.BALANCED.value
        return normalized

    debug: bool = False
    telemetry_enabled: bool = False
    forced_host: str | None = None
    default_host: str | None = None
    show_metrics: bool = True
    save_routes: bool = False
    routes_dir: str = ".routesmith/routes"
    performance_routing_enabled: bool = True
    performance_store_file: str = ".routesmith/performance.json"
    performance_max_records: int = 500
    performance_max_age_days: float | None = None
    config_file: str | None = None
    policy_overrides: dict[str, str] = Field(default_factory=dict)
    policy_plugins: list[str] = Field(default_factory=list)
