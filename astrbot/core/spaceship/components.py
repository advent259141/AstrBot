"""Spaceship runtime adapter components for ComputerBooter compatibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .dispatcher import TaskDispatcher
from .models import TaskSpec


@dataclass(slots=True)
class SpaceshipShellComponent:
    """Shell execution component compatible with ComputerBooter interface."""

    dispatcher: TaskDispatcher
    node_id: str

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = 30,
        shell: bool = True,
        background: bool = False,
    ) -> dict[str, Any]:
        """Execute a shell command via the dispatcher."""
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="exec",
            node_id=self.node_id,
            requested_by="system",
            requested_via="runtime_adapter",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=timeout or 30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "command": command,
                "cwd": cwd,
                "env": env or {},
                "shell": shell,
                "background": background,
            },
        )
        result = await self.dispatcher.dispatch(task)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "duration_ms": result.duration_ms,
            "timed_out": result.timed_out,
            "truncated": result.truncated,
        }


@dataclass(slots=True)
class SpaceshipFileSystemComponent:
    """Filesystem operations component compatible with ComputerBooter interface."""

    dispatcher: TaskDispatcher
    node_id: str

    async def list_dir(
        self,
        path: str = ".",
        show_hidden: bool = False,
        recursive: bool = False,
        limit: int = 200,
    ) -> dict[str, Any]:
        """List directory contents."""
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="list_dir",
            node_id=self.node_id,
            requested_by="system",
            requested_via="runtime_adapter",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "path": path,
                "recursive": recursive,
                "show_hidden": show_hidden,
                "limit": limit,
            },
        )
        result = await self.dispatcher.dispatch(task)
        if result.final_state != "success":
            raise RuntimeError(result.stderr or "list_dir failed")
        return {
            "success": True,
            "content": result.stdout,
            "truncated": result.truncated,
        }

    async def read_file(self, path: str, encoding: str = "utf-8") -> dict[str, Any]:
        """Read a file's contents."""
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="read_file",
            node_id=self.node_id,
            requested_by="system",
            requested_via="runtime_adapter",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={"path": path, "encoding": encoding},
        )
        result = await self.dispatcher.dispatch(task)
        if result.final_state != "success":
            raise RuntimeError(result.stderr or "read_file failed")
        return {
            "success": True,
            "content": result.stdout,
            "truncated": result.truncated,
        }

    async def write_file(
        self,
        path: str,
        content: str,
        append: bool = False,
        create_dirs: bool = True,
    ) -> dict[str, Any]:
        """Write content to a file."""
        task = TaskSpec(
            task_id=f"task_{uuid4().hex}",
            task_type="write_file",
            node_id=self.node_id,
            requested_by="system",
            requested_via="runtime_adapter",
            tool_call_id=f"tool_{uuid4().hex}",
            timeout_sec=30,
            max_output_bytes=65536,
            risk_level="normal",
            args={
                "path": path,
                "content": content,
                "append": append,
                "create_dirs": create_dirs,
            },
        )
        result = await self.dispatcher.dispatch(task)
        if result.final_state != "success":
            raise RuntimeError(result.stderr or "write_file failed")
        return {
            "success": True,
            "content": result.stdout,
        }


@dataclass(slots=True)
class SpaceshipNodeBooter:
    """Node-specific booter compatible with ComputerBooter interface."""

    dispatcher: TaskDispatcher
    node_id: str

    async def boot(self, session_id: str) -> None:
        """Boot the node (no-op for spaceship)."""
        _ = session_id
        return None

    async def shutdown(self) -> None:
        """Shutdown the node (no-op for spaceship)."""
        return None

    @property
    def shell(self) -> SpaceshipShellComponent:
        """Access shell execution component."""
        return SpaceshipShellComponent(dispatcher=self.dispatcher, node_id=self.node_id)

    @property
    def fs(self) -> SpaceshipFileSystemComponent:
        """Access filesystem component."""
        return SpaceshipFileSystemComponent(
            dispatcher=self.dispatcher, node_id=self.node_id
        )
