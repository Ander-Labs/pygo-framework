"""PyGo WebSocket System (v0.33.0).

Provides WebSocket server, client, channels, and pub/sub.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, Callable, List, Set
from dataclasses import dataclass, field
import asyncio
import json
import uuid
from enum import Enum
from collections import defaultdict


class MessageType(Enum):
    """WebSocket message types."""
    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"


@dataclass
class Message:
    """Represents a WebSocket message."""
    type: str
    data: Any
    channel: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class PubSub:
    """Publish/Subscribe system for channels."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, channel: str, callback: Callable) -> Callable:
        """Subscribe to a channel."""
        self._subscribers[channel].append(callback)
        
        # Return unsubscribe function
        def unsubscribe():
            if callback in self._subscribers[channel]:
                self._subscribers[channel].remove(callback)
        
        return unsubscribe
    
    def publish(self, channel: str, data: Any) -> None:
        """Publish data to a channel."""
        message = Message(type="publish", data=data, channel=channel)
        
        for callback in self._subscribers[channel]:
            try:
                callback(message)
            except Exception as e:
                print(f"PubSub error in callback: {e}")


class Channel:
    """Represents a WebSocket channel."""
    
    def __init__(self, name: str):
        self.name = name
        self.subscribers: List[Callable] = []
        self.messages: List[Message] = []
    
    def subscribe(self, callback: Callable) -> None:
        """Subscribe a callback to messages."""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """Unsubscribe a callback."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def broadcast(self, data: Any) -> None:
        """Broadcast data to all subscribers."""
        message = Message(type="broadcast", data=data, channel=self.name)
        self.messages.append(message)
        
        for callback in self.subscribers:
            try:
                callback(message)
            except Exception as e:
                print(f"Channel broadcast error: {e}")


class WebSocketServer:
    """WebSocket server implementation."""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self._connections: Dict[str, Any] = {}  # connection_id -> connection
        self._channels: Dict[str, Channel] = {}
        self._pubsub = PubSub()
        self._running = False
    
    def create_channel(self, name: str) -> Channel:
        """Create a new channel."""
        channel = Channel(name)
        self._channels[name] = channel
        return channel
    
    def get_channel(self, name: str) -> Optional[Channel]:
        """Get a channel by name."""
        return self._channels.get(name)
    
    def subscribe(self, channel: str, callback: Callable) -> None:
        """Subscribe to a channel."""
        self._pubsub.subscribe(channel, callback)
    
    def publish(self, channel: str, data: Any) -> None:
        """Publish to a channel."""
        self._pubsub.publish(channel, data)
    
    def broadcast(self, channel: str, data: Any) -> None:
        """Broadcast to a channel."""
        ch = self.get_channel(channel)
        if ch:
            ch.broadcast(data)


class WebSocketClient:
    """WebSocket client implementation (placeholder for future async support)."""
    
    def __init__(self, url: str, token: Optional[str] = None):
        self.url = url
        self.token = token
        self._connected = False
        self._channels: Dict[str, Channel] = {}
    
    def connect(self) -> bool:
        """Connect to the WebSocket server."""
        # Placeholder - real implementation would use websockets library
        self._connected = True
        return True
    
    def disconnect(self) -> None:
        """Disconnect from the server."""
        self._connected = False
    
    def send(self, channel: str, data: Any) -> None:
        """Send data to a channel."""
        if not self._connected:
            raise ConnectionError("Not connected")
        
        # Placeholder - would send via WebSocket
        print(f"[WS] Sending to {channel}: {data}")
    
    def on(self, channel: str, callback: Callable) -> None:
        """Register a callback for a channel."""
        if channel not in self._channels:
            self._channels[channel] = Channel(channel)
        self._channels[channel].subscribe(callback)
    
    def emit(self, channel: str, data: Any) -> None:
        """Emit data to a channel locally."""
        if channel in self._channels:
            self._channels[channel].broadcast(data)
        else:
            self._channels[channel] = Channel(channel)
            self._channels[channel].broadcast(data)


# Convenience functions
def create_server(host: str = "localhost", port: int = 8765) -> WebSocketServer:
    """Create a WebSocket server."""
    return WebSocketServer(host, port)


def create_client(url: str, token: Optional[str] = None) -> WebSocketClient:
    """Create a WebSocket client."""
    return WebSocketClient(url, token)