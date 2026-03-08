"""Spaceship gateway service for node registration and heartbeat."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from .models import Envelope, SessionConnection, SpaceshipNode
from .session import ActiveSession
from .utils import now_iso

if TYPE_CHECKING:
    from .runtime import SpaceshipRuntime


@dataclass(slots=True)
class SpaceshipGatewayService:
    """Gateway service handling node registration and heartbeat."""

    runtime: SpaceshipRuntime

    async def accept_hello(
        self,
        profile: SpaceshipNode,
        connection: SessionConnection,
        granted_scopes: list[str] | None = None,
    ) -> Envelope[dict[str, Any]]:
        """Accept a node hello and register the session."""
        session = ActiveSession(
            session_id=f"sess_{uuid4().hex}",
            node_id=profile.node_id,
            connection=connection,
            granted_scopes=granted_scopes or [],
        )
        profile.status = "active"
        profile.last_seen_at = datetime.now(timezone.utc)
        profile.granted_scopes = granted_scopes or profile.granted_scopes
        self.runtime.nodes[profile.node_id] = profile
        self.runtime.session_hub.bind(session)
        return Envelope(
            type="node.welcome",
            request_id="req_boot_001",
            session_id=session.session_id,
            node_id=profile.node_id,
            seq=1,
            ts=now_iso(),
            payload={
                "heartbeat_interval_sec": 20,
                "resume_support": True,
                "server_time": now_iso(),
                "granted_scopes": session.granted_scopes,
                "policy_version": "dev",
            },
        )

    def handle_heartbeat(self, node_id: str) -> None:
        """Update node last_seen_at timestamp on heartbeat."""
        self.runtime.heartbeat(node_id)

    def handle_task_event(
        self, node_id: str, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Delegate task events to the dispatcher."""
        self.runtime.dispatcher.handle_task_event(
            node_id=node_id, event_type=event_type, payload=payload
        )
