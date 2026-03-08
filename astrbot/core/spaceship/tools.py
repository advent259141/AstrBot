"""Spaceship tool service and LLM tool registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from .models import (
    ListDirToolRequest,
    ReadFileToolRequest,
    ShellToolRequest,
    TaskSpec,
)

if TYPE_CHECKING:
    from .dispatcher import TaskDispatcher


@dataclass(slots=True)
class SpaceshipToolService:
    """Service layer for spaceship LLM-facing tools."""

    dispatcher: TaskDispatcher

    async def execute_shell(self, request: ShellToolRequest, requested_by: str) -> str:
        """Execute a shell command on a remote node."""
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="exec",
            node_id=request.node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=request.timeout_sec,
            max_output_bytes=request.max_output_bytes,
            risk_level="normal",
            args={
                "command": request.command,
                "cwd": request.cwd,
                "shell": request.shell,
                "stream": request.stream,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def list_dir(self, request: ListDirToolRequest, requested_by: str) -> str:
        """List directory contents on a remote node."""
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="list_dir",
            node_id=request.node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "path": request.path,
                "recursive": request.recursive,
                "show_hidden": request.show_hidden,
                "limit": request.limit,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def read_file(self, request: ReadFileToolRequest, requested_by: str) -> str:
        """Read a file from a remote node."""
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="read_file",
            node_id=request.node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=request.max_bytes,
            risk_level="normal",
            args={
                "path": request.path,
                "max_bytes": request.max_bytes,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr
