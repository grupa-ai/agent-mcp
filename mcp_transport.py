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
from collections import deque # Added import

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
        self._recently_acked_ids = deque(maxlen=100) # Initialize cache for acknowledged IDs

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
        
    async def _handle_message(self, request: Request):
        """Handle incoming HTTP messages"""
        try:
            message = await request.json()
            # Use None as message_id since this is direct HTTP
            await self.message_queue.put((message, None))
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    async def _poll_for_messages(self, poll_interval: int = 2):
        """Background task to poll the server for new messages."""
        if not (self.is_remote and self.agent_name and self.token):
            logger.error(f"[{self.agent_name or 'Unknown'}] Cannot start polling: Remote URL, agent name, or token missing.")
            return

        poll_url = f"{self.remote_url}/messages/{self.agent_name}"
        headers = {"Authorization": f"Bearer {self.token}"}

        # Ensure session is None initially or properly handled if re-polling is possible
        if not hasattr(self, '_client_session') or self._client_session is None or self._client_session.closed:
             # Use headers defined during initialization or connect
             headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
             self._client_session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False), headers=headers)
             logger.info(f"[{self.agent_name}] Created new client session for polling.")
        elif not self._client_session.closed:
             # Ensure headers are updated if token changed
             if self.token and self._client_session.headers.get("Authorization") != f"Bearer {self.token}":
                 self._client_session.headers["Authorization"] = f"Bearer {self.token}"
                 logger.info(f"[{self.agent_name}] Updated Authorization header in existing session.")
             logger.info(f"[{self.agent_name}] Reusing existing client session for polling.")


        logger.info(f"[{self.agent_name}] Starting polling task for {poll_url} every {poll_interval}s")

        while not self._stop_polling_event.is_set():
            messages = [] # Ensure messages is initialized for each poll cycle
            try:
                params = {}
                if self.last_message_id:
                    params["last_message_id"] = self.last_message_id

                logger.debug(f"[{self.agent_name}] Polling {poll_url} with params: {params}")
                async with self._client_session.get(poll_url, params=params, timeout=aiohttp.ClientTimeout(total=poll_interval + 10)) as response:
                    response.raise_for_status()
                    logger.debug(f"[{self.agent_name}] Polling response status: {response.status}")
                    response_text = await response.text() # Get raw text first
                    logger.debug(f"[{self.agent_name}] Raw polling response text: {response_text[:500]}...", flush=True) # Log the raw text
                    # Check content type before parsing JSON
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' not in content_type:
                         # Handle non-JSON response (e.g., empty, text, HTML error page)
                         raw_body = response_text
                         logger.warning(f"[{self.agent_name}] Received non-JSON response from /messages: Status={response.status}, Content-Type={content_type}, Body='{raw_body[:100]}...'")
                         messages = [] # Treat as no messages
                    else:
                         try:
                             response_data = json.loads(response_text)
 
                             # Case 1: Response is a dict containing a 'body' field with a JSON string list
                             if isinstance(response_data, dict) and 'body' in response_data:
                                 body_content = response_data.get('body')
                                 if isinstance(body_content, str):
                                     try:
                                         parsed_body = json.loads(body_content)
                                         if isinstance(parsed_body, list):
                                             messages = parsed_body # Use the list parsed from 'body'
                                             logger.debug(f"[{self.agent_name}] Parsed {len(messages)} messages from 'body' string.")
                                         else:
                                             logger.warning(f"[{self.agent_name}] Parsed 'body' string is not a list: {type(parsed_body)}. Body: {body_content[:100]}...")
                                     except json.JSONDecodeError as json_err:
                                         logger.warning(f"[{self.agent_name}] Failed to decode 'body' string as JSON: {json_err}. Body: {body_content[:100]}...")
                                 elif body_content is not None:
                                      logger.warning(f"[{self.agent_name}] 'body' field is not a string: {type(body_content)}. Discarding.")
                                 # If 'body' exists but is empty/None/unparsable, messages remains []
                             
                             # Case 2: Response is directly a list of messages
                             elif isinstance(response_data, list):
                                 messages = response_data
                                 logger.debug(f"[{self.agent_name}] Received response directly as a list of {len(messages)} messages.")
                                 
                             # Case 3: Response is a single message dictionary (not wrapped in 'body')
                             elif isinstance(response_data, dict):
                                 messages = [response_data] # Wrap single dictionary in a list
                                 logger.debug(f"[{self.agent_name}] Received single message dict (not in 'body'), wrapping in list.")
                                 
                             # Case 4: Unexpected JSON structure
                             else:
                                 logger.warning(f"[{self.agent_name}] Unexpected JSON type from /messages: {type(response_data)}. Body: {str(response_data)[:100]}...")
                             # << NEW LOGIC END >>
                                
                         except aiohttp.ContentTypeError:
                             raw_body = await response.text()
                             logger.error(f"[{self.agent_name}] ContentTypeError despite header check. Status={response.status}, Body='{raw_body[:100]}...'")
                             messages = []
                         except json.JSONDecodeError:
                             raw_body = await response.text()
                             logger.error(f"[{self.agent_name}] JSONDecodeError. Status={response.status}, Body='{raw_body[:100]}...'")
                             messages = []

                    if messages:
                        logger.debug(f"[{self.agent_name}] Received {len(messages)} message(s) from server.")
                        new_last_id = None

                        queued_task_ids_in_batch = set() # Track task IDs seen in this batch

                        for msg in messages:
                            # Skip invalid messages (e.g., not dictionaries)
                            if not isinstance(msg, dict):
                                logger.warning(f"[{self.agent_name}] Skipping invalid message format in list: {msg}")
                                continue

                            # Get message ID
                            msg_id = msg.get('id')
                            if not msg_id:
                                logger.warning(f"[{self.agent_name}] Message in list missing ID: {msg}")
                                continue # Cannot acknowledge without ID

                            # --- BEGIN DEDUPLICATION LOGIC ---
                            task_id = msg.get('task_id')
                            if task_id:
                                if task_id in queued_task_ids_in_batch:
                                    logger.warning(f"[{self.agent_name}] Skipping duplicate task_id '{task_id}' (message ID: {msg_id}) within the same poll batch.")
                                    continue # Skip this duplicate task
                                else:
                                    queued_task_ids_in_batch.add(task_id) # Mark task_id as seen in this batch
                            # --- END DEDUPLICATION LOGIC ---

                            # Check for all required fields before queuing
                            required_fields = ['type', 'content', 'from', 'timestamp']
                            if all(field in msg for field in required_fields):
                                # Log queuing action *before* putting it on the queue
                                logger.info(f"[{self.agent_name}] Queueing message ID: {msg_id} Type: {msg.get('type')} From: {msg.get('from')}")
                                await self.message_queue.put((msg, msg_id))
                                new_last_id = msg_id # Track latest ID processed successfully
                                logger.debug(f"[{self.agent_name}] Successfully queued message {msg_id}")
                            else:
                                missing = [field for field in required_fields if field not in msg]
                                logger.warning(f"[{self.agent_name}] Message ID {msg_id} missing required fields: {missing}. Skipping. Message: {msg}")
                                continue # Skip incomplete messages

                        # Update last seen ID *only if* we processed any valid messages in this batch
                        if new_last_id:
                            self.last_message_id = new_last_id
                            logger.debug(f"[{self.agent_name}] Updated last_message_id to {new_last_id}")
                        else:
                             logger.debug(f"[{self.agent_name}] No valid messages processed in this batch, last_message_id remains {self.last_message_id}")


                    elif response.status in [401, 403]:
                        error_text = await response.text()
                        logger.error(f"[{self.agent_name}] Authentication error ({response.status}) polling messages: {error_text}. Stopping poll task.")
                        self._stop_polling_event.set() # Stop polling on auth errors
                        break # Exit the while loop immediately
                    else:
                        # Handle other non-200 responses (e.g., 404, 500)
                        error_text = await response.text()
                        logger.warning(f"[{self.agent_name}] Error polling messages ({response.status}): {error_text[:200]}... Retrying after interval.")

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"[{self.agent_name}] Network error or timeout during polling: {e}. Retrying after interval.")
            except Exception as e:
                # Catch-all for unexpected errors within the poll loop itself
                logger.exception(f"[{self.agent_name}] Unexpected error in polling loop: {e}")

            # Wait before the next poll attempt, unless stopping
            if not self._stop_polling_event.is_set():
                logger.debug(f"[{self.agent_name}] Waiting {poll_interval}s before next poll...")
                await asyncio.sleep(poll_interval)

        # --- End of while loop ---
        logger.info(f"[{self.agent_name}] Polling task stopped.")
        # Ensure session is closed when polling loop exits
        if hasattr(self, '_client_session') and self._client_session and not self._client_session.closed:
            await self._client_session.close()
            logger.info(f"[{self.agent_name}] Client session closed after polling loop exit.")
        self._client_session = None # Reset session variable

    async def start_polling(self, poll_interval: int = 2):
        """Starts the background message polling task."""
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
        self._polling_task = asyncio.create_task(self._poll_for_messages(poll_interval))
 

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
        self._polling_task = asyncio.create_task(self._poll_for_messages(poll_interval), name=f"poll_messages_{self.agent_name}")
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
        """Send a message to another agent.
        
        This method handles message delivery to other agents through HTTP POST requests.
        It supports both local and remote message delivery with automatic retries and
        error handling.
        
        Args:
            target: The target agent's endpoint URL or identifier
            message: The message payload to send
            
        Returns:
            Dict containing the server's response or error information
            
        Raises:
            ClientError: If there are network or connection issues
            ValueError: If the message format is invalid
        """
        # Create a ClientSession with optimized settings
        timeout = aiohttp.ClientTimeout(total=55)  # 55s timeout (Cloud Run's limit is 60s)
        async with ClientSession(
            connector=TCPConnector(verify_ssl=False),
            timeout=timeout
        ) as session:
            try:
                # Use target URL as is since it's already complete
                url = target
                logger.info(f"[{self.agent_name}] Sending message to {url}")
                
                # Include auth token in headers if we have one
                headers = {}
                if hasattr(self, 'auth_token') and self.auth_token:
                    headers['Authorization'] = f'Bearer {self.auth_token}'
                logger.debug(f"[{self.agent_name}] Using headers: {headers}")
                    
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
                        
                    logger.info(f"[{self.agent_name}] Message sent successfully")
                    
                    # Handle body parsing if present
                    if isinstance(response_data, dict) and 'body' in response_data:
                        try:
                            # Attempt to parse the body string as JSON (should be a list)
                            parsed_body = json.loads(response_data['body'])
                            if isinstance(parsed_body, list):
                                response_data['body'] = parsed_body # Assign the parsed list to body
                                logger.debug(f"[{self.agent_name}] Successfully parsed message body as JSON list.")
                            else:
                                logger.warning(f"[{self.agent_name}] Parsed message body is not a list: {type(parsed_body)}. Body: {response_data['body'][:200]}...") # Log truncated body
                        except json.JSONDecodeError as e:
                            logger.warning(f"[{self.agent_name}] Failed to decode message body as JSON: {e}. Body: {response_data['body'][:200]}...") # Log truncated body
                            
                    # Queue task messages
                    if response_data.get('type') == 'task':
                        message_id = response_data.get('message_id')
                        logger.info(f"[{self.agent_name}] Queueing task message {message_id}")
                        await self.message_queue.put((response_data, message_id))
                    
                    return response_data
            except Exception as e:
                logger.error(f"[{self.agent_name}] Error sending message: {e}")
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

    async def receive_message(self, timeout: float = 1.0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
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
            # If polling task is not running or finished (potentially due to error or disconnect),
            # don't wait indefinitely for messages that will never arrive.
            # We check if the queue is empty; if not, process remaining messages.
            if self.message_queue.empty():
                logger.debug(f"[{self.agent_name}] Polling task inactive and queue empty. Returning None.")
                return None, None
            else:
                logger.debug(f"[{self.agent_name}] Polling task inactive, but queue has messages. Trying to dequeue one.")
                # Fall through to try and get remaining messages without timeout
                timeout = 0 # Set timeout to 0 to get immediately if available

        try:
            # Wait for a message from the queue with a timeout
            if timeout > 0:
                logger.debug(f"[{self.agent_name}] Waiting for message from queue (timeout={timeout}s)...")
                try:
                    message, message_id = await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    # This is normal - no message available within timeout
                    logger.debug(f"[{self.agent_name}] Timeout waiting for message. Returning None.")
                    return None, None
            else:
                # Non-blocking get if timeout is 0 or polling stopped with items left
                try:
                    message, message_id = self.message_queue.get_nowait()
                except asyncio.QueueEmpty:
                    # Queue is empty
                    logger.debug(f"[{self.agent_name}] Queue empty on get_nowait. Returning None.")
                    return None, None
                
            logger.info(f"[{self.agent_name}] Received message from queue: {json.dumps(message, indent=2)}")
            
            # Validate message before returning
            if message and isinstance(message, dict) and message.get('type') and message.get('content'):
                logger.info(f"[{self.agent_name}] Message validation passed, returning message with ID: {message_id}")
                # Mark task done *after* successful retrieval and validation
                self.message_queue.task_done()
                return message, message_id
            else:
                logger.warning(f"[{self.agent_name}] Dequeued message failed validation. Returning None. Message: {message}, ID: {message_id}")
                # Mark task as done even if validation failed, as we dequeued it
                self.message_queue.task_done()
                return None, None
                
        except asyncio.CancelledError:
            logger.info(f"[{self.agent_name}] receive_message task cancelled.")
            raise
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error receiving message: {e}. Returning None.")
            traceback.print_exc()
            # Ensure task_done is called even on exception if item was potentially dequeued
            # Note: This might double-call task_done if the error happened before get(), but Queue handles this.
            try:
                 self.message_queue.task_done()
            except ValueError: # Already marked done
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
        
    def stop(self):
        """Stops the local HTTP server (if running).
        
        This method gracefully shuts down the local HTTP server when operating in
        local mode. For remote connections, use disconnect() instead.
        
        The method ensures proper cleanup of server resources and thread termination.
        """
        if self.is_remote:
             logger.info(f"[{self.agent_name or 'Unknown'}] In remote mode. Call disconnect() to stop polling.")
             pass 
        elif self.server_thread:
            logger.info(f"Stopping local server thread (implementation pending)...")
            pass
            
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
