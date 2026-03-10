"""ComputerToolProvider — decoupled tool injection for computer-use runtimes.

Encapsulates all sandbox / local tool injection logic previously hardcoded in
``astr_main_agent.py``.  The main agent now calls
``provider.get_tools(ctx)`` / ``provider.get_system_prompt_addon(ctx)``
without knowing about specific tool classes.
"""

from __future__ import annotations

import os
import platform

from astrbot.api import logger
from astrbot.core.agent.tool import FunctionTool
from astrbot.core.tool_provider import ToolProviderContext


# ---------------------------------------------------------------------------
# Lazy tool singletons — created once on first use, cached at module level.
# This mirrors the previous behaviour in astr_main_agent_resources.py
# but keeps everything co-located with the provider.
# ---------------------------------------------------------------------------

_SANDBOX_TOOLS_CACHE: list[FunctionTool] | None = None
_LOCAL_TOOLS_CACHE: list[FunctionTool] | None = None
_NEO_TOOLS_CACHE: list[FunctionTool] | None = None
_BROWSER_TOOLS_CACHE: list[FunctionTool] | None = None


def _get_sandbox_base_tools() -> list[FunctionTool]:
    global _SANDBOX_TOOLS_CACHE
    if _SANDBOX_TOOLS_CACHE is None:
        from astrbot.core.computer.tools import (
            ExecuteShellTool,
            FileDownloadTool,
            FileUploadTool,
            PythonTool,
        )

        _SANDBOX_TOOLS_CACHE = [
            ExecuteShellTool(),
            PythonTool(),
            FileUploadTool(),
            FileDownloadTool(),
        ]
    return list(_SANDBOX_TOOLS_CACHE)


def _get_local_tools() -> list[FunctionTool]:
    global _LOCAL_TOOLS_CACHE
    if _LOCAL_TOOLS_CACHE is None:
        from astrbot.core.computer.tools import ExecuteShellTool, LocalPythonTool

        _LOCAL_TOOLS_CACHE = [
            ExecuteShellTool(is_local=True),
            LocalPythonTool(),
        ]
    return list(_LOCAL_TOOLS_CACHE)


def _get_neo_skill_tools() -> list[FunctionTool]:
    global _NEO_TOOLS_CACHE
    if _NEO_TOOLS_CACHE is None:
        from astrbot.core.computer.tools import (
            AnnotateExecutionTool,
            CreateSkillCandidateTool,
            CreateSkillPayloadTool,
            EvaluateSkillCandidateTool,
            GetExecutionHistoryTool,
            GetSkillPayloadTool,
            ListSkillCandidatesTool,
            ListSkillReleasesTool,
            PromoteSkillCandidateTool,
            RollbackSkillReleaseTool,
            SyncSkillReleaseTool,
        )

        _NEO_TOOLS_CACHE = [
            GetExecutionHistoryTool(),
            AnnotateExecutionTool(),
            CreateSkillPayloadTool(),
            GetSkillPayloadTool(),
            CreateSkillCandidateTool(),
            ListSkillCandidatesTool(),
            EvaluateSkillCandidateTool(),
            PromoteSkillCandidateTool(),
            ListSkillReleasesTool(),
            RollbackSkillReleaseTool(),
            SyncSkillReleaseTool(),
        ]
    return list(_NEO_TOOLS_CACHE)


def _get_browser_tools() -> list[FunctionTool]:
    global _BROWSER_TOOLS_CACHE
    if _BROWSER_TOOLS_CACHE is None:
        from astrbot.core.computer.tools import (
            BrowserBatchExecTool,
            BrowserExecTool,
            RunBrowserSkillTool,
        )

        _BROWSER_TOOLS_CACHE = [
            BrowserExecTool(),
            BrowserBatchExecTool(),
            RunBrowserSkillTool(),
        ]
    return list(_BROWSER_TOOLS_CACHE)


# ---------------------------------------------------------------------------
# System-prompt constants (moved from astr_main_agent_resources.py)
# ---------------------------------------------------------------------------

SANDBOX_MODE_PROMPT = (
    "You have access to a sandboxed environment and can execute "
    "shell commands and Python code securely."
)

_NEO_PATH_RULE_PROMPT = (
    "\n[Shipyard Neo File Path Rule]\n"
    "When using sandbox filesystem tools (upload/download/read/write/list/delete), "
    "always pass paths relative to the sandbox workspace root. "
    "Example: use `baidu_homepage.png` instead of `/workspace/baidu_homepage.png`.\n"
)

_NEO_SKILL_LIFECYCLE_PROMPT = (
    "\n[Neo Skill Lifecycle Workflow]\n"
    "When user asks to create/update a reusable skill in Neo mode, use lifecycle tools instead of directly writing local skill folders.\n"
    "Preferred sequence:\n"
    "1) Use `astrbot_create_skill_payload` to store canonical payload content and get `payload_ref`.\n"
    "2) Use `astrbot_create_skill_candidate` with `skill_key` + `source_execution_ids` (and optional `payload_ref`) to create a candidate.\n"
    "3) Use `astrbot_promote_skill_candidate` to release: `stage=canary` for trial; `stage=stable` for production.\n"
    "For stable release, set `sync_to_local=true` to sync `payload.skill_markdown` into local `SKILL.md`.\n"
    "Do not treat ad-hoc generated files as reusable Neo skills unless they are captured via payload/candidate/release.\n"
    "To update an existing skill, create a new payload/candidate and promote a new release version; avoid patching old local folders directly.\n"
)


def _build_local_mode_prompt() -> str:
    system_name = platform.system() or "Unknown"
    shell_hint = (
        "The runtime shell is Windows Command Prompt (cmd.exe). "
        "Use cmd-compatible commands and do not assume Unix commands like cat/ls/grep are available."
        if system_name.lower() == "windows"
        else "The runtime shell is Unix-like. Use POSIX-compatible shell commands."
    )
    return (
        "You have access to the host local environment and can execute shell commands and Python code. "
        f"Current operating system: {system_name}. "
        f"{shell_hint}"
    )


# ---------------------------------------------------------------------------
# ComputerToolProvider
# ---------------------------------------------------------------------------


class ComputerToolProvider:
    """Provides computer-use tools (local / sandbox) based on session context."""

    def get_tools(self, ctx: ToolProviderContext) -> list[FunctionTool]:
        runtime = ctx.computer_use_runtime
        if runtime == "none":
            return []

        if runtime == "local":
            return _get_local_tools()

        if runtime == "sandbox":
            return self._sandbox_tools(ctx)

        logger.warning("[ComputerToolProvider] Unknown runtime: %s", runtime)
        return []

    def get_system_prompt_addon(self, ctx: ToolProviderContext) -> str:
        runtime = ctx.computer_use_runtime
        if runtime == "none":
            return ""

        if runtime == "local":
            return f"\n{_build_local_mode_prompt()}\n"

        if runtime == "sandbox":
            return self._sandbox_prompt_addon(ctx)

        return ""

    # -- sandbox helpers ----------------------------------------------------

    def _sandbox_tools(self, ctx: ToolProviderContext) -> list[FunctionTool]:
        """Collect tools for sandbox mode."""
        booter_type = ctx.sandbox_cfg.get("booter", "shipyard_neo")

        # Validate shipyard (non-neo) config
        if booter_type == "shipyard":
            ep = ctx.sandbox_cfg.get("shipyard_endpoint", "")
            at = ctx.sandbox_cfg.get("shipyard_access_token", "")
            if not ep or not at:
                logger.error("Shipyard sandbox configuration is incomplete.")
                return []
            os.environ["SHIPYARD_ENDPOINT"] = ep
            os.environ["SHIPYARD_ACCESS_TOKEN"] = at

        tools = _get_sandbox_base_tools()

        if booter_type == "shipyard_neo":
            sandbox_capabilities = self._get_sandbox_capabilities(ctx.session_id)

            # Browser tools if capability present (or unknown)
            if sandbox_capabilities is None or "browser" in sandbox_capabilities:
                tools.extend(_get_browser_tools())

            # Neo skill lifecycle tools
            tools.extend(_get_neo_skill_tools())

        return tools

    def _sandbox_prompt_addon(self, ctx: ToolProviderContext) -> str:
        """Build system-prompt addon for sandbox mode."""
        parts: list[str] = []

        booter_type = ctx.sandbox_cfg.get("booter", "shipyard_neo")
        if booter_type == "shipyard_neo":
            parts.append(_NEO_PATH_RULE_PROMPT)
            parts.append(_NEO_SKILL_LIFECYCLE_PROMPT)

        parts.append(f"\n{SANDBOX_MODE_PROMPT}\n")
        return "".join(parts)

    @staticmethod
    def _get_sandbox_capabilities(session_id: str) -> tuple[str, ...] | None:
        """Query capabilities for an already-booted sandbox session."""
        from astrbot.core.computer.computer_client import session_booter

        existing_booter = session_booter.get(session_id)
        if existing_booter is not None:
            return getattr(existing_booter, "capabilities", None)
        return None
