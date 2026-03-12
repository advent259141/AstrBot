"""Temporary token management for HTTP file transfers."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from secrets import token_urlsafe
from typing import Literal


_TOKEN_TTL_SEC = 300  # 5 minutes

TransferDirection = Literal["download", "upload"]


@dataclass(slots=True)
class TransferTicket:
    """A one-time-use ticket authorising a file transfer."""

    token: str
    direction: TransferDirection
    file_path: str
    node_id: str
    created_at: float


@dataclass(slots=True)
class FileTransferService:
    """Manages temporary tokens for HTTP file transfers between AstrBot and nodes."""

    _tickets: dict[str, TransferTicket] = field(default_factory=dict)

    # -- public API ----------------------------------------------------------

    def create_download_ticket(self, file_path: str, node_id: str) -> str:
        """Create a token that allows a node to download a file from AstrBot.

        Used in the 'upload to node' flow:
        AstrBot has a local file → node will HTTP GET it.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"local file not found: {file_path}")
        token = token_urlsafe(32)
        self._tickets[token] = TransferTicket(
            token=token,
            direction="download",
            file_path=os.path.abspath(file_path),
            node_id=node_id,
            created_at=time.time(),
        )
        return token

    def create_upload_ticket(self, save_path: str, node_id: str) -> str:
        """Create a token that allows a node to upload a file to AstrBot.

        Used in the 'download from node' flow:
        Node has a remote file → node will HTTP POST it to AstrBot.
        """
        # Ensure the target directory exists.
        parent = os.path.dirname(os.path.abspath(save_path))
        os.makedirs(parent, exist_ok=True)
        token = token_urlsafe(32)
        self._tickets[token] = TransferTicket(
            token=token,
            direction="upload",
            file_path=os.path.abspath(save_path),
            node_id=node_id,
            created_at=time.time(),
        )
        return token

    def consume_download_ticket(self, token: str) -> str | None:
        """Consume a download ticket and return the file path, or None if invalid."""
        self._purge_expired()
        ticket = self._tickets.pop(token, None)
        if ticket is None or ticket.direction != "download":
            return None
        return ticket.file_path

    def consume_upload_ticket(self, token: str) -> str | None:
        """Consume an upload ticket and return the save path, or None if invalid."""
        self._purge_expired()
        ticket = self._tickets.pop(token, None)
        if ticket is None or ticket.direction != "upload":
            return None
        return ticket.file_path

    # -- internal -------------------------------------------------------------

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [
            t for t, ticket in self._tickets.items()
            if now - ticket.created_at > _TOKEN_TTL_SEC
        ]
        for t in expired:
            del self._tickets[t]
