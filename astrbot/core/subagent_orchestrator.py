from __future__ import annotations

import copy
import json
import re
from typing import TYPE_CHECKING, Any

from astrbot import logger
from astrbot.core.agent.agent import Agent
from astrbot.core.agent.handoff import HandoffTool
from astrbot.core.provider.func_tool_manager import FunctionToolManager

if TYPE_CHECKING:
    from astrbot.core.persona_mgr import PersonaManager

# A subagent name becomes part of the `transfer_to_<name>` tool name, which most
# providers restrict to `[a-zA-Z0-9_-]`. Keep it stricter and aligned with the
# pattern the dashboard enforces client-side.
SUBAGENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class SubAgentOrchestrator:
    """Builds subagent handoff tools from config.

    This is intentionally lightweight: it does not execute agents itself, and it
    does not register the handoff tools into the global
    :class:`FunctionToolManager`. Handoff tools are attached per-request to the
    main agent's toolset (see ``astr_main_agent``), and executed by
    ``HandoffTool`` handling inside ``FunctionToolExecutor``.
    """

    def __init__(
        self, tool_mgr: FunctionToolManager, persona_mgr: PersonaManager
    ) -> None:
        self._tool_mgr = tool_mgr
        self._persona_mgr = persona_mgr
        self.handoffs: list[HandoffTool] = []
        # Cache keyed by a stable fingerprint of the orchestrator config, so
        # per-session config profiles can resolve their own handoff set without
        # rebuilding Agent objects on every request.
        self._cache: dict[str, list[HandoffTool]] = {}

    @staticmethod
    def _fingerprint(cfg: dict[str, Any] | None) -> str:
        try:
            return json.dumps(
                cfg or {}, sort_keys=True, ensure_ascii=False, default=str
            )
        except (TypeError, ValueError):
            return repr(cfg)

    def build_handoffs(self, cfg: dict[str, Any] | None) -> list[HandoffTool]:
        """Build the handoff tools described by ``cfg`` without caching."""
        from astrbot.core.astr_agent_context import AstrAgentContext

        agents = (cfg or {}).get("agents", [])
        if not isinstance(agents, list):
            logger.warning("subagent_orchestrator.agents must be a list")
            return []

        handoffs: list[HandoffTool] = []
        seen_names: set[str] = set()
        for item in agents:
            if not isinstance(item, dict):
                continue
            if not item.get("enabled", True):
                continue

            name = str(item.get("name", "")).strip()
            if not name:
                continue
            if not SUBAGENT_NAME_PATTERN.match(name):
                logger.warning(
                    "Skipping subagent with invalid name %r: names must match %s.",
                    name,
                    SUBAGENT_NAME_PATTERN.pattern,
                )
                continue
            if name in seen_names:
                logger.warning(
                    "Skipping duplicate subagent name %r; only the first "
                    "definition is used.",
                    name,
                )
                continue
            seen_names.add(name)

            persona_id = item.get("persona_id")
            if persona_id is not None:
                persona_id = str(persona_id).strip() or None
            persona_data = self._persona_mgr.get_persona_v3_by_id(persona_id)
            if persona_id and persona_data is None:
                logger.warning(
                    "SubAgent persona %s not found, fallback to inline prompt.",
                    persona_id,
                )

            instructions = str(item.get("system_prompt", "")).strip()
            public_description = str(item.get("public_description", "")).strip()
            provider_id = item.get("provider_id")
            if provider_id is not None:
                provider_id = str(provider_id).strip() or None
            tools = item.get("tools", [])
            begin_dialogs = None

            if persona_data:
                prompt = str(persona_data.get("prompt", "")).strip()
                if prompt:
                    instructions = prompt
                begin_dialogs = copy.deepcopy(
                    persona_data.get("_begin_dialogs_processed")
                )
                tools = persona_data.get("tools")
                if public_description == "" and prompt:
                    public_description = prompt[:120]
            if tools is None:
                tools = None
            elif not isinstance(tools, list):
                tools = []
            else:
                tools = [str(t).strip() for t in tools if str(t).strip()]

            agent = Agent[AstrAgentContext](
                name=name,
                instructions=instructions,
                tools=tools,  # type: ignore
            )
            agent.begin_dialogs = begin_dialogs
            # The tool description should be a short description for the main LLM,
            # while the subagent system prompt can be longer/more specific.
            handoff = HandoffTool(
                agent=agent,
                tool_description=public_description or None,
            )

            # Optional per-subagent chat provider override.
            handoff.provider_id = provider_id

            handoffs.append(handoff)

        return handoffs

    def get_handoffs(self, cfg: dict[str, Any] | None) -> list[HandoffTool]:
        """Return the handoff tools for ``cfg``, building and caching on miss.

        Used by the main agent so that a session-scoped config profile resolves
        the subagents it actually declares, instead of the global set.
        """
        key = self._fingerprint(cfg)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        handoffs = self.build_handoffs(cfg)
        # Bound the cache: config profiles are few, but a pathological caller
        # should not grow this without limit.
        if len(self._cache) >= 32:
            self._cache.clear()
        self._cache[key] = handoffs
        return handoffs

    async def reload_from_config(self, cfg: dict[str, Any]) -> None:
        self._cache.clear()
        handoffs = self.build_handoffs(cfg)

        for handoff in handoffs:
            logger.info(f"Registered subagent handoff tool: {handoff.name}")

        self.handoffs = handoffs
        self._cache[self._fingerprint(cfg)] = handoffs
