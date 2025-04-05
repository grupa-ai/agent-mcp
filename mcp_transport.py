"""
Transport layer for MCP communication supporting HTTP and SSE.
"""

from abc import ABC, abstractmethod
import asyncio
import json
import aiohttp
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
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
    """HTTP/SSE based transport"""
    def __init__(self, host: str, port: int):
        self.app = FastAPI()
        self.message_queue = asyncio.Queue()
        self.host = host
        self.port = port
        self.server_thread = None
        
        # Setup routes
        self.app.post("/message")(self.handle_message)
        self.app.get("/events")(self.event_stream)
    
    async def handle_message(self, request: Request):
        """Handle incoming HTTP messages"""
        message = await request.json()
        await self.message_queue.put(message)
        return {"status": "ok"}
    
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
        """Send message via HTTP POST"""
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{target}/message", json=message) as response:
                return await response.json()
    
    async def receive_message(self) -> Dict[str, Any]:
        """Receive message from queue"""
        return await self.message_queue.get()
    
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
