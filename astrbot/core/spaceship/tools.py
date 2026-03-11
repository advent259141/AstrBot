"""Spaceship tool service and LLM tool registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from astrbot.core import sp

from .models import (
    CopyFileToolRequest,
    DeleteFileToolRequest,
    EditFileToolRequest,
    ExecutePythonToolRequest,
    GrepToolRequest,
    ListDirToolRequest,
    MoveFileToolRequest,
    ReadFileToolRequest,
    ShellToolRequest,
    TaskSpec,
    WriteFileToolRequest,
)

if TYPE_CHECKING:
    from .dispatcher import TaskDispatcher
    from .runtime import SpaceshipRuntime

_SELECTED_NODE_KEY = "spaceship_selected_node_id"


@dataclass(slots=True)
class SpaceshipToolService:
    """Service layer for spaceship LLM-facing tools."""

    dispatcher: TaskDispatcher
    runtime: SpaceshipRuntime

    async def enter_node(self, node_id: str, requested_by: str) -> str:
        """Enter a node and mark it as the current workspace node for the session."""
        normalized_node_id = node_id.strip()
        if not normalized_node_id:
            raise ValueError("node_id is required")

        node = self.runtime.nodes.get(normalized_node_id)
        if node is None:
            raise ValueError(f"node '{normalized_node_id}' not found")
        if node.status != "active":
            raise ValueError(f"node '{normalized_node_id}' is not active")

        await sp.session_put(requested_by, _SELECTED_NODE_KEY, normalized_node_id)
        return (
            f"entered node '{normalized_node_id}'"
            f" (alias={node.alias}, platform={node.platform}, arch={node.arch})"
        )

    async def exit_node(self, requested_by: str) -> str:
        """Exit the current node workspace for the session."""
        selected_node_id = await self.get_selected_node_id(requested_by)
        if not selected_node_id:
            return "no active node workspace to exit"

        await sp.session_remove(requested_by, _SELECTED_NODE_KEY)
        return f"exited node '{selected_node_id}'"

    async def get_selected_node_id(self, requested_by: str) -> str | None:
        """Get the currently selected node id for the session."""
        selected_node_id = await sp.session_get(
            requested_by,
            _SELECTED_NODE_KEY,
            default=None,
        )
        if selected_node_id is None:
            return None
        normalized = str(selected_node_id).strip()
        return normalized or None

    async def require_selected_node_id(self, requested_by: str) -> str:
        """Resolve current node workspace or raise a user-facing error."""
        selected_node_id = await self.get_selected_node_id(requested_by)
        if not selected_node_id:
            raise ValueError(
                "no active node workspace; call enternode first before using spaceship execution tools"
            )

        node = self.runtime.nodes.get(selected_node_id)
        if node is None:
            await sp.session_remove(requested_by, _SELECTED_NODE_KEY)
            raise ValueError(
                f"selected node '{selected_node_id}' no longer exists; please call enternode again"
            )
        if node.status != "active":
            raise ValueError(
                f"selected node '{selected_node_id}' is offline; please enter another active node or retry later"
            )
        return selected_node_id

    async def execute_shell(self, request: ShellToolRequest, requested_by: str) -> str:
        """Execute a shell command on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="exec",
            node_id=node_id,
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
        """List directory contents on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="list_dir",
            node_id=node_id,
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
        """Read a file from the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="read_file",
            node_id=node_id,
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

    async def write_file(self, request: WriteFileToolRequest, requested_by: str) -> str:
        """Write a file on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="write_file",
            node_id=node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "path": request.path,
                "content": request.content,
                "append": request.append,
                "create_dirs": request.create_dirs,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def edit_file(self, request: EditFileToolRequest, requested_by: str) -> str:
        """Edit a file on the currently entered node via search-and-replace."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="edit_file",
            node_id=node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "path": request.path,
                "edits": request.edits,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def grep(self, request: GrepToolRequest, requested_by: str) -> str:
        """Search for text patterns in files on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="grep",
            node_id=node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "pattern": request.pattern,
                "path": request.path,
                "is_regex": request.is_regex,
                "case_insensitive": request.case_insensitive,
                "include_globs": request.include_globs or [],
                "exclude_globs": request.exclude_globs or [],
                "max_matches": request.max_matches,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def delete_file(self, request: DeleteFileToolRequest, requested_by: str) -> str:
        """Delete a file or directory on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="delete_file",
            node_id=node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "path": request.path,
                "recursive": request.recursive,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def move_file(self, request: MoveFileToolRequest, requested_by: str) -> str:
        """Move or rename a file/directory on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="move_file",
            node_id=node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "src": request.src,
                "dst": request.dst,
                "overwrite": request.overwrite,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def copy_file(self, request: CopyFileToolRequest, requested_by: str) -> str:
        """Copy a file or directory on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="copy_file",
            node_id=node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "src": request.src,
                "dst": request.dst,
                "recursive": request.recursive,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr

    async def execute_python(self, request: ExecutePythonToolRequest, requested_by: str) -> str:
        """Execute Python code on the currently entered node."""
        node_id = await self.require_selected_node_id(requested_by)
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="exec_python",
            node_id=node_id,
            requested_by=requested_by,
            requested_via="tool",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=request.timeout_sec,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "code": request.code,
                "cwd": request.cwd,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return result.stdout if result.final_state == "success" else result.stderr
