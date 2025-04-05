"""
MCP Transport Layer - Handles communication between MCP agents.

This module provides the transport layer for the Model Context Protocol (MCP),
enabling agents to communicate over HTTP and SSE.
"""

from abc import ABC, abstractmethod
import asyncio
import json
from typing import Dict, Any, Optional, Callable, AsyncGenerator
from aiohttp import web, ClientSession
from sse_starlette.sse import EventSourceResponse
from fastapi import FastAPI, Request
import uvicorn
from threading import Thread

class MCPTransport(ABC):
    """Base transport layer for MCP communication"""
    
    @abstractmethod
    async def send_message(self, target: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message to another agent"""
        pass
    
    @abstractmethod
    async def receive_message(self) -> Dict[str, Any]:
        """Receive a message from another agent"""
        pass

class HTTPTransport(MCPTransport):
    """
    HTTP transport layer for MCP communication.
    
    This class provides HTTP and SSE-based communication between MCP agents,
    handling message sending and receiving.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        """
        Initialize the HTTP transport.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.app.post("/message")(self._handle_message)
        self.app.get("/events")(self.event_stream)
        self.message_queue = asyncio.Queue()
        self.message_handler: Optional[Callable] = None
        self.server_thread = None
        
    def get_url(self) -> str:
        """Get the URL for this transport"""
        return f"http://{self.host}:{self.port}"
        
    async def _handle_message(self, request: Request):
        """Handle incoming HTTP messages"""
        try:
            message = await request.json()
            await self.message_queue.put(message)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    async def event_stream(self, request: Request):
        """SSE event stream endpoint"""
        async def event_generator():
            while True:
                message = await self.message_queue.get()
                if isinstance(message, dict):
                    yield {"data": json.dumps(message)}
                else:
                    yield {"data": str(message)}
        
        return EventSourceResponse(event_generator())
    
    async def send_message(self, target: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message to another agent.
        
        Args:
            target: URL of the recipient agent
            message: Message to send
        """
        async with ClientSession() as session:
            try:
                async with session.post(
                    f"{target}/message",
                    json=message
                ) as response:
                    return await response.json()
            except Exception as e:
                print(f"Error sending message: {e}")
                return {"status": "error", "message": str(e)}
                
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """
        Receive a message from the queue.
        
        Returns:
            The received message, or None if no message is available
        """
        try:
            return await self.message_queue.get()
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None
            
    def start(self):
        """Start the transport server in a separate thread"""
        def run_server():
            uvicorn.run(self.app, host=self.host, port=self.port)
            
        self.server_thread = Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
    def stop(self):
        """Stop the transport server"""
        if self.server_thread:
            # Implement proper shutdown
            pass
            
    def set_message_handler(self, handler: Callable):
        """
        Set a handler for incoming messages.
        
        Args:
            handler: Function to handle incoming messages
        """
        self.message_handler = handler
