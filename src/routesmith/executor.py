"""Executor - orchestrates the full routesmith pipeline."""

from __future__ import annotations

import time

from routesmith.advisory import generate_advisory
from routesmith.config import load_config
from routesmith.hosts.detector import detect_host, get_host_adapter
from routesmith.metrics import RouteMetrics, compute_metrics
from routesmith.performance import PerformanceTracker
from routesmith.planner import Planner
from routesmith.review import review_plan, review_results
from routesmith.router import Router
from routesmith.state import save_route
from routesmith.types import (
    HostCapabilities,
    RoutePlan,
    RunResult,
    SkillConfig,
    TaskResult,
)


class Executor:
    """Main orchestration engine for routesmith."""

    def __init__(self, config: SkillConfig | None = None) -> None:
        self.config = config or load_config()
        self.planner = Planner()
        max_age_seconds = None
        if self.config.performance_max_age_days is not None:
            max_age_seconds = self.config.performance_max_age_days * 86400
        self.performance_tracker = PerformanceTracker(
            path=self.config.performance_store_file,
            max_records=self.config.performance_max_records,
            max_age_seconds=max_age_seconds,
        )

    def explain(self, prompt: str) -> RoutePlan:
        """Explain the route plan without executing."""
        detection = detect_host(self.config)
        adapter = get_host_adapter(self.config)
        capabilities = adapter.get_capabilities()

        plan = self.planner.plan(prompt, host_name=detection.host_name)

        router = Router(adapter, config=self.config, performance_tracker=self.performance_tracker)
        plan = router.resolve_plan(plan)

        # Generate advisory
        advisory = generate_advisory(
            plan,
            capabilities,
            max_spawn_depth=self.config.max_spawn_depth,
        )
        plan.advisory.extend(advisory)

        # Review
        warnings = review_plan(plan)
        plan.advisory.extend(warnings)

        return plan

    def run(
        self,
        prompt: str,
        mode: str = "auto",
        model: str | None = None,
    ) -> RunResult:
        """Execute a prompt through the full pipeline."""
        t_start = time.perf_counter()

        detection = detect_host(self.config)
        adapter = get_host_adapter(self.config)
        capabilities = adapter.get_capabilities()

        # Create plan (timed)
        t_plan_start = time.perf_counter()
        plan = self.planner.plan(prompt, host_name=detection.host_name)
        plan.mode = mode
        t_plan_end = time.perf_counter()

        # Route (timed)
        t_route_start = time.perf_counter()
        router = Router(adapter, config=self.config, performance_tracker=self.performance_tracker)
        plan = router.resolve_plan(plan)

        # Handle pinned model
        pinned_model: str | None = None
        if model:
            pinned_model = model
            for task in plan.tasks:
                task.suggested_model = model

        # Generate advisory
        advisory = generate_advisory(
            plan,
            capabilities,
            pinned_model=pinned_model,
            max_spawn_depth=self.config.max_spawn_depth,
        )
        plan.advisory.extend(advisory)
        t_route_end = time.perf_counter()

        # Execute tasks (timed)
        t_exec_start = time.perf_counter()
        task_results = self._execute_tasks(plan, adapter, capabilities)
        t_exec_end = time.perf_counter()

        # Review results
        result_warnings = review_results(task_results)

        # Build route summary
        route_summary = self._build_route_summary(plan, capabilities, task_results)

        t_end = time.perf_counter()

        # Compute metrics
        timing = {
            "total": (t_end - t_start) * 1000,
            "planning": (t_plan_end - t_plan_start) * 1000,
            "routing": (t_route_end - t_route_start) * 1000,
            "execution": (t_exec_end - t_exec_start) * 1000,
        }
        metrics = compute_metrics(plan, task_results, capabilities, timing)

        result = RunResult(
            final_output=self._build_final_output(task_results),
            route_summary=route_summary,
            advisory=plan.advisory + result_warnings,
            tasks=task_results,
            raw_plan=plan,
            host=detection.host_name,
            metrics=metrics.model_dump(),
        )

        # Record performance data
        self.performance_tracker.record_run(
            plan,
            task_results,
            host_name=detection.host_name,
            source="runtime",
        )

        # Inject performance advisory
        perf_advisory = self.performance_tracker.get_performance_advisory()
        if perf_advisory:
            result.advisory.extend(perf_advisory)

        # Persist route if configured
        if self.config.save_routes:
            save_route(plan, task_results, metrics, self.config.routes_dir)

        return result

    def _execute_tasks(
        self,
        plan: RoutePlan,
        adapter,
        capabilities: HostCapabilities,
    ) -> list[TaskResult]:
        """Execute tasks in dependency order with real model switching."""
        results: list[TaskResult] = []
        completed_ids: set[str] = set()

        # Execute in plan order (already sorted by priority)
        for task in plan.tasks:
            t_task_start = time.perf_counter()

            # Check dependencies are met
            unmet = [d for d in task.dependencies if d not in completed_ids]
            if unmet:
                results.append(TaskResult(
                    task_id=task.id,
                    model_used=None,
                    output_text=f"[{task.type.value}] Skipped - unmet dependencies: {unmet}",
                    success=False,
                    warnings=[f"Dependencies not met: {unmet}"],
                    duration_ms=0.0,
                ))
                continue

            # Get strategy from adapter
            strategy = adapter.apply_prompt_strategy(task)
            model_used: str | None = None
            warnings: list[str] = []

            if capabilities.supports_dynamic_switch and task.suggested_model:
                # Attempt real model switch
                success = adapter.set_model(task.suggested_model)
                if success:
                    model_used = task.suggested_model
                else:
                    warnings.append(
                        f"Model switch to {task.suggested_model} failed. "
                        f"Using current model with prompt strategy."
                    )
                    model_used = capabilities.current_model
                    warnings.append("prompt strategy applied")
            else:
                model_used = capabilities.current_model
                if not capabilities.supports_dynamic_switch:
                    warnings.append("Model switching not available. Using prompt strategy.")
                    warnings.append("prompt strategy applied")

            t_task_end = time.perf_counter()
            duration_ms = (t_task_end - t_task_start) * 1000

            result = TaskResult(
                task_id=task.id,
                model_used=model_used,
                output_text=(
                    f"[{task.type.value}] {task.title} - "
                    f"routed to {model_used or 'default'} via {strategy['strategy']}"
                ),
                success=True,
                warnings=warnings,
                duration_ms=duration_ms,
            )
            results.append(result)
            completed_ids.add(task.id)

        return results

    def _build_route_summary(
        self,
        plan: RoutePlan,
        capabilities: HostCapabilities,
        results: list[TaskResult],
    ) -> str:
        """Build a human-readable route summary."""
        lines: list[str] = []
        lines.append(f"Host: {plan.host} (family: {capabilities.model_family})")
        lines.append(f"Mode: {plan.mode}")
        lines.append(f"Tasks: {len(plan.tasks)}")
        lines.append(f"Dynamic switching: {'yes' if capabilities.supports_dynamic_switch else 'no'}")
        lines.append("")

        for task in plan.tasks:
            model_info = task.suggested_model or "prompt strategy"
            conf = f" [{task.confidence:.0%}]" if task.confidence < 1.0 else ""
            lines.append(f"  [{task.type.value}] {task.title} -> {model_info}{conf}")

        succeeded = sum(1 for r in results if r.success)
        lines.append("")
        lines.append(f"Results: {succeeded}/{len(results)} succeeded")

        return "\n".join(lines)

    def _build_final_output(self, results: list[TaskResult]) -> str:
        """Build combined final output from task results."""
        outputs = [r.output_text for r in results if r.output_text]
        return "\n".join(outputs)
