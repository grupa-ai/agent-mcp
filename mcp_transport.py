"""
MCP Transport Layer - Handles communication between MCP agents.

This module provides the transport layer for the Model Context Protocol (MCP),
enabling agents to communicate over HTTP and SSE.
"""

from abc import ABC, abstractmethod
import asyncio
import json
from typing import Dict, Any, Optional, Callable, AsyncGenerator, Tuple
from aiohttp import web, ClientSession, TCPConnector, ClientTimeout, ClientConnectorError
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
    async def receive_message(self) -> Tuple[Dict[str, Any], str]:
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
        self.is_remote = False
        self.remote_url = None
        
    def get_url(self) -> str:
        """Get the URL for this transport"""
        if hasattr(self, 'is_remote') and self.is_remote:
            return self.remote_url
        return f"http://{self.host}:{self.port}"
        
    @classmethod
    def from_url(cls, url: str, agent_name: Optional[str] = None, token: Optional[str] = None) -> 'HTTPTransport':
        """Create a transport instance from a URL.
        
        Args:
            url: The URL to connect to (e.g., 'https://mcp-server-ixlfhxquwq-ew.a.run.app')
            agent_name: The name of the agent this transport is for (used for event stream)
            token: The JWT token for authenticating the event stream connection (can be set later)
            
        Returns:
            An HTTPTransport instance configured for the URL
        """
        # For remote URLs, we don't need to start a local server
        transport = cls()
        transport.remote_url = url
        transport.is_remote = True
        transport.agent_name = agent_name # Store agent name
        transport.token = token # Store token (might be None initially)
        
        # DO NOT start event stream connection here, wait for start_event_stream() call
            
        return transport
        
    def start_event_stream(self):
        """Starts the background task to connect to the agent-specific event stream."""
        if not (self.is_remote and self.agent_name):
            print(f"[{self.agent_name or 'Unknown'}] Cannot start event stream: Not configured for remote or agent_name missing.")
            return

        async def connect_event_stream():
            event_url = f"{self.remote_url}/events/{self.agent_name}"
            headers = {}
            last_message_id = None
            
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            else:
                print(f"[{self.agent_name}] Warning: Starting event stream connection WITHOUT token.")
                
            print(f"[{self.agent_name}] Starting long polling: {event_url}")
            await asyncio.sleep(0.1)
            
            try: # Wrap the whole connection attempt
                while True:
                    try:
                        params = {}
                        if last_message_id:
                            params["last_message_id"] = last_message_id
                            
                        # Use a longer timeout for SSE connections
                        async with ClientSession(
                            connector=TCPConnector(verify_ssl=False),
                            timeout=ClientTimeout(total=600)  # 10 minute timeout to match server
                        ) as session:
                            async with session.get(event_url, headers=headers, params=params) as response:
                                print(f"[{self.agent_name}] Event stream connection status: {response.status}")
                                
                                if response.status != 200:
                                    error_text = await response.text()
                                    print(f"[{self.agent_name}] Error connecting to event stream: {response.status}, Response: {error_text}")
                                    await asyncio.sleep(1)  # Short delay before retry
                                    continue

                                # Process the event stream
                                async for line in response.content:
                                    raw_line = line.decode('utf-8', errors='ignore').strip() # Decode safely
                                    print(f"[{self.agent_name}] Raw SSE line received: '{raw_line}'") # Log raw line

                                    # Handle keep-alive messages
                                    if raw_line.startswith(':'):
                                        print(f"[{self.agent_name}] Received keep-alive")
                                        continue

                                    if raw_line.startswith('data: '):
                                        json_payload = raw_line[len('data: '):].strip() # Skip 'data: ' prefix
                                        print(f"[{self.agent_name}] Attempting to parse JSON: '{json_payload}'") # Log JSON part
                                        try:
                                            data = json.loads(json_payload)
                                            messages = data.get('messages', [])
                                            last_message_id = data.get('last_message_id')
                                            print(f"[{self.agent_name}] Parsed data: messages={len(messages)}, last_id={last_message_id}") # Log parsed data summary

                                            for message in messages:
                                                msg_id = message.get('id')
                                                print(f"[{self.agent_name}] Processing message {msg_id} from event stream") # Log message processing
                                                # Put both message and ID in queue
                                                print(f"[{self.agent_name}] Putting message {msg_id} onto internal queue.") # Log before putting
                                                await self.message_queue.put((message, msg_id))
                                                print(f"[{self.agent_name}] Successfully put message {msg_id} onto internal queue.") # Log after putting

                                        except json.JSONDecodeError as e:
                                            print(f"[{self.agent_name}] Error decoding JSON: {e}, Payload: '{json_payload}'")
                                            continue
                                        except Exception as e: # Catch other potential parsing errors
                                            print(f"[{self.agent_name}] Error processing parsed data: {e}, Data: {data}")
                                            continue
                                    elif raw_line: # Log any other non-empty lines
                                        print(f"[{self.agent_name}] Received unexpected non-empty line: '{raw_line}'")

                                # If the loop finishes without error, connection closed by server
                                print(f"[{self.agent_name}] Event stream connection closed gracefully by server.")

                    except asyncio.TimeoutError:
                        print(f"[{self.agent_name}] Event stream connection timed out after {session.timeout.total} seconds.")
                        # Decide whether to retry or break, here we just wait before the main loop retry
                        await asyncio.sleep(5)
                        continue # Retry connection

                    except ClientConnectorError as e:
                        print(f"[{self.agent_name}] Event stream connection failed: {e}")
                        await asyncio.sleep(5) # Wait before retrying connection
                        continue # Retry connection
                    except asyncio.CancelledError:
                        print(f"[{self.agent_name}] Event stream connection cancelled.")
                        break
                    except Exception as e:
                        print(f"[{self.agent_name}] Long polling error: {e}")
                        await asyncio.sleep(5)  # Wait before retrying
            except Exception as e:
                print(f"[{self.agent_name}] Error during event stream connection/processing: {e}")
                await asyncio.sleep(5)  # Wait before retrying
                # Create a new task to retry the connection
                asyncio.create_task(connect_event_stream())
            finally:
                print(f"[{self.agent_name}] Exiting connect_event_stream task.")
        
        # Start event stream in background
        print(f"[{self.agent_name}] Creating event stream task.")
        asyncio.create_task(connect_event_stream(), name=f"event_stream_{self.agent_name}")

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
            target: URL or name of the recipient agent
            message: Message to send
        """
        # Create a ClientSession with SSL verification disabled
        async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
            try:
                # Use target URL as is since it's already complete
                url = target
                print(f"Sending message to URL: {url}")
                    
                async with session.post(url, json=message) as response:
                    data = await response.json()
                    if isinstance(data, dict) and 'body' in data:
                        # Parse the body content which is a JSON string
                        return json.loads(data['body'])
                    return data
            except Exception as e:
                print(f"Error sending message: {e}")
                return {"status": "error", "message": str(e)}
                
    async def acknowledge_message(self, target: str, message_id: str):
        """Acknowledge receipt of a message"""
        if not self.is_remote:
            return
            
        ack_url = f"{self.remote_url}/message/{target}/ack"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        async with ClientSession() as session:
            async with session.post(ack_url, json={"message_id": message_id}, headers=headers) as response:
                if response.status != 200:
                    print(f"Error acknowledging message {message_id}: {response.status}")
                    return False
                return True

    async def receive_message(self) -> Tuple[Dict[str, Any], str]:
        """Receive a message from another agent"""
        if not self.message_queue:
            raise RuntimeError("Transport not initialized")
            
        message, message_id = await self.message_queue.get()
        if message_id:  # Only acknowledge if we have an ID
            await self.acknowledge_message(self.agent_name, message_id)
        return message, message_id

    # Legacy method - replaced by new acknowledge_message with target parameter
    async def _legacy_acknowledge_message(self, message_id: str):
        """Legacy method to acknowledge a message"""
        if not self.remote_url or not self.agent_name or not self.token:
            print(f"[{self.agent_name}] Cannot acknowledge message: Missing remote URL, agent name, or token.")
            return

        ack_url = f"{self.remote_url}/message/{self.agent_name}/ack"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"message_id": message_id}

        print(f"[{self.agent_name}] Acknowledging message {message_id} to {ack_url}")
        try:
            # Use a new session for acknowledgement
            async with ClientSession(
                connector=TCPConnector(verify_ssl=False), # Adjust SSL verification as needed
                timeout=ClientTimeout(total=10) # Add a reasonable timeout
            ) as session:
                async with session.post(ack_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        print(f"[{self.agent_name}] Successfully acknowledged message {message_id}.")
                    else:
                        print(f"[{self.agent_name}] Failed to acknowledge message {message_id}. Status: {response.status}, Response: {await response.text()}")
        except Exception as e:
            print(f"[{self.agent_name}] Error acknowledging message {message_id}: {e}")

    def start(self):
        """Start the transport server in a separate thread"""
        # Skip starting local server if we're in remote mode
        if hasattr(self, 'is_remote') and self.is_remote:
            return
            
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
        
    async def register_agent(self, agent) -> Dict[str, Any]:
        """
        Register an agent with the remote server.
        
        Args:
            agent: The MCPAgent instance to register
            
        Returns:
            The server's response
        """
        if not hasattr(self, 'is_remote') or not self.is_remote:
            raise ValueError("register_agent can only be used with remote servers")
            
        # Create a ClientSession with SSL verification disabled
        async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
            try:
                registration_data = {
                    "agent_id": agent.name,  
                    "info": {  
                        "name": agent.name,
                        "system_message": agent.system_message if hasattr(agent, 'system_message') else "",
                        "capabilities": agent.capabilities if hasattr(agent, 'capabilities') else []
                    }
                }
                
                async with session.post(
                    f"{self.remote_url}/register",
                    json=registration_data
                ) as response:
                    return await response.json()
            except Exception as e:
                print(f"Error registering agent: {e}")
                return {"status": "error", "message": str(e)}
