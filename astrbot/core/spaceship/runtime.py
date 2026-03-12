"""Spaceship runtime orchestrating all spaceship services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .components import SpaceshipNodeBooter
from .dispatcher import TaskDispatcher
from .file_transfer import FileTransferService
from .gateway import SpaceshipGatewayService
from .models import (
    CopyFileToolRequest,
    DeleteFileToolRequest,
    DownloadFileToolRequest,
    EditFileToolRequest,
    ExecutePythonToolRequest,
    GrepToolRequest,
    ListDirToolRequest,
    MoveFileToolRequest,
    ReadFileToolRequest,
    SessionConnection,
    ShellToolRequest,
    SpaceshipNode,
    UploadFileToolRequest,
    WriteFileToolRequest,
)
from .session import SessionHub
from .tools import SpaceshipToolService
from .utils import build_node_from_hello


@dataclass(slots=True)
class SpaceshipRuntime:
    """Central runtime managing all spaceship operations."""

    nodes: dict[str, SpaceshipNode] = field(default_factory=dict)
    session_hub: SessionHub = field(init=False)
    dispatcher: TaskDispatcher = field(init=False)
    gateway: SpaceshipGatewayService = field(init=False)
    tool_service: SpaceshipToolService = field(init=False)
    file_transfer: FileTransferService = field(init=False)

    def __post_init__(self) -> None:
        self.session_hub = SessionHub()
        self.dispatcher = TaskDispatcher(session_hub=self.session_hub)
        self.gateway = SpaceshipGatewayService(runtime=self)
        self.file_transfer = FileTransferService()
        self.tool_service = SpaceshipToolService(
            dispatcher=self.dispatcher,
            runtime=self,
        )

    def upsert_node(self, payload: dict[str, Any]) -> SpaceshipNode:
        """Update or insert a node from a payload."""
        node_id = str(payload.get("node_id", "")).strip()
        if not node_id:
            raise ValueError("node_id is required")

        node = self.nodes.get(node_id)
        if node is None:
            node = SpaceshipNode(
                node_id=node_id,
                alias=str(payload.get("alias", node_id)),
                hostname=str(payload.get("hostname", "")),
                platform=str(payload.get("platform", payload.get("os", "unknown"))),
                arch=str(payload.get("arch", "unknown")),
            )
            self.nodes[node_id] = node

        node.alias = str(payload.get("alias", node.alias))
        node.hostname = str(payload.get("hostname", node.hostname))
        node.platform = str(payload.get("platform", payload.get("os", node.platform)))
        node.arch = str(payload.get("arch", node.arch))
        node.status = str(payload.get("status", "active"))
        node.granted_scopes = list(payload.get("granted_scopes", node.granted_scopes))
        node.tags = list(payload.get("tags", node.tags))
        node.agent_version = str(payload.get("agent_version", node.agent_version))
        node.default_shell = str(payload.get("default_shell", node.default_shell))
        node.maintenance_mode = bool(
            payload.get("maintenance_mode", node.maintenance_mode)
        )
        node.last_seen_at = datetime.now(timezone.utc)
        return node

    async def handle_incoming_event(
        self,
        envelope: dict[str, Any],
        connection: SessionConnection,
    ) -> dict[str, Any] | None:
        """Handle an incoming websocket event from a node."""
        event_type = str(envelope.get("type", ""))
        node_id = str(envelope.get("node_id", ""))
        payload = envelope.get("payload") or {}
        if not isinstance(payload, dict):
            raise TypeError("payload must be an object")

        if event_type == "node.hello":
            welcome = await self.gateway.accept_hello(
                profile=build_node_from_hello(node_id=node_id, payload=payload),
                connection=connection,
                granted_scopes=list(payload.get("declared_capabilities", [])),
            )
            return asdict(welcome)

        if event_type == "node.heartbeat":
            self.gateway.handle_heartbeat(node_id)
            return None

        if event_type in {"task.output", "task.result", "task.error"}:
            self.gateway.handle_task_event(
                node_id=node_id, event_type=event_type, payload=payload
            )
            return None

        return None

    def disconnect(self, node_id: str) -> None:
        """Mark a node as offline when its connection closes."""
        node = self.nodes.get(node_id)
        if node:
            node.status = "offline"
        self.session_hub.unbind(node_id)

    def heartbeat(self, node_id: str) -> None:
        """Update node last_seen_at on heartbeat."""
        node = self.nodes.get(node_id)
        if node:
            node.last_seen_at = datetime.now(timezone.utc)

    def get_node_info(self, node_id: str) -> dict[str, Any] | None:
        """Get node metadata by node_id."""
        node = self.nodes.get(node_id)
        if node:
            return asdict(node)
        return None

    def list_nodes(self) -> list[dict[str, Any]]:
        """List all node metadata for dashboard and tool queries."""
        return [asdict(node) for node in self.nodes.values()]

    def get_node_booter(self, node_id: str) -> SpaceshipNodeBooter | None:
        """Get a booter instance for a specific node."""
        node = self.nodes.get(node_id)
        if node and node.status == "active":
            return SpaceshipNodeBooter(dispatcher=self.dispatcher, node_id=node_id)
        return None

    async def enter_node(self, node_id: str, requested_by: str) -> str:
        """Enter a node workspace for current session."""
        return await self.tool_service.enter_node(node_id=node_id, requested_by=requested_by)

    async def exit_node(self, requested_by: str) -> str:
        """Exit current node workspace for current session."""
        return await self.tool_service.exit_node(requested_by=requested_by)

    async def execute_shell(self, request: ShellToolRequest, requested_by: str) -> str:
        """Execute shell command on the currently entered node (tool layer)."""
        return await self.tool_service.execute_shell(
            request=request, requested_by=requested_by
        )

    async def list_dir(self, request: ListDirToolRequest, requested_by: str) -> str:
        """List directory on the currently entered node (tool layer)."""
        return await self.tool_service.list_dir(
            request=request, requested_by=requested_by
        )

    async def read_file(self, request: ReadFileToolRequest, requested_by: str) -> str:
        """Read file from the currently entered node (tool layer)."""
        return await self.tool_service.read_file(
            request=request, requested_by=requested_by
        )

    async def write_file(self, request: WriteFileToolRequest, requested_by: str) -> str:
        """Write file on the currently entered node (tool layer)."""
        return await self.tool_service.write_file(
            request=request, requested_by=requested_by
        )

    async def cancel_task(self, task_id: str, node_id: str, reason: str = "") -> bool:
        """Cancel a running task on a remote node."""
        return await self.dispatcher.cancel(task_id, node_id, reason)

    def list_pending_tasks(self) -> list[str]:
        """Return task IDs of currently pending (in-flight) tasks."""
        return self.dispatcher.list_pending_tasks()

    async def edit_file(self, request: EditFileToolRequest, requested_by: str) -> str:
        """Edit file on the currently entered node via search-and-replace (tool layer)."""
        return await self.tool_service.edit_file(
            request=request, requested_by=requested_by
        )

    async def grep(self, request: GrepToolRequest, requested_by: str) -> str:
        """Search for text patterns in files on the currently entered node (tool layer)."""
        return await self.tool_service.grep(
            request=request, requested_by=requested_by
        )

    async def delete_file(self, request: DeleteFileToolRequest, requested_by: str) -> str:
        """Delete a file or directory on the currently entered node (tool layer)."""
        return await self.tool_service.delete_file(
            request=request, requested_by=requested_by
        )

    async def move_file(self, request: MoveFileToolRequest, requested_by: str) -> str:
        """Move or rename a file/directory on the currently entered node (tool layer)."""
        return await self.tool_service.move_file(
            request=request, requested_by=requested_by
        )

    async def copy_file(self, request: CopyFileToolRequest, requested_by: str) -> str:
        """Copy a file or directory on the currently entered node (tool layer)."""
        return await self.tool_service.copy_file(
            request=request, requested_by=requested_by
        )

    async def execute_python(self, request: ExecutePythonToolRequest, requested_by: str) -> str:
        """Execute Python code on the currently entered node (tool layer)."""
        return await self.tool_service.execute_python(
            request=request, requested_by=requested_by
        )

    async def upload_file(
        self, request: UploadFileToolRequest, requested_by: str, base_url: str
    ) -> str:
        """Upload a file from AstrBot to the remote node (tool layer)."""
        return await self.tool_service.upload_file(
            request=request, requested_by=requested_by, base_url=base_url
        )

    async def download_file(
        self, request: DownloadFileToolRequest, requested_by: str, base_url: str
    ) -> str:
        """Download a file from the remote node to AstrBot (tool layer)."""
        return await self.tool_service.download_file(
            request=request, requested_by=requested_by, base_url=base_url
        )

