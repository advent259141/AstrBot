"""Spaceship: remote node management and execution framework for AstrBot.

This module provides a gateway for connecting remote machines (nodes) via
websocket and executing commands, reading files, and managing tasks remotely.
"""

from .components import (
    SpaceshipFileSystemComponent,
    SpaceshipNodeBooter,
    SpaceshipShellComponent,
)
from .dispatcher import TaskDispatcher
from .gateway import SpaceshipGatewayService
from .models import (
    Envelope,
    ListDirToolRequest,
    ReadFileToolRequest,
    SessionConnection,
    ShellToolRequest,
    SpaceshipNode,
    TaskResult,
    TaskSpec,
    WriteFileToolRequest,
)
from .runtime import SpaceshipRuntime
from .session import ActiveSession, SessionHub
from .tool_registry import register_spaceship_tools
from .tools import SpaceshipToolService

__all__ = [
    "ActiveSession",
    "Envelope",
    "ListDirToolRequest",
    "ReadFileToolRequest",
    "SessionConnection",
    "SessionHub",
    "ShellToolRequest",
    "SpaceshipFileSystemComponent",
    "SpaceshipGatewayService",
    "SpaceshipNode",
    "SpaceshipNodeBooter",
    "SpaceshipRuntime",
    "SpaceshipShellComponent",
    "SpaceshipToolService",
    "TaskDispatcher",
    "TaskResult",
    "TaskSpec",
    "WriteFileToolRequest",
    "register_spaceship_tools",
]
