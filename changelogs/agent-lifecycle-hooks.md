# Agent lifecycle hooks

- Add `on_agent_step_start` and `on_agent_step_end` plugin hooks for the built-in tool loop. Step-end handlers receive the complete assistant/tool batch, including tool image messages.
- Extend the existing `on_agent_done` hook to notify each run's exit once, including provider errors, exceptions, cancellation, and step-budget exhaustion. No separate run-end or history-saved hook is added.
- Expose `run_end_reason` and `run_error` on `ContextWrapper`. Existing done handlers must allow `response=None` when there is no final response. Use `on_llm_response` to edit replies before delivery.
- Keep normal response notifications independent from exit cleanup. Interrupted responses and cleanup without a model reply do not produce a response notification. Stopped events still reach all eligible done handlers.
- Preserve task cancellation through plugin hook dispatch and close response generators deterministically when their consumers exit.
