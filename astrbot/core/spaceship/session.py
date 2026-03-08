"""Session management for spaceship websocket connections."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .models import SessionConnection


@dataclass(slots=True)
class ActiveSession:
    """Active websocket session for a connected node."""

    session_id: str
    node_id: str
    connection: SessionConnection
    granted_scopes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SessionHub:
    """Central registry of active node sessions."""

    sessions: dict[str, ActiveSession] = field(default_factory=dict)

    def bind(self, session: ActiveSession) -> None:
        """Register a new active session."""
        self.sessions[session.node_id] = session

    def unbind(self, node_id: str) -> None:
        """Remove a session by node_id."""
        self.sessions.pop(node_id, None)

    def get(self, node_id: str) -> ActiveSession | None:
        """Retrieve an active session by node_id."""
        return self.sessions.get(node_id)

    async def send(self, node_id: str, envelope: Any) -> None:
        """Send an envelope to a node's active session."""
        session = self.get(node_id)
        if session is None:
            raise LookupError("session not found")
        if hasattr(envelope, "__dataclass_fields__"):
            payload = asdict(envelope)
        else:
            payload = envelope
        await session.connection.send_json(payload)
