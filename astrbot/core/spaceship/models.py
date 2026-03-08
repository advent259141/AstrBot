"""Spaceship data models and type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, Protocol, TypeVar

PayloadT = TypeVar("PayloadT")


@dataclass(slots=True)
class Envelope(Generic[PayloadT]):
    """Websocket message envelope wrapping payloads with metadata."""

    type: str
    request_id: str
    session_id: str
    node_id: str
    seq: int
    ts: str
    payload: PayloadT


@dataclass(slots=True)
class SpaceshipNode:
    """Remote node profile and metadata."""

    node_id: str
    alias: str
    hostname: str
    platform: str
    arch: str
    status: str = "offline"
    granted_scopes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    agent_version: str = "0.1.0"
    default_shell: str = ""
    maintenance_mode: bool = False
    last_seen_at: datetime | None = None


@dataclass(slots=True)
class TaskSpec:
    """Specification for a remote task to execute on a node."""

    task_id: str
    task_type: str
    node_id: str
    requested_by: str
    requested_via: str
    tool_call_id: str
    timeout_sec: int
    max_output_bytes: int
    risk_level: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskResult:
    """Result of a completed task execution."""

    task_id: str
    final_state: str
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    timed_out: bool = False
    truncated: bool = False


@dataclass(slots=True)
class ShellToolRequest:
    """Request to execute a shell command on a remote node."""

    node_id: str
    command: str
    cwd: str | None = None
    timeout_sec: int = 30
    shell: str | None = None
    stream: bool = True
    max_output_bytes: int = 65536


@dataclass(slots=True)
class ListDirToolRequest:
    """Request to list directory contents on a remote node."""

    node_id: str
    path: str = "."
    recursive: bool = False
    show_hidden: bool = False
    limit: int = 200


@dataclass(slots=True)
class ReadFileToolRequest:
    """Request to read a file from a remote node."""

    node_id: str
    path: str
    max_bytes: int = 65536


@dataclass(slots=True)
class WriteFileToolRequest:
    """Request to write a file on a remote node."""

    node_id: str
    path: str
    content: str
    append: bool = False
    create_dirs: bool = True


class SessionConnection(Protocol):
    """Protocol for websocket connections that can send JSON."""

    async def send_json(self, payload: dict[str, Any]) -> None: ...
