"""Utility functions for spaceship module."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import SpaceshipNode


def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def build_node_from_hello(node_id: str, payload: dict[str, Any]) -> SpaceshipNode:
    """Build a SpaceshipNode from a node.hello payload."""
    return SpaceshipNode(
        node_id=node_id,
        alias=str(payload.get("alias", node_id)),
        hostname=str(payload.get("hostname", "")),
        platform=str(payload.get("platform", payload.get("os", "unknown"))),
        arch=str(payload.get("arch", "unknown")),
        agent_version=str(payload.get("agent_version", "0.1.0")),
        default_shell=str(payload.get("default_shell", "")),
        tags=list(payload.get("tags", [])),
    )
