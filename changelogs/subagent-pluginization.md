# Subagent plugin extraction

Asynchronous subagent scheduling, templates, private histories, steering, durable results, and read-only progress are provided by the independent `astrbot_plugin_subagent` plugin. The core exposes general Agent lifecycle hooks, caller-owned SDK contexts, background task registration, and per-tool timeouts. Legacy expert discovery and reload remain available only for plugin SDK compatibility; core main no longer mounts them automatically.

Main uses `spawn_agent`, `list_agents`, `wait_agent`, `get_agent_result`, `send_message`, and `cancel_agent`. Workers run asynchronously and cannot recursively delegate. Main retains its tools. Follow-up input steers a running turn; unconsumed input or a completed worker starts another turn with the same identity and private history.

Results return at complete step boundaries or wake idle main through the existing event queue, bound to the original session, conversation, and sender. The plugin checks the current conversation before enqueueing, during recovery, and when handling wakeups; switching conversations prevents automatic delivery into another conversation. Checkpoints survive restarts without replaying in-flight tools. Result receipts are confirmed against saved main history. Cancelling a worker leaves its background Shell processes under AstrBot's existing Shell session management.

## Entry-point migration

| Previous entry | Replacement |
| --- | --- |
| Extensions → SubAgents | Extensions → Plugins → Subagent → Settings |
| Built-in SubAgent page | Plugin detail → runtime |
| Legacy `transfer_to_*` experts | Available through the plugin compatibility SDK; core main no longer mounts them |
| Core `subagent_orchestrator` settings | Only `agents` data is retained for legacy plugins; asynchronous workers use plugin settings |
| `/api/v1/subagents/*` and `/api/subagent/*` | Removed; new runtime views use authenticated plugin APIs |

Native expert mounting, `main_enable`, tool deduplication, and `router_system_prompt` defaults and injection are removed. The legacy `agents` data slot remains so configuration cleanup does not discard definitions needed by existing plugins. Existing definitions can optionally be copied into the plugin's `agents` list; use `enabled` for plugin activation. The plugin requires this core SDK update and is distributed separately.

The legacy `@agent` / `register_agent`, `RegisteringAgent`, and `HandoffTool` SDK interfaces remain available for existing plugins, including nested tool binding and foreground/background handoff execution. `Context.subagent_orchestrator`, its constructor argument, configuration loading, and `reload_from_config()` are also retained. These legacy interfaces are deprecated in favor of the plugin's worker tools; retaining them keeps existing expert discovery and delegation working while plugins migrate.

The runtime view remains read-only and uses AstrBot's standard plugin API authentication and permissions. Users communicate with workers through main. Chinese and English usage guides include the updated entry mapping and screenshots using sample records.
