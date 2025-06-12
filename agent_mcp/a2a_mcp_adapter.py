"""
Adapter for A2A (Agent-to-Agent) Protocol to work with AgentMCP.
"""

import asyncio
import httpx
import uuid
from typing import Dict, Any, Optional, AsyncGenerator, List

from .mcp_agent import MCPAgent
from .mcp_transport import MCPTransport

# A2A SDK components
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import (
    AgentCard,
    Message as A2AMessage,
    TextPart as A2ATextPart,
    DataPart as A2ADataPart,
    FilePart as A2AFilePart,
    FileWithUri,
    FileWithBytes,
    Task as A2ATask,
    SendMessageRequest,
    MessageSendParams,
    SendStreamingMessageRequest,
    Role as A2ARole,
    TaskStatusUpdateEvent as A2ATaskStatusUpdateEvent,
    TaskArtifactUpdateEvent as A2ATaskArtifactUpdateEvent,
    JSONRPCErrorResponse as A2AJSONRPCErrorResponse,
    Part as A2APart,
    TaskState as A2ATaskState # Added for server-side
)
from a2a.utils.message import new_agent_text_message #, new_user_text_message # Added for server-side mock

# Server-side components
from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext as A2ARequestContext
from a2a.server.events import EventQueue as A2AEventQueue
from a2a.server.tasks import TaskUpdater as A2ATaskUpdater

# --- Setup Logger ---
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# --- End Logger Setup ---

class A2AMCPAdapter(MCPAgent):
    """
    Adapter to allow AgentMCP agents to communicate with A2A compliant agents (client role)
    and potentially be called by A2A compliant agents (server role).
    """

    def __init__(self,
                 name: str,
                 mcp_id: Optional[str] = None,
                 # A2A specific config
                 remote_agent_card_url: Optional[str] = None,
                 a2a_client_auth: Optional[Dict[str, Any]] = None, # For passing auth details to httpx
                 # AgentMCP specific config
                 transport: Optional[MCPTransport] = None, # For AgentMCP internal communication
                 system_message: str = "A2A MCP Adapter",
                 # Server-side A2A config
                 enable_a2a_server: bool = False,
                 **kwargs):
        super().__init__(name=name, mcp_id=mcp_id, system_message=system_message, **kwargs)

        self.remote_agent_card_url = remote_agent_card_url
        self.a2a_client_auth = a2a_client_auth
        self.mcp_transport = transport # For AgentMCP side

        self._a2a_client: Optional[A2AClient] = None # Type updated
        self._remote_agent_card: Optional[AgentCard] = None # Type updated
        self._http_client: Optional[httpx.AsyncClient] = None

        # Server-side components
        self.enable_a2a_server = enable_a2a_server
        self._a2a_server_executor: Optional[A2AMCPAdapter.InternalA2AExecutor] = None
        if self.enable_a2a_server:
            self._a2a_server_executor = self.InternalA2AExecutor(adapter_ref=self)
            logger.info(f"[{self.name}] A2A Server Executor initialized.")

        logger.info(f"[{self.name}] A2AMCPAdapter initialized (Server enabled: {self.enable_a2a_server}).")


    # --- Client-Side A2A Implementation ---
    async def _init_httpx_client(self):
        if not self._http_client:
            try:
                # TODO: Configure auth, timeouts, etc., based on self.a2a_client_auth (e.g. Bearer token)
                # headers = {}
                # if self.a2a_client_auth and "token" in self.a2a_client_auth:
                #     headers["Authorization"] = f"Bearer {self.a2a_client_auth['token']}"
                self._http_client = httpx.AsyncClient(timeout=30.0) # Add headers=headers if auth is used
                logger.info(f"[{self.name}] HTTPX client initialized.")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to initialize HTTPX client: {e}")
                raise

    async def _get_a2a_client(self) -> A2AClient:
        """
        Initializes and returns the A2AClient.
        Fetches the remote agent card if not already fetched.
        """
        await self._init_httpx_client()
        if not self._http_client: # Should have been initialized by _init_httpx_client
            raise ConnectionError(f"[{self.name}] HTTPX client not available.")

        if not self._a2a_client:
            if not self.remote_agent_card_url:
                logger.error(f"[{self.name}] Remote A2A Agent Card URL is not configured.")
                raise ValueError("Remote A2A Agent Card URL is not configured.")

            try:
                logger.info(f"[{self.name}] Attempting to resolve A2A Agent Card from: {self.remote_agent_card_url}")
                resolver = A2ACardResolver(httpx_client=self._http_client, base_url=self.remote_agent_card_url)
                self._remote_agent_card = await resolver.get_agent_card()
                logger.info(f"[{self.name}] Successfully fetched remote agent card for '{self._remote_agent_card.name}'.")

                self._a2a_client = A2AClient(httpx_client=self._http_client, agent_card=self._remote_agent_card)
                logger.info(f"[{self.name}] A2AClient initialized for agent '{self._remote_agent_card.name}'.")

            except httpx.HTTPStatusError as e:
                logger.error(f"[{self.name}] HTTP error fetching agent card from {self.remote_agent_card_url}: {e.response.status_code} - {e.response.text}")
                raise ConnectionError(f"Failed to fetch agent card: {e.response.status_code}") from e
            except Exception as e:
                logger.error(f"[{self.name}] Failed to initialize A2A client or fetch agent card: {e}")
                raise
        return self._a2a_client

    async def send_a2a_message(self, message_content: Dict[str, Any], skill_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends a message to the remote A2A agent using the A2A protocol.
        This is for request/response interaction.
        """
        a2a_client = await self._get_a2a_client()

        a2a_message = self._convert_mcp_to_a2a_message(message_content, skill_id=skill_id)

        request_id = str(uuid.uuid4())
        # TODO: The `MessageSendParams` might need more fields depending on A2A spec evolution (e.g. `skill_id`)
        # For now, assuming skill_id might be part of the message content or handled by the agent itself.
        params = MessageSendParams(message=a2a_message)
        a2a_request = SendMessageRequest(id=request_id, params=params)

        logger.info(f"[{self.name}] Sending A2A message (ID: {request_id}) to '{self._remote_agent_card.name if self._remote_agent_card else 'Unknown A2A Agent'}'.")
        logger.debug(f"[{self.name}] A2A Request: {a2a_request.model_dump_json(indent=2, exclude_none=True)}")

        try:
            raw_response = await a2a_client.send_message(a2a_request)

            if raw_response.result:
                logger.info(f"[{self.name}] Received A2A response for message ID {request_id}.")
                logger.debug(f"[{self.name}] Raw A2A Response Result: {raw_response.result}")
                return self._convert_a2a_response_to_mcp(raw_response.result)
            elif raw_response.error:
                logger.error(f"[{self.name}] A2A error for message ID {request_id}: {raw_response.error.message} (Code: {raw_response.error.code})")
                logger.debug(f"[{self.name}] Raw A2A Error Response: {raw_response.error}")
                # Convert the whole error response for structured error info
                return self._convert_a2a_response_to_mcp(raw_response) # Pass the full JSONRPCResponse
            else:
                # This case should ideally not happen if the A2A SDK adheres to JSON-RPC structure
                logger.error(f"[{self.name}] Unexpected A2A response structure for message ID {request_id}: No result or error.")
                raise ConnectionError("Invalid A2A response: missing result and error.")

        except httpx.RequestError as e:
            logger.error(f"[{self.name}] HTTP request error during A2A send_message: {e}")
            raise ConnectionError(f"A2A request failed: {e}") from e
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error in send_a2a_message: {e}")
            raise

    async def stream_a2a_message(self, message_content: Dict[str, Any], skill_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Sends a message and streams responses from the remote A2A agent using SSE.
        """
        a2a_client = await self._get_a2a_client()

        if not (self._remote_agent_card and self._remote_agent_card.capabilities and self._remote_agent_card.capabilities.streaming):
            logger.error(f"[{self.name}] Remote A2A agent '{self._remote_agent_card.name if self._remote_agent_card else 'Unknown'}' does not support streaming.")
            raise NotImplementedError(f"Remote A2A agent '{self._remote_agent_card.name if self._remote_agent_card else 'Unknown'}' does not support streaming.")

        a2a_message = self._convert_mcp_to_a2a_message(message_content, skill_id=skill_id)

        request_id = str(uuid.uuid4())
        params = MessageSendParams(message=a2a_message) # skill_id might be part of params in future SDK
        a2a_request = SendStreamingMessageRequest(id=request_id, params=params)

        logger.info(f"[{self.name}] Sending A2A streaming message (ID: {request_id}) to '{self._remote_agent_card.name}'.")
        logger.debug(f"[{self.name}] A2A Streaming Request: {a2a_request.model_dump_json(indent=2, exclude_none=True)}")

        try:
            async for event_response in a2a_client.send_message_streaming(a2a_request):
                if event_response.result:
                    logger.debug(f"[{self.name}] Received A2A stream event for request ID {request_id}: {type(event_response.result)}")
                    yield self._convert_a2a_response_to_mcp(event_response.result)
                elif event_response.error:
                    logger.error(f"[{self.name}] A2A stream error for request ID {request_id}: {event_response.error.message} (Code: {event_response.error.code})")
                    # Yield a structured error or raise? For now, yield it.
                    yield self._convert_a2a_response_to_mcp(event_response) # Pass the full JSONRPCResponse
                else:
                    logger.warning(f"[{self.name}] Unexpected A2A stream event structure for request ID {request_id}: No result or error.")

        except httpx.RequestError as e:
            logger.error(f"[{self.name}] HTTP request error during A2A stream_message: {e}")
            raise ConnectionError(f"A2A streaming request failed: {e}") from e
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error in stream_a2a_message: {e}")
            raise
        finally:
            logger.info(f"[{self.name}] Finished streaming A2A responses for request ID {request_id}.")


    def _convert_a2a_response_to_mcp(self, a2a_response: Any) -> Dict[str, Any]:
        """
        Converts an A2A Task, Message, Event object, or JSONRPCErrorResponse
        to an AgentMCP dictionary response.
        """
        response_type = "unknown"
        if isinstance(a2a_response, A2ATask):
            response_type = "task"
        elif isinstance(a2a_response, A2AMessage):
            response_type = "message"
        elif isinstance(a2a_response, A2ATaskStatusUpdateEvent):
            response_type = "status_update"
        elif isinstance(a2a_response, A2ATaskArtifactUpdateEvent):
            response_type = "artifact_update"
        elif isinstance(a2a_response, A2AJSONRPCErrorResponse): # This is the whole response, not just the error part
            response_type = "error"
            # Return structure that includes the error object
            return {
                "type": response_type,
                "id": a2a_response.id,
                "error": {
                    "code": a2a_response.error.code,
                    "message": a2a_response.error.message,
                    "data": a2a_response.error.data
                }
            }

        if hasattr(a2a_response, 'model_dump'):
            try:
                mcp_dict = a2a_response.model_dump(mode='json', exclude_none=True)
                # Ensure a 'type' field is present, especially for events that might be part of a Task.
                if 'type' not in mcp_dict : # Could be Task which contains events
                    mcp_dict['type'] = response_type
                return mcp_dict
            except Exception as e:
                logger.error(f"[{self.name}] Failed to model_dump A2A response of type {type(a2a_response)}: {e}")
                return {"raw_a2a_response": str(a2a_response), "type": "conversion_error", "error_message": str(e)}

        logger.warning(f"[{self.name}] Unexpected A2A response type for conversion: {type(a2a_response)}. Value: {a2a_response}")
        return {"raw_a2a_response": str(a2a_response), "type": "unknown_type"}

    def _convert_mcp_to_a2a_message(self, mcp_message: Dict[str, Any], skill_id: Optional[str] = None) -> A2AMessage:
        """Converts an AgentMCP message dictionary to an A2A Message object."""
        message_id = str(uuid.uuid4())

        # Determine role - default to USER. Could be configurable via mcp_message meta if needed.
        role_str = mcp_message.get("role", "user")
        try:
            role = A2ARole(role_str.lower())
        except ValueError:
            logger.warning(f"[{self.name}] Invalid role '{role_str}' in MCP message. Defaulting to USER.")
            role = A2ARole.USER

        a2a_parts: List[A2APart] = []

        # Handle structured parts if present
        mcp_parts = mcp_message.get("parts")
        if isinstance(mcp_parts, list):
            for part_dict in mcp_parts:
                if not isinstance(part_dict, dict):
                    logger.warning(f"[{self.name}] Skipping non-dict part in mcp_message parts list: {part_dict}")
                    continue

                kind = part_dict.get("kind")
                if kind == "text":
                    a2a_parts.append(A2ATextPart(text=part_dict.get("text", "")))
                elif kind == "data":
                    data_content = part_dict.get("data")
                    if isinstance(data_content, dict):
                        a2a_parts.append(A2ADataPart(data=data_content))
                    else:
                        logger.warning(f"[{self.name}] DataPart content is not a dict, skipping: {data_content}")
                elif kind == "file":
                    if "uri" in part_dict:
                        a2a_parts.append(A2AFilePart(file=FileWithUri(uri=part_dict["uri"], mimeType=part_dict.get("mime_type"))))
                    elif "bytes_content" in part_dict: # Assuming bytes_content holds the actual bytes
                         a2a_parts.append(A2AFilePart(file=FileWithBytes(bytes=part_dict["bytes_content"], mimeType=part_dict.get("mime_type"))))
                    else:
                        logger.warning(f"[{self.name}] FilePart has no 'uri' or 'bytes_content', skipping: {part_dict}")
                else:
                    logger.warning(f"[{self.name}] Unknown part kind '{kind}', skipping: {part_dict}")

        # Fallback or direct content fields if `parts` is not used or empty
        if not a2a_parts:
            text_content = mcp_message.get("text")
            data_content = mcp_message.get("data") # This is ambiguous with parts[kind=data]. Prioritize parts.

            if text_content is not None and isinstance(text_content, str):
                a2a_parts.append(A2ATextPart(text=text_content))

            if data_content is not None and isinstance(data_content, dict):
                 # Only add if not already processed via parts (though explicit parts should be preferred)
                if not any(isinstance(p, A2ADataPart) and p.data == data_content for p in a2a_parts):
                    a2a_parts.append(A2ADataPart(data=data_content))

            # Simplest case: if parts is empty and mcp_message itself is a simple text string (passed as content/data)
            if not a2a_parts and isinstance(mcp_message.get("content"), str): # "content" as a common field
                 a2a_parts.append(A2ATextPart(text=mcp_message["content"]))
            elif not a2a_parts and isinstance(mcp_message.get("data"), str): # "data" as a simple text field
                 a2a_parts.append(A2ATextPart(text=mcp_message["data"]))


        if not a2a_parts:
            logger.warning(f"[{self.name}] No parts could be constructed for A2A message from MCP message: {mcp_message}. Sending an empty message.")
            # Or raise ValueError("Cannot send an empty message") if that's preferred

        # skill_id is not directly part of A2AMessage in current a2a.types
        # It might be part of MessageSendParams or handled by the agent's endpoint routing.
        # For now, it's passed to send/stream methods but not directly in A2AMessage object.

        return A2AMessage(
            messageId=message_id,
            role=role,
            parts=a2a_parts,
            taskId=mcp_message.get("task_id"),      # Propagate if present
            contextId=mcp_message.get("context_id") # Propagate if present
        )

    # --- MCPAgent methods to override ---

    async def handle_incoming_message(self, message: Dict[str, Any], message_id: Optional[str] = None):
        """
        Handles an incoming message from AgentMCP, intended for a remote A2A agent.
        This adapter acts as a client to the A2A agent.
        """
        logger.info(f"[{self.name}] A2A Adapter received MCP message: {message}")

        # Determine if streaming is requested (e.g., via a flag in message.get("meta"))
        meta = message.get("meta", {}) if isinstance(message.get("meta"), dict) else {}
        use_streaming = meta.get("a2a_streaming", False)
        skill_id = meta.get("a2a_skill_id") # skill_id might be used by A2A agent endpoint

        # The 'content' of the MCP message is expected to be a dictionary
        # suitable for _convert_mcp_to_a2a_message.
        # This could be e.g. {"text": "Hello"} or {"parts": [{"kind": "text", "text": "Hello"}]}
        a2a_message_payload = message.get("content", {})
        if not isinstance(a2a_message_payload, dict):
            logger.warning(f"[{self.name}] MCP message content is not a dict, attempting to wrap: {a2a_message_payload}")
            # Attempt to treat it as simple text if it's a string.
            if isinstance(a2a_message_payload, str):
                 a2a_message_payload = {"text": a2a_message_payload}
            else: # Otherwise, it's an unhandled format.
                a2a_message_payload = {"data": str(a2a_message_payload)} # Fallback, might not be ideal

        reply_to_agent = message.get("reply_to")
        original_task_id = message.get("task_id")

        try:
            if use_streaming:
                logger.info(f"[{self.name}] Handling incoming MCP message for A2A streaming. Task ID: {original_task_id}")
                async for response_part in self.stream_a2a_message(a2a_message_payload, skill_id):
                    if self.mcp_transport and reply_to_agent:
                        await self.mcp_transport.send_message(
                            target_agent_name=reply_to_agent,
                            message_content={
                                "type": "task_result_stream_part", # More specific type
                                "task_id": original_task_id,
                                "stream_content": response_part, # This is the converted A2A event dict
                                "sender": self.name
                            }
                        )
                    else:
                        logger.info(f"[{self.name}] Streamed A2A response part (no MCP transport/reply_to): {response_part}")
            else:
                logger.info(f"[{self.name}] Handling incoming MCP message for A2A request/response. Task ID: {original_task_id}")
                response = await self.send_a2a_message(a2a_message_payload, skill_id)
                if self.mcp_transport and reply_to_agent:
                    await self.mcp_transport.send_message(
                        target_agent_name=reply_to_agent,
                        message_content={
                            "type": "task_result", # Standard type for full result
                            "task_id": original_task_id,
                            "result": response, # This is the converted A2A Task/Message dict
                            "sender": self.name
                        }
                    )
                else:
                    logger.info(f"[{self.name}] A2A response (no MCP transport/reply_to): {response}")

        except NotImplementedError as nie: # Specific for non-streaming agent
            logger.error(f"[{self.name}] Operation not implemented (e.g. streaming for non-streaming agent): {nie}")
            if self.mcp_transport and reply_to_agent:
                 await self.mcp_transport.send_message(
                    target_agent_name=reply_to_agent,
                    message_content={
                        "type": "task_error", "task_id": original_task_id,
                        "error": f"NotImplemented: {str(nie)}", "sender": self.name
                    })
        except ConnectionError as ce: # Specific for connection issues
            logger.error(f"[{self.name}] A2A Connection error: {ce}")
            if self.mcp_transport and reply_to_agent:
                 await self.mcp_transport.send_message(
                    target_agent_name=reply_to_agent,
                    message_content={
                        "type": "task_error", "task_id": original_task_id,
                        "error": f"A2A Connection Error: {str(ce)}", "sender": self.name
                    })
        except Exception as e:
            logger.error(f"[{self.name}] Error during A2A communication for Task ID {original_task_id}: {e}", exc_info=True)
            if self.mcp_transport and reply_to_agent:
                await self.mcp_transport.send_message(
                    target_agent_name=reply_to_agent,
                    message_content={
                        "type": "task_error",
                        "task_id": original_task_id,
                        "error": f"General A2A Error: {str(e)}",
                        "sender": self.name
                    }
                )
        finally:
            # Acknowledge MCP message if message_id and transport are available
            if message_id and self.mcp_transport and hasattr(self.mcp_transport, 'acknowledge_message'):
                try:
                    await self.mcp_transport.acknowledge_message(self.name, message_id)
                    logger.debug(f"[{self.name}] MCP Message ID {message_id} acknowledged.")
                except Exception as ack_e:
                    logger.error(f"[{self.name}] Failed to acknowledge MCP message ID {message_id}: {ack_e}")

    def _convert_a2a_to_mcp_message(self, a2a_message: A2AMessage) -> Dict[str, Any]:
        """
        Converts an incoming A2A Message object to an AgentMCP message dictionary.
        Placeholder implementation.
        """
        logger.debug(f"[{self.name}] Converting A2A message (ID: {a2a_message.messageId}) to MCP format.")
        # This would iterate through a2a_message.parts and convert them to a suitable MCP structure.
        # For example, map A2ATextPart to {"text": ...}, A2ADataPart to {"data": ...}, etc.
        # It also needs to consider how to represent different part kinds in the MCP message.

        # Simple placeholder:
        text_content = "Default content (A2A message was complex or non-text)"
        if a2a_message.parts:
            first_part = a2a_message.parts[0]
            if isinstance(first_part, A2ATextPart):
                text_content = first_part.text
            elif isinstance(first_part, A2ADataPart):
                text_content = f"Received data: {str(first_part.data)[:100]}" # Truncate for logging
            # Add more part types as needed

        return {
            "content": {"text": text_content}, # Or a more structured format like {"parts": [...]}
            "meta": {
                "source": "a2a_adapter_server",
                "a2a_message_id": a2a_message.messageId,
                "a2a_task_id": a2a_message.taskId,
                "a2a_context_id": a2a_message.contextId,
                "a2a_role": a2a_message.role.value if a2a_message.role else None,
            }
        }

    # --- Server-Side A2A Executor Implementation ---
    class InternalA2AExecutor(A2AAgentExecutor):
        def __init__(self, adapter_ref: 'A2AMCPAdapter'):
            self.adapter_ref = adapter_ref # Reference to the parent A2AMCPAdapter
            self.logger = logging.getLogger(f"{adapter_ref.name}.InternalA2AExecutor")
            super().__init__()
            self.logger.info("InternalA2AExecutor initialized.")

        async def execute(self, context: A2ARequestContext, event_queue: A2AEventQueue) -> None:
            self.logger.info(f"Execute called for task_id: {context.task_id}, A2A Message ID: {context.message.messageId if context.message else 'N/A'}")

            task_updater = A2ATaskUpdater(event_queue=event_queue, task_id=context.task_id, context_id=context.context_id)

            if not context.message:
                self.logger.warning(f"Execute called with no message for task_id: {context.task_id}. Completing with error.")
                error_response_msg = new_agent_text_message(
                    text="Error: No message provided in the request.",
                    task_id=context.task_id, context_id=context.context_id
                )
                await task_updater.update_status(A2ATaskState.FAILED, final=True, message=error_response_msg)
                return

            try:
                # 1. Acknowledge receipt by submitting the original message (or a derivative)
                # This informs the A2A client that the message was received and processing has begun.
                # The A2A spec suggests the agent *may* respond with the initial message or a new one.
                await task_updater.submit(message=context.message)
                await task_updater.start_work()
                self.logger.info(f"Task {context.task_id} work started.")

                # 2. Convert A2A RequestContext.message to an AgentMCP message/task
                # mcp_message_payload = self.adapter_ref._convert_a2a_to_mcp_message(context.message)

                # 3. Dispatch to self.adapter_ref.wrapped_mcp_agent (MCPAgent instance)
                # This is the complex part:
                #   - How to get the response back if it's async? (Requires a callback mechanism or await)
                #   - If using mcp_transport.send_message, it implies the wrapped agent is "remote"
                #     and we need a way to correlate responses. This might mean this executor
                #     needs its own temporary reply queue/handler within the MCP system.
                #   - For a direct call (if wrapped_mcp_agent is local and has a suitable method):
                #     `mcp_response = await self.adapter_ref.wrapped_mcp_agent.some_handler_method(mcp_message_payload)`

                # --- Placeholder/Mock Logic for now ---
                await asyncio.sleep(0.2) # Simulate work being done by the wrapped MCP agent

                # Example: Create a simple text response based on the input
                first_part_text = "unknown content"
                if context.message.parts and isinstance(context.message.parts[0], A2ATextPart):
                    first_part_text = context.message.parts[0].text

                mock_mcp_response_text = f"A2A Server processed: '{first_part_text}' for task {context.task_id}"
                self.logger.info(f"Mock MCP response for task {context.task_id}: {mock_mcp_response_text}")

                # 4. Convert MCP response back to A2A Message or Artifacts
                # For this mock, we just create a new A2A agent message.
                response_a2a_message = new_agent_text_message(
                    text=mock_mcp_response_text,
                    task_id=context.task_id, # Ensure task_id is part of the response message
                    context_id=context.context_id
                )

                # 5. Use TaskUpdater to publish results/artifacts and complete the task
                # await task_updater.add_artifact(...) # If there are artifacts
                await task_updater.complete(message=response_a2a_message)
                self.logger.info(f"Task {context.task_id} completed successfully.")

            except Exception as e:
                self.logger.error(f"Error during execute for task_id {context.task_id}: {e}", exc_info=True)
                error_message = new_agent_text_message(
                    text=f"Error processing request: {str(e)}",
                    task_id=context.task_id, context_id=context.context_id
                )
                try:
                    await task_updater.update_status(A2ATaskState.FAILED, final=True, message=error_message)
                except Exception as update_err:
                     self.logger.error(f"Failed to update task status to FAILED for task_id {context.task_id}: {update_err}")


        async def cancel(self, context: A2ARequestContext, event_queue: A2AEventQueue) -> None:
            self.logger.info(f"Cancel called for task_id: {context.task_id}")
            task_updater = A2ATaskUpdater(event_queue=event_queue, task_id=context.task_id, context_id=context.context_id)

            # 1. Send cancellation to self.adapter_ref.wrapped_mcp_agent
            #    This would involve logic similar to dispatching in `execute`, e.g.,
            #    `await self.adapter_ref.wrapped_mcp_agent.cancel_task(context.task_id)`
            #    For now, we assume cancellation is accepted.
            self.logger.info(f"Placeholder: Propagating cancellation for task {context.task_id} to wrapped MCP agent.")

            # 2. Publish cancellation status to event_queue
            try:
                # Optionally include a message with the cancellation status update
                # cancel_message = new_agent_text_message(text="Task cancellation processed.", task_id=context.task_id, context_id=context.context_id)
                await task_updater.update_status(A2ATaskState.CANCELED, final=True) #, message=cancel_message)
                self.logger.info(f"Task {context.task_id} status updated to CANCELED.")
            except Exception as e:
                self.logger.error(f"Error updating task status to CANCELED for task_id {context.task_id}: {e}", exc_info=True)

    async def shutdown(self):
        if self._http_client:
            await self._http_client.aclose()
            logger.info(f"[{self.name}] HTTPX client closed.")
        # TODO: Add shutdown for A2A server components if implemented (e.g. stopping the ASGI server)
        if self.enable_a2a_server and self._a2a_server_executor:
            logger.info(f"[{self.name}] A2A Server Executor was enabled. (No specific shutdown action for executor itself).")
        logger.info(f"[{self.name}] A2AMCPAdapter shutdown complete.")

    # Required MCPAgent methods (if not fully handled by base or above)
    async def send_message(self, content: Dict[str, Any], recipient_mcp_id: str) -> Optional[Dict[str, Any]]:
        # This method is for MCP-to-MCP communication.
        # If this adapter is purely for A2A, this might not be used directly,
        # or it could be used to forward to an A2A agent if recipient_mcp_id
        # is mapped to an A2A agent's card.
        logger.warning(f"[{self.name}] send_message called, but this adapter is primarily for A2A. Forwarding logic needed if {recipient_mcp_id} is A2A.")
        # Example: if self.is_a2a_target(recipient_mcp_id):
        # return await self.send_a2a_message(content)
        return None

    async def process_action(self, action_name: str, params: Dict[str, Any]) -> Any:
        # This is for direct action calls on the agent.
        # Could be mapped to A2A skills/calls if applicable.
        logger.warning(f"[{self.name}] process_action '{action_name}' called. A2A mapping would be needed.")
        # Example: if action_name == "call_a2a_skill_X":
        # return await self.send_a2a_message(params, skill_id="X")
        return f"Action '{action_name}' not implemented for A2A adapter."

if __name__ == '__main__':
    # Example Usage (Conceptual - requires running A2A server and proper SDK setup)
    async def main():
        # Initialize adapter to talk to a remote A2A agent
        # This example requires a running A2A-compliant agent server.
        # Ensure a2a-python-sdk is installed.
        # Set up a dummy A2A server or use a real one for testing.

        # Example: remote_agent_card_url="http://localhost:8000/.well-known/agent.json" # For client part
        # To test server part, you would need an A2A client calling this adapter.

        logger.info("Starting A2AMCPAdapter example main().")

        # Initialize with server disabled for now in this example,
        # as running the server part requires an external A2A client to call it.
        adapter = A2AMCPAdapter(
            name="MyA2AClientAdapterWithServerStubs",
            remote_agent_card_url="http://localhost:8000/.well-known/agent.json", # For client functionality
            enable_a2a_server=False # Set to True if you have an A2A client to test server part
        )

        if adapter.enable_a2a_server and adapter._a2a_server_executor:
            logger.info("A2A Server executor is configured. To test, an A2A client should make requests to this agent's A2A endpoint.")
            # Here you would typically start an ASGI server (e.g., Uvicorn) with an A2AStarletteApplication
            # that uses adapter._a2a_server_executor. This is beyond this script's scope.
            # Example:
            # from a2a.server.app import A2AStarletteApplication
            # app = A2AStarletteApplication(agent_executor=adapter._a2a_server_executor, agent_card_service=...)
            # uvicorn.run(app, host="0.0.0.0", port=8001) # Example port for server

        # Mock MCPTransport for testing client-side handle_incoming_message
        class MockMCPTransport(MCPTransport):
            async def send_message(self, target_agent_name: str, message_content: Dict[str, Any]):
                logger.info(f"[MockMCPTransport] Sending to {target_agent_name}: {message_content}")
            async def acknowledge_message(self, agent_name: str, message_id: str):
                 logger.info(f"[MockMCPTransport] Ack for {agent_name}, msg_id {message_id}")

        adapter.mcp_transport = MockMCPTransport()


        # --- Test Case 1: Non-streaming message ---
        logger.info("\n--- Test Case 1: Sending non-streaming A2A message via handle_incoming_message ---")
        mcp_message_non_stream = {
            "task_id": "task_non_stream_001",
            "reply_to": "RequestingMCPAgent",
            "content": {"text": "Hello A2A agent, what is your name and capabilities?"},
            "meta": {"a2a_streaming": False}
        }
        try:
            await adapter.handle_incoming_message(mcp_message_non_stream, message_id="mcp_msg_1")
        except Exception as e:
            logger.error(f"Error in non-streaming test: {e}", exc_info=True)

        # --- Test Case 2: Streaming message ---
        # Note: This requires the remote A2A agent to support streaming.
        logger.info("\n--- Test Case 2: Sending streaming A2A message via handle_incoming_message ---")
        mcp_message_stream = {
            "task_id": "task_stream_002",
            "reply_to": "RequestingMCPAgent",
            "content": {"text": "Please stream me a short story, one sentence at a time."},
            "meta": {"a2a_streaming": True}
        }
        try:
            await adapter.handle_incoming_message(mcp_message_stream, message_id="mcp_msg_2")
        except NotImplementedError:
            logger.warning("Streaming test skipped or failed: Remote agent might not support streaming or A2A SDK not fully configured.")
        except Exception as e:
            logger.error(f"Error in streaming test: {e}", exc_info=True)

        # --- Test Case 3: Direct send_a2a_message (if you want to bypass handle_incoming) ---
        logger.info("\n--- Test Case 3: Direct send_a2a_message call ---")
        try:
            response = await adapter.send_a2a_message(
                {"parts": [{"kind": "text", "text": "Direct query: What's the weather like?"}]}
            )
            logger.info(f"Direct send_a2a_message response: {response}")
        except Exception as e:
            logger.error(f"Error in direct send_a2a_message test: {e}", exc_info=True)

        # --- Test Case 4: MCP message with more structured parts ---
        logger.info("\n--- Test Case 4: MCP message with structured parts ---")
        mcp_message_structured = {
            "task_id": "task_structured_003",
            "reply_to": "RequestingMCPAgent",
            "content": {
                "parts": [
                    {"kind": "text", "text": "This is a multi-part message."},
                    {"kind": "data", "data": {"key": "value", "number": 123}},
                    # {"kind": "file", "uri": "file:///tmp/example.txt"} # Requires file access / A2A agent support
                ]
            },
            "meta": {"a2a_streaming": False}
        }
        try:
            await adapter.handle_incoming_message(mcp_message_structured, message_id="mcp_msg_3")
        except Exception as e:
            logger.error(f"Error in structured parts test: {e}", exc_info=True)

        try:
            # Simulate how generate_internal_id might be used if it's part of MCPAgent
            # This is just for the mock example in the original file, not used by A2A SDK directly
            if hasattr(adapter, 'generate_internal_id'):
                logger.info(f"Adapter can generate internal IDs: {adapter.generate_internal_id()}")
        except Exception as e: # pylint: disable=broad-except
            logger.warning(f"Could not test generate_internal_id: {e}")


        except Exception as e: # pylint: disable=broad-except
            logger.error(f"Error in example usage: {e}", exc_info=True)
        finally:
            await adapter.shutdown()

    # asyncio.run(main())
    logger.info("A2A Adapter conceptual main finished. Uncomment asyncio.run(main()) and ensure A2A SDK is properly integrated for actual testing.")
