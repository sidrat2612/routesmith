"""Host adapters for routesmith."""

from routesmith.hosts.base import BaseHostAdapter
from routesmith.hosts.detector import detect_host, get_host_capabilities
from routesmith.hosts.aider import AiderHostAdapter
from routesmith.hosts.claude_code import ClaudeCodeHostAdapter
from routesmith.hosts.codex import CodexHostAdapter
from routesmith.hosts.copilot import CopilotHostAdapter
from routesmith.hosts.cursor import CursorHostAdapter
from routesmith.hosts.gemini_cli import GeminiCLIHostAdapter
from routesmith.hosts.generic import GenericHostAdapter

__all__ = [
    "BaseHostAdapter",
    "detect_host",
    "get_host_capabilities",
    "AiderHostAdapter",
    "ClaudeCodeHostAdapter",
    "CodexHostAdapter",
    "CopilotHostAdapter",
    "CursorHostAdapter",
    "GeminiCLIHostAdapter",
    "GenericHostAdapter",
]
