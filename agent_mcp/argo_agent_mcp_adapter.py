import asyncio
import traceback
import json
from typing import Dict, Any, Optional, Callable

from .mcp_agent import MCPAgent
from .mcp_transport import MCPTransport # Assuming HTTPTransport or a base MCPTransport

# --- Placeholder for Argo Agent ---
class PlaceholderArgoAgent:
    """
    A placeholder for the actual Argo Agent class.
    This will be replaced with the real Argo Agent implementation.
    """
    def __init__(self, name: str, **kwargs):
        self.name = name
        print(f"PlaceholderArgoAgent '{self.name}' initialized with kwargs: {kwargs}")

    async def execute_task(self, task_description: str, **kwargs) -> str:
        """
        Simulates executing a task.
        """
        print(f"PlaceholderArgoAgent '{self.name}' executing task: {task_description} with kwargs: {kwargs}")
        # In a real scenario, this would interact with the Argo agent's core logic
        await asyncio.sleep(1) # Simulate async work
        return f"Result for task '{task_description}' from {self.name}"

    async def arun(self, task_description: str, **kwargs) -> str:
        """
        Alternative execution method, similar to what might be expected.
        """
        return await self.execute_task(task_description, **kwargs)

# --- End Placeholder for Argo Agent ---

class ArgoAgentMcpAdapter(MCPAgent):
    """
    Adapter for Argo Agents to work with MCP.
    """

    def __init__(self,
                 name: str,
                 argo_agent: PlaceholderArgoAgent, # Will be the actual Argo Agent type
                 transport: Optional[MCPTransport] = None,
                 client_mode: bool = False, # Typically true if connecting to a central MCP server
                 system_message: str = "I am an Argo agent integrated with MCP.",
                 **kwargs):
        super().__init__(name=name, system_message=system_message, **kwargs)

        self.argo_agent = argo_agent
        self.transport = transport
        self.client_mode = client_mode
        self.task_queue = asyncio.Queue()
        self._task_processor_task = None
        self._message_processor_task = None # For client mode message receiving

        # If transport is provided and it has a server component (e.g. HTTPTransport for server mode)
        # This part would be more relevant if this adapter itself runs a server
        # For now, focusing on client_mode where it sends messages and receives via polling or callbacks
        if self.transport and not self.client_mode and hasattr(self.transport, "app"):
            # Example: self.transport.add_route("/argo_message", self.handle_http_message)
            pass

    async def handle_incoming_message(self, message: Dict[str, Any], message_id: Optional[str] = None):
        """
        Handle incoming messages from other agents via MCP.
        This method is called by the transport layer or a message processing loop.
        """
        msg_type = message.get("type")
        sender = self._extract_sender(message) # Using protected method from MCPAgent
        task_id = message.get("task_id") or message.get("content", {}).get("task_id")

        print(f"[{self.name}] Received message (ID: {message_id}) of type '{msg_type}' from {sender} (Task ID: {task_id})")

        if not super()._should_process_message(message): # Idempotency check from MCPAgent
            if message_id and self.transport:
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
            print(f"[{self.name}] Skipped duplicate task {task_id} (msg_id: {message_id})")
            return

        if msg_type == "task":
            content = message.get("content", {})
            description = content.get("description") or message.get("description") # Compatibility
            reply_to = content.get("reply_to") or message.get("reply_to")

            if not task_id or not description:
                print(f"[{self.name}] Task message missing required fields: {message}")
                if message_id and self.transport:
                    asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                return

            # Add original message_id to task context for acknowledgement later
            task_context = {
                "type": "task",
                "task_id": task_id,
                "description": description,
                "reply_to": reply_to,
                "sender": sender,
                "original_message_id": message_id # Important for ACK
            }
            await self.task_queue.put(task_context)
            print(f"[{self.name}] Queued task {task_id} from {sender}")

        elif msg_type == "task_result":
            # Argo agents might act on results, or this could be handled by a workflow manager
            print(f"[{self.name}] Received task_result: {message}")
            # Acknowledge the result message
            if message_id and self.transport:
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
            # Further processing of task_result can be added here if needed

        else:
            print(f"[{self.name}] Received unknown message type: {msg_type}. Message: {message}")
            if message_id and self.transport: # Acknowledge other messages too
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))

    async def process_tasks(self):
        """
        Process tasks from the internal queue using the Argo agent.
        """
        print(f"[{self.name}] Task processor loop started.")
        while True:
            try:
                task_context = await self.task_queue.get()
                if task_context is None: # Sentinel for stopping
                    break

                task_id = task_context.get("task_id")
                description = task_context.get("description")
                reply_to = task_context.get("reply_to")
                original_message_id = task_context.get("original_message_id")

                print(f"[{self.name}] Processing task {task_id}: {description}")

                try:
                    # Execute task using the Argo agent's method
                    # Assuming argo_agent has an async method like 'arun' or 'execute_task'
                    result_data = await self.argo_agent.arun(task_description=description)
                except Exception as e:
                    print(f"[{self.name}] Error executing task {task_id} with Argo agent: {e}")
                    traceback.print_exc()
                    result_data = f"Error executing task: {str(e)}"
                    # Optionally, send error back to requester

                # Send the result back
                if reply_to and self.transport:
                    # The target_agent_name for send_message should be the agent's registered MCP name
                    # If reply_to is a full URL, extract the agent name part if necessary,
                    # or ensure the transport handles it.
                    target_agent_name = reply_to # Assuming reply_to is the MCP agent name/ID
                    if isinstance(reply_to, str) and '/' in reply_to: # Basic check if it's a URL path
                         target_agent_name = reply_to.split('/')[-1]


                    response_message = {
                        "type": "task_result",
                        "task_id": task_id,
                        "result": result_data,
                        "sender": self.name,
                        "original_message_id": original_message_id # For tracing/ACK by receiver
                    }
                    try:
                        await self.transport.send_message(target_agent_name, response_message)
                        print(f"[{self.name}] Sent result for task {task_id} to {target_agent_name}")
                    except Exception as e:
                        print(f"[{self.name}] Failed to send result for task {task_id} to {target_agent_name}: {e}")
                        traceback.print_exc()
                else:
                    print(f"[{self.name}] No reply_to for task {task_id}, or transport not available. Result: {result_data}")

                # Acknowledge the original task message after processing
                if original_message_id and self.transport:
                    await self.transport.acknowledge_message(self.name, original_message_id)
                    print(f"[{self.name}] Acknowledged original message {original_message_id} for task {task_id}")

                super()._mark_task_completed(task_id) # Mark task as completed for idempotency
                self.task_queue.task_done()

            except asyncio.CancelledError:
                print(f"[{self.name}] Task processor cancelled.")
                break
            except Exception as e:
                print(f"[{self.name}] Error in task processor: {e}")
                traceback.print_exc()
                # Avoid continuous fast error loops
                await asyncio.sleep(1)
        print(f"[{self.name}] Task processor loop finished.")

    async def _client_message_receiver(self):
        """
        Dedicated loop for receiving messages when in client mode and transport supports it.
        This is typically used with transports that require polling or a persistent connection.
        """
        if not self.transport or not self.client_mode:
            print(f"[{self.name}] Message receiver not started (not in client mode or no transport).")
            return

        print(f"[{self.name}] Client message receiver loop started.")
        while True:
            try:
                # This assumes transport.receive_message() is designed for polling
                # and will block until a message is received or a timeout occurs (if configured).
                # The first element of the tuple is the message, the second is the message_id.
                message, message_id = await self.transport.receive_message() # Pass self.name if required by transport
                if message:
                    await self.handle_incoming_message(message, message_id)
                else:
                    # transport.receive_message() might return None on timeout or clean disconnect
                    await asyncio.sleep(0.1) # Brief pause before next poll if no message
            except asyncio.CancelledError:
                print(f"[{self.name}] Client message receiver cancelled.")
                break
            except Exception as e:
                print(f"[{self.name}] Error in client message receiver: {e}")
                traceback.print_exc()
                await asyncio.sleep(1) # Wait before retrying on error
        print(f"[{self.name}] Client message receiver loop finished.")


    async def run(self):
        """
        Run the agent's main loop.
        Starts the task processor and, if in client mode, the message receiver.
        """
        print(f"[{self.name}] Starting ArgoAgentMcpAdapter run loop...")
        if not self.transport and self.client_mode:
            # In client mode, transport is essential for communication.
            print(f"[ERROR] [{self.name}] Transport is not configured. Cannot run in client mode without transport.")
            return

        self._task_processor_task = asyncio.create_task(self.process_tasks())
        print(f"[{self.name}] Task processor created.")

        if self.client_mode and self.transport:
            # Start the message receiver loop if in client mode and transport is available
            self._message_processor_task = asyncio.create_task(self._client_message_receiver())
            print(f"[{self.name}] Client message receiver created.")

        # Keep the run method alive while processors are running
        # Gather tasks that are actually started
        running_tasks = [t for t in [self._task_processor_task, self._message_processor_task] if t is not None]
        if running_tasks:
            await asyncio.gather(*running_tasks, return_exceptions=True)
        else:
            # If no tasks were started (e.g. not client_mode and no server component started here)
            # This might indicate a configuration issue or a server-only agent that relies on an external runner.
            print(f"[{self.name}] No processing tasks started. Agent may be idle or misconfigured.")


    async def stop(self):
        """
        Stop the agent's loops gracefully.
        """
        print(f"[{self.name}] Stopping ArgoAgentMcpAdapter...")
        if self._message_processor_task and not self._message_processor_task.done():
            self._message_processor_task.cancel()
        if self._task_processor_task and not self._task_processor_task.done():
            self._task_processor_task.cancel()

        # Add sentinel to queue to stop task processor if it's waiting on queue.get()
        if self.task_queue:
            await self.task_queue.put(None)

        # Wait for tasks to finish cancelling
        await asyncio.gather(
            *(t for t in [self._task_processor_task, self._message_processor_task] if t),
            return_exceptions=True
        )
        print(f"[{self.name}] ArgoAgentMcpAdapter stopped.")

    # Example of how one might connect to a server if in client mode
    async def connect_to_mcp_server(self, server_url: str, registration_payload: Optional[Dict[str, Any]] = None):
        if not self.client_mode or not self.transport:
            raise ValueError("Agent is not in client mode or transport is not set.")

        if not hasattr(self.transport, 'send_message'):
            raise NotImplementedError("Transport does not support send_message for registration.")

        default_payload = {
            "type": "register_agent", # Or whatever the MCP server expects
            "agent_id": self.mcp_id,
            "name": self.name,
            "capabilities": ["argo_processing"], # Example capability
            "address": self.transport.get_address() if hasattr(self.transport, 'get_address') else None
        }
        payload = {**default_payload, **(registration_payload or {})}

        try:
            # Assuming the server_url is the MCP name of the server/coordinator
            # or the transport knows how to resolve it.
            response = await self.transport.send_message(server_url, payload)
            print(f"[{self.name}] Registration response from {server_url}: {response}")
            # Potentially start client message receiver loop here if not started automatically
            if not self._message_processor_task or self._message_processor_task.done():
                 self._message_processor_task = asyncio.create_task(self._client_message_receiver())
                 print(f"[{self.name}] Client message receiver started after registration.")

        except Exception as e:
            print(f"[{self.name}] Failed to register with MCP server at {server_url}: {e}")
            traceback.print_exc()
