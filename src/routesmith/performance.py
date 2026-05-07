"""Real-time model performance tracking for routesmith.

Records per-model task outcomes across runs and provides performance
stats that can inform routing decisions.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from routesmith.types import CapabilityClass, RoutePlan, TaskResult


@dataclass(slots=True)
class ModelRecord:
    """A single recorded task outcome for a model."""

    model: str
    task_type: str
    capability_class: str
    success: bool
    duration_ms: float
    timestamp: float
    host_name: str = "unknown"
    source: str = "runtime"


@dataclass(slots=True)
class ModelStats:
    """Aggregated performance statistics for a model."""

    model: str
    total_tasks: int = 0
    successes: int = 0
    failures: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    task_types: dict[str, int] = field(default_factory=dict)
    capability_classes: dict[str, int] = field(default_factory=dict)
    hosts: dict[str, int] = field(default_factory=dict)
    sources: dict[str, int] = field(default_factory=dict)
    last_used: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "total_tasks": self.total_tasks,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "min_duration_ms": round(self.min_duration_ms, 1),
            "max_duration_ms": round(self.max_duration_ms, 1),
            "task_types": self.task_types,
            "capability_classes": self.capability_classes,
            "hosts": self.hosts,
            "sources": self.sources,
            "last_used": self.last_used,
        }


class PerformanceTracker:
    """Tracks and persists model performance across runs.

    Data is stored in a local JSON file so it accumulates over time
    within a project.
    """

    SCHEMA_VERSION = 2
    DEFAULT_PATH = ".routesmith/performance.json"
    MAX_RECORDS = 500  # Rolling window of recent records
    MIN_ROUTING_SAMPLES = 3
    LOW_SUCCESS_THRESHOLD = 0.75
    SLOW_MODEL_THRESHOLD_MS = 5000.0
    ALLOWED_SOURCES = {"runtime", "synthetic"}

    def __init__(
        self,
        path: str | Path | None = None,
        max_records: int | None = None,
        max_age_seconds: float | None = None,
        default_source: str = "runtime",
    ) -> None:
        self.path = Path(path) if path else Path(self.DEFAULT_PATH)
        self.max_records = self.MAX_RECORDS if max_records is None else max_records
        self.max_age_seconds = max_age_seconds
        self.default_source = self._normalize_source(default_source, allow_all=False)
        self._records: list[ModelRecord] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            payload, migrated = self._migrate_payload(data)
            for entry in payload.get("records", []):
                self._records.append(ModelRecord(
                    model=entry["model"],
                    task_type=entry["task_type"],
                    capability_class=entry["capability_class"],
                    host_name=entry.get("host_name", "unknown"),
                    source=entry.get("source", self.default_source),
                    success=entry["success"],
                    duration_ms=entry["duration_ms"],
                    timestamp=entry["timestamp"],
                ))
            if migrated:
                self._persist()
        except (OSError, json.JSONDecodeError, KeyError):
            # Corrupted file — start fresh
            self._records = []

    def _migrate_payload(self, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        schema_version = int(data.get("schema_version") or data.get("version") or 1)
        records = data.get("records", [])
        migrated = False

        if schema_version <= 1:
            migrated = True
            records = [
                {
                    **entry,
                    "host_name": entry.get("host_name", "unknown"),
                    "source": entry.get("source", "runtime"),
                }
                for entry in records
            ]
            schema_version = self.SCHEMA_VERSION
        elif schema_version == self.SCHEMA_VERSION:
            normalized_records = []
            for entry in records:
                normalized_entry = dict(entry)
                if "host_name" not in normalized_entry:
                    normalized_entry["host_name"] = "unknown"
                    migrated = True
                if "source" not in normalized_entry:
                    normalized_entry["source"] = "runtime"
                    migrated = True
                normalized_records.append(normalized_entry)
            records = normalized_records

        return {
            "schema_version": self.SCHEMA_VERSION,
            "updated": data.get("updated", time.time()),
            "records": records,
        }, migrated

    def record_run(
        self,
        plan: RoutePlan,
        results: list[TaskResult],
        host_name: str | None = None,
        source: str | None = None,
    ) -> None:
        """Record task outcomes from a completed run."""
        self._ensure_loaded()
        task_map = {t.id: t for t in plan.tasks}
        now = time.time()
        resolved_host = host_name or plan.host or "unknown"
        resolved_source = self._normalize_source(source, allow_all=False) if source else self.default_source

        for result in results:
            task_node = task_map.get(result.task_id)
            if not task_node:
                continue
            model = result.model_used or "unknown"
            self._records.append(ModelRecord(
                model=model,
                task_type=task_node.type.value,
                capability_class=task_node.preferred_capability_class.value,
                host_name=resolved_host,
                source=resolved_source,
                success=result.success,
                duration_ms=result.duration_ms,
                timestamp=now,
            ))

        self.prune(
            max_records=self.max_records,
            max_age_seconds=self.max_age_seconds,
            persist=False,
        )
        self._persist()

    def _persist(self) -> None:
        """Write records to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema_version": self.SCHEMA_VERSION,
            "updated": time.time(),
            "store": {
                "max_records": self.max_records,
                "max_age_seconds": self.max_age_seconds,
            },
            "records": [
                {
                    "model": r.model,
                    "task_type": r.task_type,
                    "capability_class": r.capability_class,
                    "host_name": r.host_name,
                    "source": r.source,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                    "timestamp": r.timestamp,
                }
                for r in self._records
            ],
        }
        self.path.write_text(json.dumps(data, indent=2))

    def _normalize_capability(self, capability: CapabilityClass | str | None) -> str | None:
        if capability is None:
            return None
        if isinstance(capability, CapabilityClass):
            return capability.value
        normalized = str(capability).strip().lower().replace("-", "_").replace(" ", "_")
        return normalized or None

    def _normalize_source(self, source: str | None, allow_all: bool = True) -> str:
        if source is None:
            return "all" if allow_all else "runtime"
        normalized = str(source).strip().lower()
        if allow_all and normalized == "all":
            return normalized
        if normalized in self.ALLOWED_SOURCES:
            return normalized
        return "all" if allow_all else "runtime"

    def _iter_filtered_records(
        self,
        model: str | None = None,
        host_name: str | None = None,
        capability: CapabilityClass | str | None = None,
        source: str | None = "all",
    ) -> list[ModelRecord]:
        self._ensure_loaded()
        capability_value = self._normalize_capability(capability)
        source_value = self._normalize_source(source)
        normalized_model = model.strip() if model else None
        normalized_host = host_name.strip() if host_name else None

        filtered: list[ModelRecord] = []
        for record in self._records:
            if normalized_model and record.model != normalized_model:
                continue
            if normalized_host and record.host_name != normalized_host:
                continue
            if capability_value and record.capability_class != capability_value:
                continue
            if source_value != "all" and record.source != source_value:
                continue
            filtered.append(record)

        return filtered

    def get_model_stats(
        self,
        model: str | None = None,
        host_name: str | None = None,
        capability: CapabilityClass | str | None = None,
        source: str | None = "all",
    ) -> list[ModelStats]:
        """Get aggregated stats, optionally filtered to a single model."""
        grouped: dict[str, list[ModelRecord]] = {}
        for record in self._iter_filtered_records(
            model=model,
            host_name=host_name,
            capability=capability,
            source=source,
        ):
            grouped.setdefault(record.model, []).append(record)

        stats: list[ModelStats] = []
        for model_name, records in sorted(grouped.items()):
            stats.append(self._build_model_stats(model_name, records))
        return stats

    def get_capability_stats(
        self,
        capability: CapabilityClass | str | None = None,
        host_name: str | None = None,
        model: str | None = None,
        source: str | None = "all",
    ) -> dict[str, Any]:
        """Get performance breakdown by capability class."""
        grouped: dict[str, list[ModelRecord]] = {}
        for record in self._iter_filtered_records(
            model=model,
            host_name=host_name,
            capability=capability,
            source=source,
        ):
            grouped.setdefault(record.capability_class, []).append(record)

        result: dict[str, Any] = {}
        for cap_name, records in sorted(grouped.items()):
            models: dict[str, dict[str, Any]] = {}
            hosts = Counter(record.host_name for record in records)
            for r in records:
                entry = models.setdefault(r.model, {"tasks": 0, "successes": 0, "total_ms": 0.0})
                entry["tasks"] += 1
                if r.success:
                    entry["successes"] += 1
                entry["total_ms"] += r.duration_ms

            result[cap_name] = {
                "total_tasks": len(records),
                "success_rate": sum(1 for r in records if r.success) / len(records) if records else 0.0,
                "hosts": dict(hosts),
                "models": {
                    m: {
                        "tasks": d["tasks"],
                        "success_rate": d["successes"] / d["tasks"] if d["tasks"] else 0.0,
                        "avg_duration_ms": round(d["total_ms"] / d["tasks"], 1) if d["tasks"] else 0.0,
                    }
                    for m, d in models.items()
                },
            }
        return result

    def get_host_stats(
        self,
        model: str | None = None,
        capability: CapabilityClass | str | None = None,
        source: str | None = "all",
    ) -> dict[str, Any]:
        """Get performance breakdown by host."""
        grouped: dict[str, list[ModelRecord]] = {}
        for record in self._iter_filtered_records(
            model=model,
            capability=capability,
            source=source,
        ):
            grouped.setdefault(record.host_name, []).append(record)

        result: dict[str, Any] = {}
        for host, records in sorted(grouped.items()):
            durations = [record.duration_ms for record in records]
            result[host] = {
                "total_tasks": len(records),
                "success_rate": sum(1 for record in records if record.success) / len(records) if records else 0.0,
                "avg_duration_ms": round(sum(durations) / len(records), 1) if records else 0.0,
                "models_used": sorted({record.model for record in records}),
                "sources": dict(Counter(record.source for record in records)),
            }
        return result

    def get_ranked_models(
        self,
        limit: int = 3,
        order: str = "desc",
        host_name: str | None = None,
        capability: CapabilityClass | str | None = None,
        source: str | None = "all",
    ) -> list[dict[str, Any]]:
        """Get top or bottom performers across the filtered model set."""
        if limit <= 0:
            return []

        stats = [
            stat for stat in self.get_model_stats(
                host_name=host_name,
                capability=capability,
                source=source,
            )
            if stat.model != "unknown"
        ]
        reverse = order != "asc"
        ranked = sorted(
            stats,
            key=lambda stat: (
                self._routing_score(stat),
                stat.success_rate,
                -stat.avg_duration_ms,
                stat.total_tasks,
            ),
            reverse=reverse,
        )
        return [
            {
                **stat.to_dict(),
                "score": round(self._routing_score(stat), 3),
            }
            for stat in ranked[:limit]
        ]

    def get_performance_advisory(
        self,
        host_name: str | None = None,
        capability: CapabilityClass | str | None = None,
        source: str | None = "runtime",
    ) -> list[str]:
        """Generate advisory messages based on tracked performance data."""
        stats = self.get_model_stats(
            host_name=host_name,
            capability=capability,
            source=source,
        )
        if not stats:
            return []

        advisory: list[str] = []

        for s in stats:
            if s.model == "unknown":
                continue
            if s.total_tasks >= 5 and s.success_rate < 0.7:
                advisory.append(
                    f"Model {s.model} has a low success rate ({s.success_rate:.0%}) "
                    f"across {s.total_tasks} tracked tasks."
                )
            if s.total_tasks >= 5 and s.avg_duration_ms > 5000:
                advisory.append(
                    f"Model {s.model} averages {s.avg_duration_ms:.0f}ms per task — "
                    "consider a faster model for latency-sensitive work."
                )

        return advisory

    def select_model_for_capability(
        self,
        capability: CapabilityClass | str,
        available_models: list[str],
        default_model: str | None,
        host_name: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Select a better-performing model for a capability when evidence is strong enough."""
        self._ensure_loaded()
        if not default_model:
            return default_model, None

        capability_value = capability.value if isinstance(capability, CapabilityClass) else str(capability)
        candidate_stats = self._get_routing_candidate_stats(
            capability_value,
            available_models,
            host_name=host_name,
            source="runtime",
        )
        if default_model not in candidate_stats and host_name:
            candidate_stats = self._get_routing_candidate_stats(
                capability_value,
                available_models,
                host_name=None,
                source="runtime",
            )
        if default_model not in candidate_stats:
            return default_model, None

        default_stats = candidate_stats[default_model]
        best_model = max(candidate_stats, key=lambda model: self._routing_score(candidate_stats[model]))
        best_stats = candidate_stats[best_model]
        if best_model == default_model:
            return default_model, None

        default_score = self._routing_score(default_stats)
        best_score = self._routing_score(best_stats)
        default_is_underperforming = (
            default_stats.total_tasks >= self.MIN_ROUTING_SAMPLES
            and (
                default_stats.success_rate < self.LOW_SUCCESS_THRESHOLD
                or default_stats.avg_duration_ms > self.SLOW_MODEL_THRESHOLD_MS
            )
        )
        materially_better = best_score >= default_score + 0.15

        if not (default_is_underperforming or materially_better):
            return default_model, None

        reason = (
            f"Performance-aware routing selected {best_model} over {default_model} for "
            f"{capability_value}: success {best_stats.success_rate:.0%} vs {default_stats.success_rate:.0%}, "
            f"avg latency {best_stats.avg_duration_ms:.0f}ms vs {default_stats.avg_duration_ms:.0f}ms."
        )
        return best_model, reason

    def _get_routing_candidate_stats(
        self,
        capability_value: str,
        available_models: list[str],
        host_name: str | None = None,
        source: str | None = "runtime",
    ) -> dict[str, ModelStats]:
        grouped: dict[str, list[ModelRecord]] = {}
        for record in self._iter_filtered_records(
            host_name=host_name,
            capability=capability_value,
            source=source,
        ):
            if record.model == "unknown" or record.model not in available_models:
                continue
            grouped.setdefault(record.model, []).append(record)

        candidate_stats: dict[str, ModelStats] = {}
        for model_name, records in grouped.items():
            if len(records) < self.MIN_ROUTING_SAMPLES:
                continue
            candidate_stats[model_name] = self._build_model_stats(model_name, records)
        return candidate_stats

    def _build_model_stats(self, model_name: str, records: list[ModelRecord]) -> ModelStats:
        durations = [record.duration_ms for record in records]
        successes = sum(1 for record in records if record.success)
        total = len(records)
        task_types = dict(Counter(record.task_type for record in records))
        cap_classes = dict(Counter(record.capability_class for record in records))
        hosts = dict(Counter(record.host_name for record in records))
        sources = dict(Counter(record.source for record in records))

        return ModelStats(
            model=model_name,
            total_tasks=total,
            successes=successes,
            failures=total - successes,
            success_rate=successes / total if total > 0 else 0.0,
            avg_duration_ms=sum(durations) / total if total > 0 else 0.0,
            min_duration_ms=min(durations) if durations else 0.0,
            max_duration_ms=max(durations) if durations else 0.0,
            task_types=task_types,
            capability_classes=cap_classes,
            hosts=hosts,
            sources=sources,
            last_used=max(record.timestamp for record in records),
        )

    def _routing_score(self, stats: ModelStats) -> float:
        latency_penalty = min(stats.avg_duration_ms / self.SLOW_MODEL_THRESHOLD_MS, 1.0)
        return stats.success_rate - (latency_penalty * 0.25)

    def prune(
        self,
        max_records: int | None = None,
        max_age_seconds: float | None = None,
        source: str | None = "all",
        persist: bool = True,
    ) -> int:
        """Prune old or excess records and return the number removed."""
        self._ensure_loaded()
        source_value = self._normalize_source(source)
        kept: list[ModelRecord] = []
        candidates: list[ModelRecord] = []
        for record in self._records:
            if source_value != "all" and record.source != source_value:
                kept.append(record)
            else:
                candidates.append(record)

        removed = 0
        if max_age_seconds is not None:
            cutoff = time.time() - max_age_seconds
            fresh_candidates = [record for record in candidates if record.timestamp >= cutoff]
            removed += len(candidates) - len(fresh_candidates)
            candidates = fresh_candidates

        if max_records is not None and len(candidates) > max_records:
            candidates = sorted(candidates, key=lambda record: record.timestamp, reverse=True)
            removed += len(candidates) - max_records
            candidates = candidates[:max_records]

        self._records = sorted(kept + candidates, key=lambda record: record.timestamp)
        if persist and removed:
            if self._records:
                self._persist()
            elif self.path.exists():
                self.path.unlink()
        return removed

    def clear(self, source: str | None = "all") -> int:
        """Clear tracked performance data for a source or for the whole store."""
        self._ensure_loaded()
        source_value = self._normalize_source(source)
        removed = len(self._records)
        if source_value == "all":
            self._records = []
            if self.path.exists():
                self.path.unlink()
            return removed

        retained = [record for record in self._records if record.source != source_value]
        removed = len(self._records) - len(retained)
        self._records = retained
        if self._records:
            self._persist()
        elif self.path.exists():
            self.path.unlink()
        return removed

    def summary_dict(
        self,
        model: str | None = None,
        host_name: str | None = None,
        capability: CapabilityClass | str | None = None,
        source: str | None = "all",
        top: int = 3,
        bottom: int = 3,
    ) -> dict[str, Any]:
        """Return a complete summary suitable for serialization or display."""
        filtered_records = self._iter_filtered_records(
            model=model,
            host_name=host_name,
            capability=capability,
            source=source,
        )
        normalized_source = self._normalize_source(source)
        return {
            "schema_version": self.SCHEMA_VERSION,
            "filters": {
                "model": model,
                "host": host_name,
                "capability": self._normalize_capability(capability),
                "source": normalized_source,
            },
            "total_records": len(filtered_records),
            "source_counts": dict(Counter(record.source for record in filtered_records)),
            "models": [
                stat.to_dict()
                for stat in self.get_model_stats(
                    model=model,
                    host_name=host_name,
                    capability=capability,
                    source=source,
                )
            ],
            "by_capability": self.get_capability_stats(
                capability=capability,
                host_name=host_name,
                model=model,
                source=source,
            ),
            "by_host": self.get_host_stats(
                model=model,
                capability=capability,
                source=source,
            ),
            "top_performers": self.get_ranked_models(
                limit=top,
                order="desc",
                host_name=host_name,
                capability=capability,
                source=source,
            ),
            "bottom_performers": self.get_ranked_models(
                limit=bottom,
                order="asc",
                host_name=host_name,
                capability=capability,
                source=source,
            ),
            "advisory": self.get_performance_advisory(
                host_name=host_name,
                capability=capability,
                source=source,
            ),
        }
