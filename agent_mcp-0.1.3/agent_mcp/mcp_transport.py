"""
MCP Transport Layer - Handles communication between MCP agents.

This module provides the transport layer for the Model Context Protocol (MCP),
enabling agents to communicate over HTTP and SSE.
"""

from abc import ABC, abstractmethod
import asyncio
import json
import aiohttp # Added this line
from typing import Dict, Any, Optional, Callable, AsyncGenerator, Tuple
from aiohttp import web, ClientSession, TCPConnector, ClientTimeout, ClientConnectorError, ClientPayloadError
from fastapi import FastAPI, Request
import uvicorn
from threading import Thread
import traceback
import logging
from collections import deque 
import time
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    """HTTP transport layer for MCP communication.
    
    This class implements the MCPTransport interface using HTTP and SSE for
    communication between agents. It provides:
    
    - HTTP Endpoints: REST API for message exchange
    - SSE Support: Real-time event streaming for continuous updates
    - Connection Management: Handles connection lifecycle and reconnection
    - Message Queueing: Buffers messages for reliable delivery
    - Error Recovery: Robust error handling and automatic retries
    
    The transport can operate in two modes:
    1. Server Mode: Runs a local HTTP server (when is_remote=False)
    2. Client Mode: Connects to remote server (when is_remote=True)
    """
    
    def __init__(self, host: str = "localhost", port: int = 8000, poll_interval: int = 2):
        """
        Initialize the HTTP transport.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            poll_interval: How often to poll the server in seconds
        """
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.app.post("/message")(self._handle_message)
        self.message_queue = asyncio.Queue()
        self.message_handler: Optional[Callable] = None
        self.server_thread = None
        self.is_remote = False
        self.remote_url = None
        self.agent_name = None
        self.token = None
        self.auth_token = None
        self.last_message_id = None  # Track last seen message ID
        self._stop_polling_event = asyncio.Event() # Event to signal polling loop to stop
        self._polling_task = None # To hold the polling task
        self._client_session = None # Shared aiohttp client session
        self._recently_acked_ids = deque(maxlen=500) # Track message IDs
        self._seen_task_ids = deque(maxlen=500) # Track task IDs across polls
        self.poll_interval = poll_interval

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
        transport = cls(poll_interval=2)  # Set default poll interval
        transport.remote_url = url
        transport.is_remote = True
        transport.agent_name = agent_name # Store agent name
        transport.token = token # Store token (might be None initially)
        
        # DO NOT start event stream connection here, wait for start_event_stream() call
            
        return transport
        
    async def _handle_message(self, request: Request):
        """Handle incoming HTTP messages"""
        try:
            message = await request.json()
            # Use None as message_id since this is direct HTTP
            await self.message_queue.put((message, None))
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    async def _ensure_session(self, force_reconnect: bool = False) -> None:
        """Ensure we have a valid client session.
        
        Args:
            force_reconnect: If True, create a new session even if one exists
        """
        if force_reconnect or not self._client_session or self._client_session.closed:
            if self._client_session and not self._client_session.closed:
                await self._client_session.close()
            
            # Create new session with proper headers
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            self._client_session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(verify_ssl=False),
                headers=headers
            )
            logger.info(f"[{self.agent_name}] Created new client session")

    async def _poll_for_messages(self) -> None:
        """Poll for messages from the server.

        This method runs in a loop, polling the server for new messages.
        It handles reconnection and error recovery.
        """
        retry_count = 0
        max_retries = 5
        base_delay = 1.0  # Base delay in seconds
        max_delay = 30.0  # Maximum delay in seconds

        while not self._stop_polling_event.is_set():
            try:
                # Ensure we have a valid session
                await self._ensure_session()
                
                # Create headers with authentication token
                headers = {}
                if self.token:
                    headers["Authorization"] = f"Bearer {self.token}"
                
                # Poll for messages with authentication headers
                async with self._client_session.get(
                    f"{self.remote_url}/messages/{self.agent_name}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"[{self.agent_name}] Raw server response: {json.dumps(data, indent=2)}")
                        
                        # Extract messages from the response body
                        messages = []
                        if isinstance(data, dict):
                            body = data.get('body', '[]')
                            try:
                                messages = json.loads(body)
                                logger.info(f"[{self.agent_name}] Parsed messages from body: {json.dumps(messages, indent=2)}")
                            except json.JSONDecodeError:
                                logger.warning(f"[{self.agent_name}] Failed to parse messages from body: {body}")
                                messages = []
                        
                        if messages:
                            # Sort messages by timestamp before processing
                            messages.sort(key=lambda x: x.get('timestamp', ''))
                            
                            # Clear old messages from the queue to prevent buildup
                            while not self.message_queue.empty():
                                try:
                                    self.message_queue.get_nowait()
                                    self.message_queue.task_done()
                                except asyncio.QueueEmpty:
                                    break

                            logger.info(f"[{self.agent_name}] Processing {len(messages)} messages")
                            for msg in messages:
                                try:
                                    # Validate message format
                                    if not isinstance(msg, dict):
                                        logger.warning(f"[{self.agent_name}] Invalid message format: {msg}")
                                        continue

                                    # Extract message ID and content
                                    message_id = msg.get('id')
                                    message_content = msg.get('content')
                                    
                                    # Skip if we've seen this message before - check BEFORE processing
                                    if message_id in self._seen_task_ids:
                                        logger.debug(f"[{self.agent_name}] Message {message_id} already processed. Skipping.")
                                        continue
                                        
                                    # Add to seen messages BEFORE processing
                                    self._seen_task_ids.append(message_id)
                                    
                                    # Standardize message content format
                                    if isinstance(message_content, str):
                                        message_content = {'text': message_content}
                                        msg['content'] = message_content
                                    elif isinstance(message_content, dict):
                                        if message_content.get('type') == 'task':
                                            # Preserve task structure
                                            pass
                                        elif 'text' not in message_content:
                                            # Wrap non-task dictionaries that don't have a text field
                                            message_content = {'text': json.dumps(message_content)}
                                            msg['content'] = message_content

                                    logger.info(f"[{self.agent_name}] Processing message - ID: {message_id}, Content: {json.dumps(message_content, indent=2)}")
                                    
                                    # Add message to queue for processing
                                    await self.message_queue.put((msg, message_id))
                                    logger.info(f"[{self.agent_name}] Added message to queue: {message_id}")
                                except Exception as e:
                                    logger.error(f"[{self.agent_name}] Error processing message: {e}")
                                    continue
                        else:
                            logger.debug(f"[{self.agent_name}] No new messages")
                    else:
                        logger.warning(f"[{self.agent_name}] Server returned status {response.status}")
                        if response.status == 401:
                            # Authentication error - try to reauthenticate
                            await self._ensure_session(force_reconnect=True)
                        elif response.status >= 500:
                            # Server error - use exponential backoff
                            retry_count += 1
                            if retry_count < max_retries:
                                delay = min(base_delay * (2 ** retry_count), max_delay)
                                logger.warning(f"[{self.agent_name}] Server error, retrying in {delay}s...")
                                await asyncio.sleep(delay)
                                continue

                # Reset retry count on successful poll
                retry_count = 0
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                logger.info(f"[{self.agent_name}] Polling task cancelled")
                break
            except Exception as e:
                logger.error(f"[{self.agent_name}] Error in polling task: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    delay = min(base_delay * (2 ** retry_count), max_delay)
                    logger.warning(f"[{self.agent_name}] Error occurred, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{self.agent_name}] Max retries reached, stopping polling")
                    break

        logger.info(f"[{self.agent_name}] Polling task stopped")

    async def start_polling(self, poll_interval: int = 2):
        """Starts the background message polling task."""
        # Set connection time before polling starts, ensuring we use UTC
        self._connection_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.last_message_id = None # Also reset message tracking here

        if not self.is_remote:
            logger.warning("Polling is only applicable in remote mode. Agent: {self.agent_name}")
            return
            
        if not self.agent_name or not self.auth_token:
            logger.error("Cannot start polling without agent_name and auth_token. Agent: {self.agent_name}")
            raise ValueError("Agent name and authentication token must be set before starting polling.")

        if self._polling_task and not self._polling_task.done():
            logger.info(f"Polling task already running for agent: {self.agent_name}")
            return

        # Ensure stop event is clear before starting
        self._stop_polling_event.clear()

        # Create client session if it doesn't exist or is closed
        if self._client_session is None or self._client_session.closed:
            # Configure timeout (e.g., 30 seconds total timeout)
            timeout = aiohttp.ClientTimeout(total=30)
            # Disable SSL verification if needed (use cautiously)
            connector = aiohttp.TCPConnector(ssl=False) # Or ssl=True for verification
            self._client_session = aiohttp.ClientSession(connector=connector, timeout=timeout)
            logger.debug(f"Created new ClientSession for agent: {self.agent_name}")

        logger.info(f"Starting polling task for agent: {self.agent_name} with interval {poll_interval}s")
        self._polling_task = asyncio.create_task(self._poll_for_messages())
 

    async def connect(self, agent_name: Optional[str] = None, token: Optional[str] = None, poll_interval: int = 2):
        """Connects to the remote server and starts polling for messages.
        
        This method should be called when in remote mode (is_remote=True).
        It sets the agent name and token if provided, and starts the background
        polling task.
        
        Args:
            agent_name: The name of the agent to poll messages for. Overrides existing if provided.
            token: The JWT token for authentication. Overrides existing if provided.
            poll_interval: How often to poll the server in seconds.
        """
        self.last_message_id = None  # Reset message tracking on new connection

        if not self.is_remote:
            logger.warning("connect() called but transport is not in remote mode. Did you mean start()?)")
            return

        if agent_name:
            self.agent_name = agent_name
        if token:
            self.token = token

        if not self.agent_name or not self.token:
            logger.error("Cannot connect: agent_name or token is missing.")
            raise ValueError("Agent name and token must be set before connecting.")
            
        if self._polling_task and not self._polling_task.done():
            logger.warning(f"[{self.agent_name}] connect() called but polling task is already running.")
            return
            
        # Reset the stop event before starting
        self._stop_polling_event.clear()
        
        logger.info(f"[{self.agent_name}] Creating and starting polling task.")
        self._polling_task = asyncio.create_task(self._poll_for_messages(), name=f"poll_messages_{self.agent_name}")
        # Add error handling for task creation?

    async def disconnect(self):
        """Disconnects from the remote server and stops polling for messages.
        
        This method signals the background polling task to stop and waits for it
        to complete.
        """
        if not self.is_remote:
            logger.warning("disconnect() called but transport is not in remote mode. Did you mean stop()?)")
            return
            
        if self._polling_task and not self._polling_task.done():
            logger.info(f"[{self.agent_name}] Signaling polling task to stop.")
            self._stop_polling_event.set()
            try:
                # Wait for the task to finish gracefully
                await asyncio.wait_for(self._polling_task, timeout=10.0) 
                logger.info(f"[{self.agent_name}] Polling task finished gracefully.")
            except asyncio.TimeoutError:
                logger.warning(f"[{self.agent_name}] Polling task did not finish in time, cancelling.")
                self._polling_task.cancel()
                try:
                    await self._polling_task # Await cancellation
                except asyncio.CancelledError:
                     logger.info(f"[{self.agent_name}] Polling task successfully cancelled.")
            except Exception as e:
                 logger.error(f"[{self.agent_name}] Error occurred while waiting for polling task: {e}")
            finally:
                self._polling_task = None # Clear the task reference
        else:
            logger.info(f"[{self.agent_name}] disconnect() called but no active polling task found.")
        
        # Ensure session is explicitly closed here *after* the polling task has stopped
        if self._client_session and not self._client_session.closed:
            logger.info(f"[{self.agent_name}] Closing client session in disconnect.")
            await self._client_session.close()
            self._client_session = None
        else:
            logger.debug(f"[{self.agent_name}] Client session already closed or None in disconnect.")

    # --- Message Sending ---
    async def send_message(self, target: str, message: Dict[str, Any]):
        """Send a message to another agent."""
        try:
            # Ensure message has proper structure
            if isinstance(message, dict) and 'content' not in message:
                message = {
                    "type": message.get("type", "message"),
                    "content": message,
                    "reply_to": message.get("reply_to", f"{self.remote_url}/message/{self.agent_name}")
                }
            
            # Create a ClientSession with optimized settings
            timeout = aiohttp.ClientTimeout(total=55)  # 55s timeout (Cloud Run's limit is 60s)
            async with ClientSession(
                connector=TCPConnector(verify_ssl=False),
                timeout=timeout
            ) as session:
                try:
                    # --- FIX: Parse target if it looks like a full URL ---
                    parsed_target = target
                    if "://" in target:
                        try:
                            # Extract the last part of the path as the agent name
                            parsed_target = target.split('/')[-1]
                            if not parsed_target: # Handle trailing slash case
                                parsed_target = target.split('/')[-2]
                            logger.info(f"[{self.agent_name}] Parsed target URL '{target}' to agent name '{parsed_target}'")
                        except IndexError:
                            logger.warning(f"[{self.agent_name}] Could not parse agent name from target URL '{target}', using original.")
                            parsed_target = target # Fallback to original if parsing fails
                    
                    # Construct the URL using the potentially parsed target
                    url = f"{self.remote_url}/message/{parsed_target}" 

                    headers = {"Authorization": f"Bearer {self.token}"}
                    logger.info(f"[{self.agent_name}] Sending message to {url} (original target was '{target}')")
                    
                    async with session.post(url, json=message, headers=headers) as response:
                        response_text = await response.text()
                        try:
                            response_data = json.loads(response_text)
                        except json.JSONDecodeError:
                            response_data = {"status": "error", "message": response_text}
                            
                        if response.status != 200:
                            logger.error(f"[{self.agent_name}] Error sending message: {response.status}")
                            logger.error(f"[{self.agent_name}] Response: {response_data}")
                            return {"status": "error", "code": response.status, "message": response_data}
                            
                        logger.info(f"[{self.agent_name}] sent this Message : {response_data}  successfully")
                        
                        # Handle body parsing if present
                        if isinstance(response_data, dict):
                            if 'body' in response_data:
                                try:
                                    # Attempt to parse the body string as JSON
                                    parsed_body = json.loads(response_data['body'])
                                    if isinstance(parsed_body, list):
                                        response_data['body'] = parsed_body
                                        logger.info(f"[{self.agent_name}] Successfully parsed message body as JSON list.")
                                    else:
                                        logger.info(f"[{self.agent_name}] Message body is not a list: {type(parsed_body)}")
                                except json.JSONDecodeError as e:
                                    logger.info(f"[{self.agent_name}] Failed to decode message body as JSON: {e}")
                            
                            # Queue task messages
                            if response_data.get('type') == 'task':
                                message_id = response_data.get('message_id')
                                logger.info(f"[{self.agent_name}] Queueing task message {message_id}")
                                await self.message_queue.put((response_data, message_id))
                            
                        return response_data
                except Exception as e:
                    logger.error(f"[{self.agent_name}] Error sending message: {e}")
                    return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error in send_message: {e}")
            return {"status": "error", "message": str(e)}
                
    async def acknowledge_message(self, target: str, message_id: str):
        """Acknowledge receipt of a message"""
        if not self.is_remote:
            # Return True because there's nothing to acknowledge locally
            logger.debug(f"[{self.agent_name}] No remote server configured. Skipping acknowledgment for message ID: {message_id}")
            return True
            
        if not self.agent_name or not self.token:
            logger.error(f"Cannot acknowledge message: Missing agent name or token")
            return False
            
        ack_url = f"{self.remote_url}/message/{self.agent_name}/acknowledge/{message_id}"
        headers = {"Authorization": f"Bearer {self.token}"}

        logger.info(f"[{self.agent_name}] Attempting to acknowledge message {message_id} to {ack_url}")

        # Check if already recently acknowledged
        if message_id in self._recently_acked_ids:
            logger.debug(f"[{self.agent_name}] Message {message_id} already recently acknowledged. Skipping redundant ack.")
            return True # Treat as success, as it was likely acked before

        if not self._client_session or self._client_session.closed:
            logger.error(f"[{self.agent_name}] Cannot acknowledge message {message_id}: Client session is not available or closed.")
            return False

        try:
            # Use the shared client session
            async with self._client_session.post(ack_url, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"[{self.agent_name}] Successfully acknowledged message {message_id}")
                    self._recently_acked_ids.append(message_id)
                    return True
                else:
                    response_text = await response.text()
                    logger.error(f"[{self.agent_name}] Failed to acknowledge message {message_id}. Status: {response.status}, Response: {response_text}")
                    return False
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error acknowledging message {message_id}: {e}")
            return False

    async def receive_message(self, timeout: float = 5.0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Receive a message fetched by the polling task.

        Waits for a message from the internal queue with a timeout.
        Checks if the polling task is still active.

        Args:
            timeout (float): Maximum time to wait for a message in seconds.

        Returns:
            A tuple containing the message dictionary and its ID, or (None, None)
            if no message is received within the timeout, the polling task
            has stopped, or an error occurs.
        """
        # Check if polling is active before waiting
        if not self._polling_task or self._polling_task.done():
            # If polling task is not running or finished, try to restart it
            logger.warning(f"[{self.agent_name}] Polling task inactive, attempting to restart...")
            try:
                await self.start_polling()
                # Wait a bit for polling to start
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"[{self.agent_name}] Failed to restart polling: {e}")
                return None, None

        try:
            # Wait for a message from the queue with a timeout
            if timeout > 0:
                logger.info(f"[{self.agent_name}] Waiting for message from queue (timeout={timeout}s)...")
                try:
                    message, message_id = await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
                    logger.info(f"[{self.agent_name}] Received message from queue: {json.dumps(message, indent=2)}")
                except asyncio.TimeoutError:
                    logger.info(f"[{self.agent_name}] Timeout waiting for message. Returning None.")
                    return None, None
            else:
                # Non-blocking get if timeout is 0
                try:
                    message, message_id = self.message_queue.get_nowait()
                except asyncio.QueueEmpty:
                    logger.info(f"[{self.agent_name}] Queue empty on get_nowait. Returning None.")
                    return None, None

            # Validate message before returning
            if message and isinstance(message, dict):
                # More lenient validation - only check for essential fields
                if 'content' in message or 'text' in message or 'description' in message:
                    logger.info(f"[{self.agent_name}] Message validation passed, returning message with ID: {message_id}")
                    # Mark task done *after* successful retrieval and validation
                    self.message_queue.task_done()
                    # Acknowledge the message after successfully receiving it
                    if message.get('from') and message_id:
                        await self.acknowledge_message(message.get('from'), message_id)
                    return message, message_id
                else:
                    logger.warning(f"[{self.agent_name}] Message missing required 'content' field. Message: {message}")
            else:
                logger.warning(f"[{self.agent_name}] Invalid message format. Message: {message}")

            # Mark task as done even if validation failed
            self.message_queue.task_done()
            return None, None

        except asyncio.CancelledError:
            logger.info(f"[{self.agent_name}] receive_message task cancelled.")
            raise
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error receiving message: {e}")
            traceback.print_exc()
            try:
                self.message_queue.task_done()
            except ValueError:
                pass
            except Exception as inner_e:
                logger.error(f"[{self.agent_name}] Error calling task_done in exception handler: {inner_e}")
            return None, None

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
        """Starts the local HTTP server (if not in remote mode).
        
        This method initializes and starts a local HTTP server for handling agent
        communication when operating in local mode. In remote mode, use connect()
        instead.
        
        The server runs in a separate daemon thread to avoid blocking the main
        application thread.
        """
        # Skip starting local server if we're in remote mode
        if hasattr(self, 'is_remote') and self.is_remote:
            logger.info(f"[{self.agent_name or 'Unknown'}] In remote mode. Call connect() to start polling.")
            return
            
        def run_server():
            uvicorn.run(self.app, host=self.host, port=self.port)
            
        self.server_thread = Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
    async def stop(self):
        """Stops the local HTTP server (if running).
        
        This method gracefully shuts down the local HTTP server when operating in
        local mode. For remote connections, use disconnect() instead.
        
        The method ensures proper cleanup of server resources and thread termination.
        """
        if self.is_remote:
            logger.info(f"[{self.agent_name or 'Unknown'}] In remote mode. Call disconnect() to stop polling.")
            return 
        # Close client session if exists
        if hasattr(self, '_client_session') and self._client_session:
            await self._client_session.close()
            self._client_session = None
    
        elif self.server_thread:
            logger.info(f"Stopping local server thread (implementation pending)...")
            self.server_thread = None  # Important for GC

        
    def set_message_handler(self, handler: Callable):
        """Set a handler for incoming messages.
        
        This method registers a callback function to process incoming messages.
        The handler will be called for each message received by the transport.
        
        Args:
            handler: Function to handle incoming messages. Should accept a message
                    dictionary as its argument.
        """
        self.message_handler = handler
        
    async def register_agent(self, agent) -> Dict[str, Any]:
        """Register an agent with the remote server.
        
        This method registers an agent with the remote MCP server, providing the
        server with information about the agent's capabilities and configuration.
        
        Args:
            agent: The MCPAgent instance to register
            
        Returns:
            Dict containing the server's response
            
        Raises:
            ValueError: If called in local mode
            ClientError: If there are network or connection issues
        """
        if not hasattr(self, 'is_remote') or not self.is_remote:
            raise ValueError("register_agent can only be used with remote servers")
            
        # Create a ClientSession with SSL verification disabled
        async with ClientSession(
            connector=TCPConnector(verify_ssl=False)
        ) as session:
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
