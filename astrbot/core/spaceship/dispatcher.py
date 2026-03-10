"""Task dispatcher for remote node executions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .models import Envelope, TaskResult, TaskSpec
from .session import SessionHub
from .utils import now_iso


@dataclass(slots=True)
class TaskDispatcher:
    """Dispatches tasks to remote nodes and tracks their execution."""

    session_hub: SessionHub
    _pending: dict[str, asyncio.Future[TaskResult]] = field(init=False)
    _buffers: dict[str, dict[str, list[str]]] = field(init=False)

    def __post_init__(self) -> None:
        self._pending: dict[str, asyncio.Future[TaskResult]] = {}
        self._buffers: dict[str, dict[str, list[str]]] = {}

    async def dispatch(self, task: TaskSpec) -> TaskResult:
        """Dispatch a task to a remote node and wait for result."""
        if not task.task_id:
            task.task_id = f"task_{uuid4().hex}"
        if not task.tool_call_id:
            task.tool_call_id = f"tool_{uuid4().hex}"

        session = self.session_hub.get(task.node_id)
        if session is None:
            return TaskResult(
                task_id=task.task_id,
                final_state="failed",
                stderr="node is offline",
            )

        future = asyncio.get_running_loop().create_future()
        self._pending[task.task_id] = future
        self._buffers[task.task_id] = {"stdout": [], "stderr": []}

        try:
            envelope = Envelope(
                type="task.dispatch",
                request_id=task.tool_call_id,
                session_id=session.session_id,
                node_id=task.node_id,
                seq=0,
                ts=now_iso(),
                payload={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "node_id": task.node_id,
                    "requested_by": task.requested_by,
                    "requested_via": task.requested_via,
                    "tool_call_id": task.tool_call_id,
                    "timeout_sec": task.timeout_sec,
                    "max_output_bytes": task.max_output_bytes,
                    "risk_level": task.risk_level,
                    "args": task.args,
                },
            )
            await self.session_hub.send(task.node_id, envelope)
            return await asyncio.wait_for(future, timeout=task.timeout_sec + 5)
        finally:
            self._pending.pop(task.task_id, None)
            self._buffers.pop(task.task_id, None)

    def handle_task_event(
        self, node_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Handle incoming task events from remote nodes."""
        _ = node_id
        task_id = str(payload.get("task_id", ""))
        if not task_id:
            return

        if event_type == "task.output":
            stream = str(payload.get("stream", "stdout"))
            chunk = str(payload.get("chunk", ""))
            buffer = self._buffers.get(task_id)
            if buffer is not None and stream in buffer:
                buffer[stream].append(chunk)
            return

        future = self._pending.get(task_id)
        if future is None or future.done():
            return

        if event_type == "task.result":
            buffer = self._buffers.get(task_id, {"stdout": [], "stderr": []})
            future.set_result(
                TaskResult(
                    task_id=task_id,
                    final_state=str(payload.get("final_state", "success")),
                    exit_code=int(payload.get("exit_code", 0)),
                    stdout="".join(buffer.get("stdout", [])),
                    stderr="".join(buffer.get("stderr", [])),
                    duration_ms=int(payload.get("duration_ms", 0)),
                    timed_out=bool(payload.get("timed_out", False)),
                    truncated=bool(payload.get("truncated", False)),
                )
            )
            return

        if event_type == "task.error":
            future.set_result(
                TaskResult(
                    task_id=task_id,
                    final_state="failed",
                    stderr=str(payload.get("message", "task failed")),
                )
            )

    async def cancel(self, task_id: str, node_id: str, reason: str = "") -> bool:
        """Send a task.cancel envelope and resolve the pending future."""
        session = self.session_hub.get(node_id)
        if session is None:
            return False

        envelope = Envelope(
            type="task.cancel",
            request_id=f"cancel_{uuid4().hex}",
            session_id=session.session_id,
            node_id=node_id,
            seq=0,
            ts=now_iso(),
            payload={"task_id": task_id, "reason": reason},
        )
        await self.session_hub.send(node_id, envelope)

        future = self._pending.get(task_id)
        if future and not future.done():
            future.set_result(
                TaskResult(
                    task_id=task_id,
                    final_state="cancelled",
                    stderr=f"cancelled: {reason}" if reason else "cancelled by user",
                )
            )
        return True

    def list_pending_tasks(self) -> list[str]:
        """Return task IDs of currently pending (in-flight) tasks."""
        return [tid for tid, f in self._pending.items() if not f.done()]
