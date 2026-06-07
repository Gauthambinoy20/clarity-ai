"""
WebSocket connection manager for ClarityAI.

Provides real-time streaming of analysis results and progress updates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time streaming.

    Features:
    - Per-client connections (keyed by an optional client_id or WebSocket identity)
    - Room/channel support for grouping related connections
    - Broadcast, targeted send, and progress update methods
    """

    def __init__(self) -> None:
        # All active connections
        self._active_connections: List[WebSocket] = []
        # Connections grouped by channel/room
        self._channels: Dict[str, Set[WebSocket]] = {}
        # Map WebSocket to client_id for targeted sends
        self._client_map: Dict[str, WebSocket] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        client_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> None:
        """Accept a WebSocket connection and register it."""
        await websocket.accept()
        self._active_connections.append(websocket)

        if client_id:
            self._client_map[client_id] = websocket

        if channel:
            if channel not in self._channels:
                self._channels[channel] = set()
            self._channels[channel].add(websocket)

        logger.info(
            "WebSocket connected: client_id=%s channel=%s (total=%d)",
            client_id,
            channel,
            len(self._active_connections),
        )

    def disconnect(
        self,
        websocket: WebSocket,
        client_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> None:
        """Remove a WebSocket connection from all registries."""
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

        if client_id and client_id in self._client_map:
            del self._client_map[client_id]

        if channel and channel in self._channels:
            self._channels[channel].discard(websocket)
            if not self._channels[channel]:
                del self._channels[channel]

        # Also clean up from all channels if channel not specified
        if not channel:
            for ch_name in list(self._channels.keys()):
                self._channels[ch_name].discard(websocket)
                if not self._channels[ch_name]:
                    del self._channels[ch_name]

        logger.info(
            "WebSocket disconnected: client_id=%s (remaining=%d)",
            client_id,
            len(self._active_connections),
        )

    # ------------------------------------------------------------------
    # Send methods
    # ------------------------------------------------------------------

    async def send_json(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Send a JSON message to a specific WebSocket."""
        try:
            await websocket.send_json(data)
        except Exception as exc:
            logger.warning("Failed to send JSON to WebSocket: %s", exc)

    async def send_to_client(self, client_id: str, data: Dict[str, Any]) -> bool:
        """Send a JSON message to a specific client by ID. Returns True if sent."""
        ws = self._client_map.get(client_id)
        if ws is None:
            logger.warning("Client %s not found", client_id)
            return False
        await self.send_json(ws, data)
        return True

    async def broadcast(self, data: Dict[str, Any]) -> None:
        """Broadcast a JSON message to ALL connected clients."""
        disconnected: List[WebSocket] = []
        for ws in self._active_connections:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)

        # Clean up broken connections
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_to_channel(self, channel: str, data: Dict[str, Any]) -> None:
        """Broadcast a JSON message to all clients in a specific channel."""
        connections = self._channels.get(channel, set())
        disconnected: List[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws, channel=channel)

    # ------------------------------------------------------------------
    # Convenience methods for analysis streaming
    # ------------------------------------------------------------------

    async def send_signal_result(
        self,
        client_id: str,
        signal_name: str,
        result: Dict[str, Any],
    ) -> None:
        """Stream a single signal's result as it completes during detection."""
        await self.send_to_client(
            client_id,
            {
                "type": "signal_result",
                "signal": signal_name,
                "data": result,
            },
        )

    async def send_progress(
        self,
        client_id: str,
        current_step: int,
        total_steps: int,
        message: str = "",
    ) -> None:
        """Send a progress update (e.g., during humanization iterations)."""
        progress = round(current_step / total_steps * 100, 1) if total_steps > 0 else 0
        await self.send_to_client(
            client_id,
            {
                "type": "progress",
                "current_step": current_step,
                "total_steps": total_steps,
                "progress_percent": progress,
                "message": message,
            },
        )

    async def send_completion(
        self,
        client_id: str,
        analysis_id: str,
        result: Dict[str, Any],
    ) -> None:
        """Send a completion message when an analysis finishes."""
        await self.send_to_client(
            client_id,
            {
                "type": "complete",
                "analysis_id": analysis_id,
                "data": result,
            },
        )

    async def send_error(self, client_id: str, error_message: str) -> None:
        """Send an error message to a specific client."""
        await self.send_to_client(
            client_id,
            {
                "type": "error",
                "message": error_message,
            },
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_connection_count(self) -> int:
        return len(self._active_connections)

    @property
    def channels(self) -> List[str]:
        return list(self._channels.keys())


# ---------------------------------------------------------------------------
# Singleton manager instance
# ---------------------------------------------------------------------------

manager = ConnectionManager()
