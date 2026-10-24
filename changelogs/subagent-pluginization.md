# Subagent plugin extraction

Subagent scheduling, templates, private histories, steering, durable results, and read-only progress now live in the independent `astrbot_plugin_subagent` plugin. The core exposes general Agent lifecycle hooks, caller-owned SDK contexts, background task registration, and per-tool timeouts.

Main uses `spawn_agent`, `list_agents`, `wait_agent`, `get_agent_result`, `send_message`, and `cancel_agent`. Workers run asynchronously and cannot recursively delegate. Main retains its tools. Follow-up input steers a running turn; unconsumed input or a completed worker starts another turn with the same identity and private history.

Results return at complete step boundaries or wake idle main through the existing event queue, bound to the original session, conversation, and sender. The plugin checks the current conversation before enqueueing, during recovery, and when handling wakeups; switching conversations prevents automatic delivery into another conversation. Checkpoints survive restarts without replaying in-flight tools. Result receipts are confirmed against saved main history. Cancelling a worker leaves its background Shell processes under AstrBot's existing Shell session management.

## Entry-point migration

| Previous entry | Replacement |
| --- | --- |
| Extensions → SubAgents | Extensions → Plugins → Subagent → Settings |
| Built-in SubAgent page | Plugin detail → runtime |
| `transfer_to_*`, `@agent` | `spawn_agent`; legacy tools and decorator are removed |
| Core `subagent_orchestrator` settings and `/api/v1/subagents/*` | Plugin settings and authenticated plugin view APIs |

The old tool-deduplication switch and router prompt are removed. Existing expert definitions can be copied into the plugin's `agents` list; use `enabled` for plugin activation. The plugin requires this core SDK update and is distributed separately.

The runtime view remains read-only and uses AstrBot's standard plugin API authentication and permissions. Users communicate with workers through main. Chinese and English usage guides include the updated entry mapping and screenshots using sample records.
