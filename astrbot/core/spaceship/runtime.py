"""Spaceship runtime orchestrating all spaceship services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .components import SpaceshipNodeBooter
from .dispatcher import TaskDispatcher
from .gateway import SpaceshipGatewayService
from .models import (
    ListDirToolRequest,
    ReadFileToolRequest,
    SessionConnection,
    ShellToolRequest,
    SpaceshipNode,
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

    def __post_init__(self) -> None:
        self.session_hub = SessionHub()
        self.dispatcher = TaskDispatcher(session_hub=self.session_hub)
        self.gateway = SpaceshipGatewayService(runtime=self)
        self.tool_service = SpaceshipToolService(dispatcher=self.dispatcher)

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

    async def execute_shell(self, request: ShellToolRequest, requested_by: str) -> str:
        """Execute shell command on a remote node (tool layer)."""
        return await self.tool_service.execute_shell(
            request=request, requested_by=requested_by
        )

    async def list_dir(self, request: ListDirToolRequest, requested_by: str) -> str:
        """List directory on a remote node (tool layer)."""
        return await self.tool_service.list_dir(
            request=request, requested_by=requested_by
        )

    async def read_file(self, request: ReadFileToolRequest, requested_by: str) -> str:
        """Read file from a remote node (tool layer)."""
        return await self.tool_service.read_file(
            request=request, requested_by=requested_by
        )
