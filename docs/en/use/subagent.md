# Subagent Plugin {#agent-handoff-and-subagent}

Asynchronous delegation is provided by the independent `astrbot_plugin_subagent` plugin for AstrBot's built-in Agent. It requires the core Agent lifecycle SDK update. Subagents provided by external Agent services remain configured in those services. Configuration-driven legacy experts and their orchestrator remain available for existing plugins.

## Install and configure {#configuration}

Upload the plugin ZIP through **Extensions → Plugins**, then open **Subagent → Settings**. Main can autonomously create generic workers or select configured expert templates.

Templates support a name, public description, persona, system prompt, provider, and tools. A selected persona supplies its prompt, preset dialogue, and tools. An empty tool list means no tools. Main retains its own tools; expert configuration no longer removes tools from main.

## Execution and follow-up

`spawn_agent` submits the first task together with creation and returns a worker ID immediately. Workers run concurrently while main continues independent work.

| Tool | Purpose |
| --- | --- |
| `spawn_agent` | Start a generic worker or select an expert template |
| `list_agents` | Read states and completed steps within the current sender and conversation |
| `wait_agent` | Wait for any/all workers; timeout leaves workers running |
| `get_agent_result` | Read repeatable results or errors |
| `send_message` | Steer an active turn, or automatically start another turn if complete or input remains unconsumed |
| `cancel_agent` | Cancel one worker independently |

Users communicate with workers through main. Workers do not automatically inherit main's full history: include the necessary context, constraints, and expected output in the task. Workers retain a private history and stable ID, but cannot recursively spawn workers.

Defaults: 3 concurrent workers per session, a 600-second timeout including queue time, and 30 steps per turn capped by main's limit. `wait_agent` accepts 0–60000 ms and `any` / `all`. Timing out a wait never cancels a worker.

## Inspect progress

Open **Extensions → Plugins → Subagent → runtime** to inspect states, turns, completed steps, results, and execution records. This view is read-only and uses AstrBot's standard plugin API authentication and permissions.

![Read-only worker progress in the plugin](./images/subagent-plugin-runtime-en.png)

The screenshot uses sample records to demonstrate the layout.

An active main receives results at complete step boundaries. An idle main resumes through AstrBot's existing event queue, bound to the original session, conversation, and sender. The plugin validates the current CID before enqueueing, during recovery, and when handling wakeups. Switching conversations prevents automatic wakeups for the old conversation and never redirects its results. Platform capabilities still determine proactive delivery; see [Proactive Capabilities](./proactive-agent.md).

## Interruption and recovery

States, completed steps, and pending input persist in AstrBot's database. After restart or plugin reload, unfinished workers become `interrupted`; possibly executed tools are never automatically replayed. Main can inspect and resume them through `send_message`.

Delivery is at least once: abnormal exits can cause duplicates. Stopping a session cancels its background work. Cancelling one worker leaves main and its siblings running. Cancelling a worker does not additionally terminate background Shell processes it has started; Shell sessions use AstrBot's existing management tools and process timeouts.

## Migration

| Previous entry | Replacement |
| --- | --- |
| Extensions → SubAgents | Extensions → Plugins → Subagent → Settings |
| Built-in SubAgent page | Plugin detail → runtime |
| Legacy `transfer_to_*` experts | Retained; use `spawn_agent` for new asynchronous workers |
| Core `subagent_orchestrator` configuration | Retained; optionally copy expert definitions into the plugin's `agents`, and use `enabled` |

The tool deduplication switch no longer removes main's tools. The legacy `main_enable` switch and router prompt still apply to legacy experts. The old `/api/v1/subagents/*` and `/api/subagent/*` routes are removed; the new plugin uses standard plugin APIs.

The legacy `@agent` / `register_agent`, `RegisteringAgent`, and `HandoffTool` SDK interfaces remain supported for existing plugins, including nested tools and foreground/background execution. `Context.subagent_orchestrator`, its constructor argument, configuration loading, and `reload_from_config()` are also retained so existing plugins can discover and invoke legacy experts. These interfaces are deprecated in favor of the plugin's worker tools.
