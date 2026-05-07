"""Tests for the performance tracking module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from routesmith.performance import PerformanceTracker
from routesmith.server.stdio import handle_request
from routesmith.types import CapabilityClass, RoutePlan, SkillConfig, TaskNode, TaskResult, TaskType


def _make_plan(tasks: list[TaskNode]) -> RoutePlan:
    return RoutePlan(original_prompt="test", tasks=tasks)


def _make_task(task_id: str, task_type: TaskType, capability: CapabilityClass) -> TaskNode:
    return TaskNode(
        id=task_id,
        type=task_type,
        title=f"{task_type.value} task",
        preferred_capability_class=capability,
        suggested_model="claude-sonnet-4-6",
    )


def _make_result(task_id: str, model: str = "claude-sonnet-4-6", success: bool = True, duration_ms: float = 100.0) -> TaskResult:
    return TaskResult(
        task_id=task_id,
        model_used=model,
        success=success,
        duration_ms=duration_ms,
    )


class TestPerformanceTracker:
    """Test the PerformanceTracker class."""

    def test_records_run_and_produces_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.PLANNING, CapabilityClass.DEEP_REASONING),
                _make_task("t2", TaskType.CODING, CapabilityClass.CODING),
            ])
            results = [
                _make_result("t1", "claude-opus-4", duration_ms=200.0),
                _make_result("t2", "claude-sonnet-4-6", duration_ms=80.0),
            ]

            tracker.record_run(plan, results)

            stats = tracker.get_model_stats()
            assert len(stats) == 2
            opus_stats = next(s for s in stats if s.model == "claude-opus-4")
            assert opus_stats.total_tasks == 1
            assert opus_stats.success_rate == 1.0
            assert opus_stats.avg_duration_ms == 200.0

    def test_persists_and_reloads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "perf.json"
            tracker = PerformanceTracker(path)
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])
            results = [_make_result("t1")]
            tracker.record_run(plan, results)

            # Create a new tracker instance pointing to same file
            tracker2 = PerformanceTracker(path)
            stats = tracker2.get_model_stats()
            assert len(stats) == 1
            assert stats[0].total_tasks == 1

    def test_multiple_runs_accumulate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])

            tracker.record_run(plan, [_make_result("t1", duration_ms=100)])
            tracker.record_run(plan, [_make_result("t1", duration_ms=200)])
            tracker.record_run(plan, [_make_result("t1", duration_ms=300)])

            stats = tracker.get_model_stats()
            assert stats[0].total_tasks == 3
            assert stats[0].avg_duration_ms == 200.0

    def test_failure_tracking(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.TESTING, CapabilityClass.BALANCED),
            ])
            results = [_make_result("t1", success=False)]
            tracker.record_run(plan, results)

            stats = tracker.get_model_stats()
            assert stats[0].failures == 1
            assert stats[0].success_rate == 0.0

    def test_filter_by_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.PLANNING, CapabilityClass.DEEP_REASONING),
                _make_task("t2", TaskType.CODING, CapabilityClass.CODING),
            ])
            results = [
                _make_result("t1", "claude-opus-4"),
                _make_result("t2", "claude-sonnet-4-6"),
            ]
            tracker.record_run(plan, results)

            opus_stats = tracker.get_model_stats(model="claude-opus-4")
            assert len(opus_stats) == 1
            assert opus_stats[0].model == "claude-opus-4"

    def test_filter_by_host_and_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])

            tracker.record_run(
                plan,
                [_make_result("t1", "claude-sonnet-4-6")],
                host_name="claude_code",
                source="runtime",
            )
            tracker.record_run(
                plan,
                [_make_result("t1", "claude-sonnet-4-6")],
                host_name="codex",
                source="synthetic",
            )

            runtime_stats = tracker.get_model_stats(host_name="claude_code", source="runtime")
            synthetic_stats = tracker.get_model_stats(host_name="codex", source="synthetic")

            assert len(runtime_stats) == 1
            assert runtime_stats[0].hosts == {"claude_code": 1}
            assert len(synthetic_stats) == 1
            assert synthetic_stats[0].sources == {"synthetic": 1}

    def test_capability_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.PLANNING, CapabilityClass.DEEP_REASONING),
                _make_task("t2", TaskType.CODING, CapabilityClass.CODING),
            ])
            results = [
                _make_result("t1", "claude-opus-4"),
                _make_result("t2", "claude-sonnet-4-6"),
            ]
            tracker.record_run(plan, results)

            cap_stats = tracker.get_capability_stats(CapabilityClass.DEEP_REASONING)
            assert "deep_reasoning" in cap_stats
            assert cap_stats["deep_reasoning"]["total_tasks"] == 1

    def test_performance_advisory_low_success_rate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])

            # Record 5 runs, 3 failures
            for i in range(5):
                tracker.record_run(plan, [_make_result("t1", success=(i < 2))])

            advisory = tracker.get_performance_advisory()
            assert any("low success rate" in msg for msg in advisory)

    def test_performance_advisory_slow_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])

            for _ in range(5):
                tracker.record_run(plan, [_make_result("t1", duration_ms=6000)])

            advisory = tracker.get_performance_advisory()
            assert any("averages" in msg for msg in advisory)

    def test_clear_removes_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "perf.json"
            tracker = PerformanceTracker(path)
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])
            tracker.record_run(plan, [_make_result("t1")])

            tracker.clear()
            assert tracker.get_model_stats() == []
            assert not path.exists()

    def test_rolling_window_trims_old_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            tracker.max_records = 10  # Small window for testing
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])

            for _ in range(15):
                tracker.record_run(plan, [_make_result("t1")])

            stats = tracker.get_model_stats()
            assert stats[0].total_tasks == 10

    def test_corrupted_file_starts_fresh(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "perf.json"
            path.write_text("not valid json {{{")

            tracker = PerformanceTracker(path)
            assert tracker.get_model_stats() == []

    def test_migrates_legacy_v1_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "perf.json"
            path.write_text(json.dumps({
                "version": 1,
                "records": [
                    {
                        "model": "claude-sonnet-4-6",
                        "task_type": "coding",
                        "capability_class": "coding",
                        "success": True,
                        "duration_ms": 120.0,
                        "timestamp": 1.0,
                    }
                ],
            }))

            tracker = PerformanceTracker(path)
            summary = tracker.summary_dict(source="all")

            assert summary["schema_version"] == 2
            assert summary["by_host"]["unknown"]["total_tasks"] == 1
            assert summary["source_counts"]["runtime"] == 1

    def test_prune_controls_remove_old_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "perf.json"
            now = 5000.0
            path.write_text(json.dumps({
                "schema_version": 2,
                "records": [
                    {
                        "model": "claude-sonnet-4-6",
                        "task_type": "coding",
                        "capability_class": "coding",
                        "host_name": "claude_code",
                        "source": "runtime",
                        "success": True,
                        "duration_ms": 100.0,
                        "timestamp": now - 1000,
                    },
                    {
                        "model": "claude-haiku-4-5",
                        "task_type": "coding",
                        "capability_class": "coding",
                        "host_name": "claude_code",
                        "source": "runtime",
                        "success": True,
                        "duration_ms": 80.0,
                        "timestamp": now,
                    },
                ],
            }))

            tracker = PerformanceTracker(path)
            with patch("routesmith.performance.time.time", return_value=now):
                removed = tracker.prune(max_age_seconds=60)

            assert removed == 1
            assert len(tracker.get_model_stats(source="all")) == 1

    def test_summary_dict_includes_rankings(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("good", TaskType.CODING, CapabilityClass.CODING),
                _make_task("bad", TaskType.CODING, CapabilityClass.CODING),
            ])

            for run_index in range(3):
                tracker.record_run(
                    plan,
                    [
                        _make_result("good", model="claude-haiku-4-5", success=True, duration_ms=100.0),
                        _make_result("bad", model="claude-sonnet-4-6", success=run_index == 0, duration_ms=6500.0),
                    ],
                    host_name="claude_code",
                    source="runtime",
                )

            summary = tracker.summary_dict(host_name="claude_code", source="runtime", top=1, bottom=1)
            assert summary["top_performers"][0]["model"] == "claude-haiku-4-5"
            assert summary["bottom_performers"][0]["model"] == "claude-sonnet-4-6"

    def test_summary_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "perf.json")
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])
            tracker.record_run(plan, [_make_result("t1")])

            summary = tracker.summary_dict()
            assert summary["total_records"] == 1
            assert len(summary["models"]) == 1
            assert "coding" in summary["by_capability"]


class TestPerformanceIntegration:
    """Test performance tracking integrated with the executor."""

    def test_executor_records_performance(self):
        import tempfile
        from routesmith.executor import Executor

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SkillConfig(forced_host="generic")
            executor = Executor(config=config)
            perf_path = Path(tmpdir) / "perf.json"
            executor.performance_tracker = PerformanceTracker(perf_path)

            executor.run("write a function and test it")

            # Generic host won't assign models, but records should still exist
            assert executor.performance_tracker._records
            summary = executor.performance_tracker.summary_dict(source="runtime")
            assert summary["by_host"]["generic"]["total_tasks"] >= 1

    def test_stdio_performance_tool_returns_exportable_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            perf_path = Path(tmpdir) / "perf.json"
            tracker = PerformanceTracker(perf_path)
            plan = _make_plan([
                _make_task("t1", TaskType.CODING, CapabilityClass.CODING),
            ])
            tracker.record_run(
                plan,
                [_make_result("t1", "claude-sonnet-4-6")],
                host_name="claude_code",
                source="runtime",
            )

            with patch(
                "routesmith.server.stdio.load_config",
                return_value=SkillConfig(performance_store_file=str(perf_path)),
            ):
                response = handle_request(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "routesmith.performance",
                            "arguments": {"host": "claude_code", "source": "runtime", "top": 1},
                        },
                    }
                )

            payload = json.loads(response["result"]["content"][0]["text"])
            assert payload["filters"]["host"] == "claude_code"
            assert payload["top_performers"]
