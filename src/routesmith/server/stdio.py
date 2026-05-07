"""MCP-compatible stdio server for routesmith tool integration."""

from __future__ import annotations

import json
import sys
from typing import Any

from routesmith import __version__
from routesmith.config import load_config
from routesmith.executor import Executor
from routesmith.hosts.detector import detect_host, get_host_capabilities
from routesmith.performance import PerformanceTracker
from routesmith.state import list_routes, get_last_route


# MCP Tool definitions
MCP_TOOLS = [
    {
        "name": "routesmith.run",
        "description": "Route and execute a prompt through the routesmith pipeline. Decomposes the prompt into capability-matched subtasks and executes them.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt to route and execute"},
                "mode": {"type": "string", "enum": ["auto", "plan", "fast"], "default": "auto"},
                "model": {"type": "string", "description": "Pin to specific model (optional)"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "routesmith.explain",
        "description": "Explain the route plan for a prompt without executing. Shows how the prompt would be decomposed and routed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The prompt to plan for"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "routesmith.detect_host",
        "description": "Detect the current host IDE/agent environment.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "routesmith.capabilities",
        "description": "Get the capabilities of the detected host environment.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "routesmith.history",
        "description": "List recent route execution history.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "description": "Max routes to return"},
            },
        },
    },
    {
        "name": "routesmith.performance",
        "description": "Return structured model performance summaries with filters and ranked performers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Filter by model name"},
                "host": {"type": "string", "description": "Filter by host name"},
                "capability": {"type": "string", "description": "Filter by capability class"},
                "source": {"type": "string", "enum": ["runtime", "synthetic", "all"], "default": "runtime"},
                "top": {"type": "integer", "default": 3, "description": "Top performers to return"},
                "bottom": {"type": "integer", "default": 3, "description": "Bottom performers to return"},
            },
        },
    },
]


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle a JSON-RPC 2.0 request (MCP protocol)."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    config = load_config()

    try:
        # MCP lifecycle methods
        if method == "initialize":
            return _success(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "routesmith", "version": __version__},
            })

        elif method == "notifications/initialized":
            return _success(req_id, None)

        elif method == "tools/list":
            return _success(req_id, {"tools": MCP_TOOLS})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            return _handle_tool_call(req_id, tool_name, arguments, config)

        # Legacy direct methods (backward compatible)
        elif method == "run":
            executor = Executor(config=config)
            result = executor.run(
                prompt=params.get("prompt", ""),
                mode=params.get("mode", "auto"),
                model=params.get("model"),
            )
            return _success(req_id, result.model_dump())

        elif method == "explain":
            executor = Executor(config=config)
            plan = executor.explain(prompt=params.get("prompt", ""))
            return _success(req_id, plan.model_dump())

        elif method == "detect_host":
            detection = detect_host(config)
            return _success(req_id, detection.model_dump())

        elif method == "capabilities":
            caps = get_host_capabilities(config)
            return _success(req_id, caps.model_dump())

        elif method == "performance":
            tracker = _build_performance_tracker(config)
            summary = tracker.summary_dict(
                model=params.get("model"),
                host_name=params.get("host"),
                capability=params.get("capability"),
                source=params.get("source", "runtime"),
                top=params.get("top", 3),
                bottom=params.get("bottom", 3),
            )
            return _success(req_id, summary)

        elif method == "ping":
            return _success(req_id, {"status": "ok", "version": __version__})

        else:
            return _error(req_id, -32601, f"Unknown method: {method}")

    except Exception as e:
        return _error(req_id, -32000, str(e))


def _handle_tool_call(
    req_id: Any, tool_name: str, arguments: dict[str, Any], config: Any,
) -> dict[str, Any]:
    """Handle an MCP tools/call request."""
    if tool_name == "routesmith.run":
        executor = Executor(config=config)
        result = executor.run(
            prompt=arguments.get("prompt", ""),
            mode=arguments.get("mode", "auto"),
            model=arguments.get("model"),
        )
        return _success(req_id, {
            "content": [{"type": "text", "text": json.dumps(result.model_dump(), default=str)}],
        })

    elif tool_name == "routesmith.explain":
        executor = Executor(config=config)
        plan = executor.explain(prompt=arguments.get("prompt", ""))
        return _success(req_id, {
            "content": [{"type": "text", "text": json.dumps(plan.model_dump(), default=str)}],
        })

    elif tool_name == "routesmith.detect_host":
        detection = detect_host(config)
        return _success(req_id, {
            "content": [{"type": "text", "text": json.dumps(detection.model_dump())}],
        })

    elif tool_name == "routesmith.capabilities":
        caps = get_host_capabilities(config)
        return _success(req_id, {
            "content": [{"type": "text", "text": json.dumps(caps.model_dump())}],
        })

    elif tool_name == "routesmith.history":
        limit = arguments.get("limit", 10)
        routes = list_routes()[:limit]
        return _success(req_id, {
            "content": [{"type": "text", "text": json.dumps(routes, default=str)}],
        })

    elif tool_name == "routesmith.performance":
        tracker = _build_performance_tracker(config)
        summary = tracker.summary_dict(
            model=arguments.get("model"),
            host_name=arguments.get("host"),
            capability=arguments.get("capability"),
            source=arguments.get("source", "runtime"),
            top=arguments.get("top", 3),
            bottom=arguments.get("bottom", 3),
        )
        return _success(req_id, {
            "content": [{"type": "text", "text": json.dumps(summary, default=str)}],
        })

    else:
        return _error(req_id, -32602, f"Unknown tool: {tool_name}")


def _build_performance_tracker(config: Any) -> PerformanceTracker:
    max_age_seconds = None
    if getattr(config, "performance_max_age_days", None) is not None:
        max_age_seconds = config.performance_max_age_days * 86400
    return PerformanceTracker(
        path=getattr(config, "performance_store_file", PerformanceTracker.DEFAULT_PATH),
        max_records=getattr(config, "performance_max_records", PerformanceTracker.MAX_RECORDS),
        max_age_seconds=max_age_seconds,
    )


def _success(req_id: Any, result: Any) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 success response."""
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def run_stdio_server() -> None:
    """Run the MCP stdio server loop.

    Reads JSON-RPC 2.0 requests from stdin (one per line),
    writes JSON-RPC 2.0 responses to stdout.
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, -32700, "Parse error")
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
