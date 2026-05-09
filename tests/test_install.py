"""Tests for install adapters."""

import json

from routesmith.install.aider import AiderInstaller
from routesmith.install.base import _deep_merge_dicts
from routesmith.install.claude import ClaudeInstaller
from routesmith.install.codex import CodexInstaller
from routesmith.install.copilot import CopilotInstaller
from routesmith.install.cursor import CursorInstaller
from routesmith.install.gemini import GeminiInstaller
from routesmith.types import SkillConfig


class TestClaudeInstaller:
    """Verify Claude installer output and settings merging."""

    def test_install_creates_claude_md_with_token_guidance(self, tmp_path):
        installer = ClaudeInstaller(root=tmp_path)

        result = installer.install()

        assert result.success is True
        claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "## Task Delegation" in claude_md
        assert "### Spawn rules" in claude_md
        assert "## Preferred Tools" in claude_md
        assert "## Context Management" in claude_md

        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] == "80"
        assert settings["env"]["CLAUDE_CODE_DISABLE_1M_CONTEXT"] == "1"

    def test_install_merges_existing_settings(self, tmp_path):
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(
                {
                    "model": "claude-sonnet-4-6",
                    "env": {"EXISTING": "1"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        installer = ClaudeInstaller(root=tmp_path)
        installer.install()

        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        assert settings["model"] == "claude-sonnet-4-6"
        assert settings["env"]["EXISTING"] == "1"
        assert settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] == "80"
        assert settings["env"]["CLAUDE_CODE_DISABLE_1M_CONTEXT"] == "1"

    def test_install_uses_configured_context_values(self, tmp_path):
        installer = ClaudeInstaller(
            root=tmp_path,
            config=SkillConfig(
                autocompact_threshold=70,
                context_window_limit=False,
            ),
        )

        installer.install()

        settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert settings["env"]["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] == "70"
        assert "CLAUDE_CODE_DISABLE_1M_CONTEXT" not in settings["env"]

        # CLAUDE.md should NOT mention 1M context when context_window_limit=False
        claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "1M context window" not in claude_md
        assert "70%" in claude_md

    def test_install_warns_on_corrupt_existing_json(self, tmp_path):
        settings_path = tmp_path / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("{bad json", encoding="utf-8")

        installer = ClaudeInstaller(root=tmp_path)
        result = installer.install()

        assert len(result.warnings) == 1
        assert "malformed JSON" in result.warnings[0]
        # Should still write valid settings
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "env" in settings


class TestDeepMerge:
    """Verify _deep_merge_dicts handles edge cases."""

    def test_overlay_replaces_non_dict_with_dict(self):
        base = {"key": "string_value"}
        overlay = {"key": {"nested": True}}
        result = _deep_merge_dicts(base, overlay)
        assert result["key"] == {"nested": True}

    def test_overlay_replaces_dict_with_non_dict(self):
        base = {"key": {"nested": True}}
        overlay = {"key": "string_value"}
        result = _deep_merge_dicts(base, overlay)
        assert result["key"] == "string_value"

    def test_preserves_unrelated_keys(self):
        base = {"a": 1, "b": 2}
        overlay = {"c": 3}
        result = _deep_merge_dicts(base, overlay)
        assert result == {"a": 1, "b": 2, "c": 3}


class TestOtherInstallers:
    """Verify the remaining install adapters include token-saving guidance."""

    def test_codex_installer_adds_delegation_and_context_guidance(self, tmp_path):
        installer = CodexInstaller(root=tmp_path)

        installer.install()

        content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        assert "## Task Delegation" in content
        assert "## Preferred Tools" in content
        assert "## Context Management" in content

    def test_gemini_installer_adds_delegation_and_context_guidance(self, tmp_path):
        installer = GeminiInstaller(root=tmp_path)

        installer.install()

        content = (tmp_path / "GEMINI.md").read_text(encoding="utf-8")
        assert "## Task Delegation" in content
        assert "## Preferred Tools" in content
        assert "## Context Management" in content

    def test_copilot_installer_adds_context_management(self, tmp_path):
        installer = CopilotInstaller(root=tmp_path)

        installer.install()

        content = (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        assert "## Task Delegation" in content
        assert "## Preferred Tools" in content
        assert "## Context Management" in content

    def test_cursor_installer_adds_context_management(self, tmp_path):
        installer = CursorInstaller(root=tmp_path)

        installer.install()

        content = (tmp_path / ".cursorules").read_text(encoding="utf-8")
        assert "## Task Delegation" in content
        assert "## Preferred Tools" in content
        assert "## Context Management" in content

    def test_aider_installer_writes_active_config_when_absent(self, tmp_path):
        installer = AiderInstaller(root=tmp_path)

        installer.install()

        content = (tmp_path / ".aider.conf.yml").read_text(encoding="utf-8")
        assert "max-chat-history-tokens: 4000" in content
        assert "cache-prompts: true" in content
        assert "map-tokens: 1024" in content
        # weak-model should be commented out, not hardcoded
        assert "weak-model:" not in content or content.count("# weak-model:") == content.count("weak-model:")

    def test_aider_installer_falls_back_to_sidecar_if_config_exists(self, tmp_path):
        (tmp_path / ".aider.conf.yml").write_text("model: claude-sonnet-4-6\n", encoding="utf-8")
        installer = AiderInstaller(root=tmp_path)

        result = installer.install()

        assert (tmp_path / ".aider.routesmith.yml").exists()
        assert any(".aider.routesmith.yml" in message for message in result.messages)
        # Verify sidecar content is valid
        content = (tmp_path / ".aider.routesmith.yml").read_text(encoding="utf-8")
        assert "max-chat-history-tokens: 4000" in content