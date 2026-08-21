from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest

from astrbot.core.subagent_orchestrator import SubAgentOrchestrator


def _build_cfg(agent_overrides: dict) -> dict:
    agent = {
        "name": "planner",
        "enabled": True,
        "persona_id": None,
        "system_prompt": "inline prompt",
        "public_description": "",
        "tools": ["tool_a", " ", "tool_b"],
    }
    agent.update(agent_overrides)
    return {"agents": [agent]}


@pytest.mark.asyncio
async def test_reload_from_config_default_persona_is_resolved():
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    default_persona = {
        "name": "default",
        "prompt": "You are a helpful and friendly assistant.",
        "tools": None,
        "_begin_dialogs_processed": [],
    }
    persona_mgr.get_persona_v3_by_id.return_value = deepcopy(default_persona)
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    await orchestrator.reload_from_config(_build_cfg({"persona_id": "default"}))

    assert len(orchestrator.handoffs) == 1
    handoff = orchestrator.handoffs[0]
    assert handoff.agent.instructions == default_persona["prompt"]
    assert handoff.agent.tools is None
    assert handoff.agent.begin_dialogs == default_persona["_begin_dialogs_processed"]


@pytest.mark.asyncio
async def test_reload_from_config_missing_persona_falls_back_to_inline_and_warns():
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    persona_mgr.get_persona_v3_by_id.return_value = None
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    with patch("astrbot.core.subagent_orchestrator.logger") as mock_logger:
        await orchestrator.reload_from_config(_build_cfg({"persona_id": "not_exists"}))

    assert len(orchestrator.handoffs) == 1
    handoff = orchestrator.handoffs[0]
    assert handoff.agent.instructions == "inline prompt"
    assert handoff.agent.tools == ["tool_a", "tool_b"]
    assert handoff.agent.begin_dialogs is None
    mock_logger.warning.assert_called_once_with(
        "SubAgent persona %s not found, fallback to inline prompt.",
        "not_exists",
    )


@pytest.mark.asyncio
async def test_reload_from_config_uses_processed_begin_dialogs_and_deepcopy():
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    processed_dialogs = [{"role": "user", "content": "hello", "_no_save": True}]
    persona_mgr.get_persona_v3_by_id.return_value = {
        "name": "custom",
        "prompt": "persona prompt",
        "tools": ["tool_from_persona"],
        "_begin_dialogs_processed": processed_dialogs,
    }
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    await orchestrator.reload_from_config(_build_cfg({"persona_id": "custom"}))
    processed_dialogs[0]["content"] = "mutated"

    handoff = orchestrator.handoffs[0]
    assert handoff.agent.instructions == "persona prompt"
    assert handoff.agent.tools == ["tool_from_persona"]
    assert handoff.agent.begin_dialogs[0]["content"] == "hello"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw_tools", "expected_tools"),
    [
        (None, None),
        ([], []),
        ("not-a-list", []),
    ],
)
async def test_reload_from_config_tool_normalization(raw_tools, expected_tools):
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    persona_mgr.get_persona_v3_by_id.return_value = {
        "name": "custom",
        "prompt": "persona prompt",
        "tools": raw_tools,
        "_begin_dialogs_processed": [],
    }
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    await orchestrator.reload_from_config(_build_cfg({"persona_id": "custom"}))

    handoff = orchestrator.handoffs[0]
    assert handoff.agent.tools == expected_tools


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_name",
    ["Planner", "1planner", "my planner", "planner-x", "a" * 65, ""],
)
async def test_reload_from_config_skips_invalid_names(bad_name):
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    persona_mgr.get_persona_v3_by_id.return_value = None
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    await orchestrator.reload_from_config(_build_cfg({"name": bad_name}))

    assert orchestrator.handoffs == []


@pytest.mark.asyncio
async def test_reload_from_config_skips_duplicate_names():
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    persona_mgr.get_persona_v3_by_id.return_value = None
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    cfg = {
        "agents": [
            {"name": "planner", "system_prompt": "first"},
            {"name": "planner", "system_prompt": "second"},
        ]
    }
    with patch("astrbot.core.subagent_orchestrator.logger") as mock_logger:
        await orchestrator.reload_from_config(cfg)

    assert len(orchestrator.handoffs) == 1
    assert orchestrator.handoffs[0].agent.instructions == "first"
    assert mock_logger.warning.called


@pytest.mark.asyncio
async def test_get_handoffs_resolves_per_config_and_caches():
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    persona_mgr.get_persona_v3_by_id.return_value = None
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    global_cfg = _build_cfg({"name": "planner"})
    await orchestrator.reload_from_config(global_cfg)

    # A different (e.g. session-scoped) config resolves its own subagents.
    session_cfg = _build_cfg({"name": "researcher"})
    session_handoffs = orchestrator.get_handoffs(session_cfg)
    assert [h.name for h in session_handoffs] == ["transfer_to_researcher"]
    assert [h.name for h in orchestrator.handoffs] == ["transfer_to_planner"]

    # Same config object -> cached, identical instances.
    assert orchestrator.get_handoffs(session_cfg) is session_handoffs
    # The global config was primed by reload_from_config.
    assert orchestrator.get_handoffs(global_cfg) is orchestrator.handoffs


@pytest.mark.asyncio
async def test_reload_from_config_clears_stale_cache():
    tool_mgr = MagicMock()
    persona_mgr = MagicMock()
    persona_mgr.get_persona_v3_by_id.return_value = None
    orchestrator = SubAgentOrchestrator(tool_mgr=tool_mgr, persona_mgr=persona_mgr)

    cfg = _build_cfg({"name": "planner"})
    first = orchestrator.get_handoffs(cfg)
    await orchestrator.reload_from_config(cfg)

    # Personas may have changed under us, so a reload must not serve the old build.
    assert orchestrator.get_handoffs(cfg) is not first
