import asyncio
import traceback
import json
from typing import Dict, Any, Optional, Callable

from .mcp_agent import MCPAgent
from .mcp_transport import MCPTransport # Assuming HTTPTransport or a base MCPTransport

# --- Placeholder for LlamaIndex Agent ---
class PlaceholderLlamaIndexAgent:
    """
    A placeholder for the actual LlamaIndex Agent class.
    This will be replaced with the real LlamaIndex Agent implementation.
    Example LlamaIndex agent methods: chat, query
    """
    def __init__(self, name: str, **kwargs):
        self.name = name
        print(f"PlaceholderLlamaIndexAgent '{self.name}' initialized with kwargs: {kwargs}")

    async def chat(self, message: str, **kwargs) -> Any: # LlamaIndex agents often return an AgentChatResponse object
        """
        Simulates a chat interaction.
        """
        print(f"PlaceholderLlamaIndexAgent '{self.name}' processing chat: {message} with kwargs: {kwargs}")
        await asyncio.sleep(1) # Simulate async work
        # Simulate LlamaIndex AgentChatResponse structure
        class MockAgentChatResponse:
            def __init__(self, response_str):
                self.response = response_str
            def __str__(self):
                return self.response

        return MockAgentChatResponse(f"Response to '{message}' from {self.name}")

    async def query(self, query_str: str, **kwargs) -> Any:
        """
        Simulates a query interaction.
        """
        print(f"PlaceholderLlamaIndexAgent '{self.name}' processing query: {query_str} with kwargs: {kwargs}")
        await asyncio.sleep(1)
        class MockAgentChatResponse: # Or a QueryResponse object
            def __init__(self, response_str):
                self.response = response_str
            def __str__(self):
                return self.response
        return MockAgentChatResponse(f"Answer to query '{query_str}' from {self.name}")

# --- End Placeholder for LlamaIndex Agent ---

class LlamaIndexMcpAdapter(MCPAgent):
    """
    Adapter for LlamaIndex Agents to work with MCP.
    """

    def __init__(self,
                 name: str,
                 llama_index_agent: PlaceholderLlamaIndexAgent, # Will be actual LlamaIndex agent type
                 transport: Optional[MCPTransport] = None,
                 client_mode: bool = False, # Typically true
                 execution_method_name: str = "chat", # 'chat' or 'query' or other custom method
                 system_message: str = "I am a LlamaIndex agent integrated with MCP.",
                 **kwargs):
        super().__init__(name=name, system_message=system_message, **kwargs)

        self.llama_index_agent = llama_index_agent
        self.transport = transport
        self.client_mode = client_mode
        self.execution_method_name = execution_method_name
        self.task_queue = asyncio.Queue()
        self._task_processor_task = None
        self._message_processor_task = None

    async def handle_incoming_message(self, message: Dict[str, Any], message_id: Optional[str] = None):
        """
        Handle incoming messages from other agents via MCP.
        """
        msg_type = message.get("type")
        sender = self._extract_sender(message)
        task_id = message.get("task_id") or message.get("content", {}).get("task_id")

        print(f"[{self.name}] Received message (ID: {message_id}) of type '{msg_type}' from {sender} (Task ID: {task_id})")

        if not super()._should_process_message(message): # Idempotency
            if message_id and self.transport:
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
            print(f"[{self.name}] Skipped duplicate task {task_id} (msg_id: {message_id})")
            return

        if msg_type == "task":
            content = message.get("content", {})
            description = content.get("description") or message.get("description")
            reply_to = content.get("reply_to") or message.get("reply_to")

            if not task_id or not description:
                print(f"[{self.name}] Task message missing required fields: {message}")
                if message_id and self.transport:
                    asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                return

            task_context = {
                "type": "task",
                "task_id": task_id,
                "description": description,
                "reply_to": reply_to,
                "sender": sender,
                "original_message_id": message_id
            }
            await self.task_queue.put(task_context)
            print(f"[{self.name}] Queued task {task_id} from {sender}")

        elif msg_type == "task_result":
            print(f"[{self.name}] Received task_result: {message}")
            if message_id and self.transport:
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
        else:
            print(f"[{self.name}] Received unknown message type: {msg_type}. Message: {message}")
            if message_id and self.transport:
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))

    async def process_tasks(self):
        """
        Process tasks from the internal queue using the LlamaIndex agent.
        """
        print(f"[{self.name}] Task processor loop started.")
        while True:
            try:
                task_context = await self.task_queue.get()
                if task_context is None: break

                task_id = task_context.get("task_id")
                description = task_context.get("description")
                reply_to = task_context.get("reply_to")
                original_message_id = task_context.get("original_message_id")

                print(f"[{self.name}] Processing task {task_id}: {description}")

                try:
                    agent_method = getattr(self.llama_index_agent, self.execution_method_name)
                    # LlamaIndex agent methods (chat, query) typically return an object (e.g., AgentChatResponse)
                    # We need to extract the string representation or relevant part.
                    response_obj = await agent_method(description)
                    result_data = str(response_obj) # Extracts .response via __str__ in placeholder
                except AttributeError:
                    err_msg = f"LlamaIndex agent does not have method '{self.execution_method_name}'"
                    print(f"[{self.name}] {err_msg}")
                    traceback.print_exc()
                    result_data = f"Error: {err_msg}"
                except Exception as e:
                    print(f"[{self.name}] Error executing task {task_id} with LlamaIndex agent: {e}")
                    traceback.print_exc()
                    result_data = f"Error executing task: {str(e)}"

                if reply_to and self.transport:
                    target_agent_name = reply_to
                    if isinstance(reply_to, str) and '/' in reply_to:
                         target_agent_name = reply_to.split('/')[-1]

                    response_message = {
                        "type": "task_result",
                        "task_id": task_id,
                        "result": result_data,
                        "sender": self.name,
                        "original_message_id": original_message_id
                    }
                    try:
                        await self.transport.send_message(target_agent_name, response_message)
                        print(f"[{self.name}] Sent result for task {task_id} to {target_agent_name}")
                    except Exception as e:
                        print(f"[{self.name}] Failed to send result for task {task_id} to {target_agent_name}: {e}")
                        traceback.print_exc()
                else:
                    print(f"[{self.name}] No reply_to for task {task_id}, or transport not available. Result: {result_data}")

                if original_message_id and self.transport:
                    await self.transport.acknowledge_message(self.name, original_message_id)
                    print(f"[{self.name}] Acknowledged original message {original_message_id} for task {task_id}")

                super()._mark_task_completed(task_id)
                self.task_queue.task_done()

            except asyncio.CancelledError:
                print(f"[{self.name}] Task processor cancelled.")
                break
            except Exception as e:
                print(f"[{self.name}] Error in task processor: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)
        print(f"[{self.name}] Task processor loop finished.")

    async def _client_message_receiver(self):
        """
        Dedicated loop for receiving messages when in client mode.
        """
        if not self.transport or not self.client_mode:
            print(f"[{self.name}] Message receiver not started (not in client mode or no transport).")
            return

        print(f"[{self.name}] Client message receiver loop started.")
        while True:
            try:
                message, message_id = await self.transport.receive_message() # Pass self.name if needed
                if message:
                    await self.handle_incoming_message(message, message_id)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                print(f"[{self.name}] Client message receiver cancelled.")
                break
            except Exception as e:
                print(f"[{self.name}] Error in client message receiver: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)
        print(f"[{self.name}] Client message receiver loop finished.")

    async def run(self):
        """
        Run the agent's main loop.
        """
        print(f"[{self.name}] Starting LlamaIndexMcpAdapter run loop...")
        if not self.transport and self.client_mode:
            print(f"[ERROR] [{self.name}] Transport not configured. Cannot run in client mode.")
            return

        self._task_processor_task = asyncio.create_task(self.process_tasks())
        print(f"[{self.name}] Task processor created.")

        if self.client_mode and self.transport:
            self._message_processor_task = asyncio.create_task(self._client_message_receiver())
            print(f"[{self.name}] Client message receiver created.")

        running_tasks = [t for t in [self._task_processor_task, self._message_processor_task] if t is not None]
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)
        else:
            print(f"[{self.name}] No processing tasks started. Agent may be idle or misconfigured.")


    async def stop(self):
        """
        Stop the agent's loops gracefully.
        """
        print(f"[{self.name}] Stopping LlamaIndexMcpAdapter...")
        if self._message_processor_task and not self._message_processor_task.done():
            self._message_processor_task.cancel()
        if self._task_processor_task and not self._task_processor_task.done():
            self._task_processor_task.cancel()

        if self.task_queue:
            await self.task_queue.put(None)

        await asyncio.gather(
            *(t for t in [self._task_processor_task, self._message_processor_task] if t),
            return_exceptions=True
        )
        print(f"[{self.name}] LlamaIndexMcpAdapter stopped.")

    async def connect_to_mcp_server(self, server_url: str, registration_payload: Optional[Dict[str, Any]] = None):
        if not self.client_mode or not self.transport:
            raise ValueError("Agent is not in client mode or transport is not set.")
        if not hasattr(self.transport, 'send_message'):
            raise NotImplementedError("Transport does not support send_message for registration.")

        default_payload = {
            "type": "register_agent",
            "agent_id": self.mcp_id,
            "name": self.name,
            "capabilities": ["llama_index_processing"], # Example
            "address": self.transport.get_address() if hasattr(self.transport, 'get_address') else None
        }
        payload = {**default_payload, **(registration_payload or {})}

        try:
            response = await self.transport.send_message(server_url, payload)
            print(f"[{self.name}] Registration response from {server_url}: {response}")
            if not self._message_processor_task or self._message_processor_task.done():
                 self._message_processor_task = asyncio.create_task(self._client_message_receiver())
                 print(f"[{self.name}] Client message receiver started after registration.")
        except Exception as e:
            print(f"[{self.name}] Failed to register with MCP server at {server_url}: {e}")
            traceback.print_exc()
