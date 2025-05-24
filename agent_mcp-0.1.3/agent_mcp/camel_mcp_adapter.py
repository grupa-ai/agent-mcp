"""
Adapter for Camel AI agents to work with MCP.
"""

import asyncio
from typing import Dict, Any, Optional
from .mcp_agent import MCPAgent
from .mcp_transport import MCPTransport
from camel.agents import ChatAgent  # Import the core Camel AI agent
import traceback
import json
import uuid

# --- Setup Logger ---
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# --- End Logger Setup ---

class CamelMCPAdapter(MCPAgent):
    """Adapter for Camel AI ChatAgent to work with MCP"""

    def __init__(self,
                 name: str,
                 transport: Optional[MCPTransport] = None,
                 client_mode: bool = False,
                 camel_agent: ChatAgent = None,  # Expect a Camel ChatAgent instance
                 system_message: str = "",
                 **kwargs):
        # Set default system message if none provided and agent doesn't have one
        if not system_message and camel_agent and hasattr(camel_agent, 'system_message') and not camel_agent.system_message:
            system_message = "I am a Camel AI agent ready to assist."
        elif not system_message:
             system_message = "I am a Camel AI agent ready to assist."

        # Initialize parent with system message
        # Use provided system_message or agent's if available
        effective_system_message = system_message or (camel_agent.system_message.content if camel_agent and camel_agent.system_message else "Camel AI Assistant")
        super().__init__(name=name, system_message=effective_system_message, **kwargs)

        # Set instance attributes
        self.transport = transport
        self.client_mode = client_mode
        self.camel_agent = camel_agent # Store the Camel ChatAgent
        self.task_queue = asyncio.Queue()
        self._task_processor = None
        self._message_processor = None
        self._processed_tasks = set()  # For idempotency check

        if not self.camel_agent:
            raise ValueError("A camel.agents.ChatAgent instance must be provided.")

    async def connect_to_server(self, server_url: str):
        """Connect to another agent's server"""
        if not self.client_mode or not self.transport:
            raise ValueError("Agent not configured for client mode")

        # Register with the server
        registration = {
            "type": "registration",
            "agent_id": self.mcp_id,
            "name": self.name,
            "capabilities": [] # Define capabilities based on agent if needed
        }

        response = await self.transport.send_message(server_url, registration)
        if response.get("status") == "ok":
            print(f"Successfully connected to server at {server_url}")
# transport message format
    async def handle_incoming_message(self, message: Dict[str, Any], message_id: Optional[str] = None):
        """Handle incoming messages from other agents"""
        # First check if type is directly in the message
        msg_type = message.get("type")
        logger.info(f"[{self.name}] Raw message: {message}")

        # If not, check if it's inside the content field
        if not msg_type and "content" in message and isinstance(message["content"], dict):
            msg_type = message["content"].get("type")

        # Extract sender with nested JSON support
        sender = self._extract_sender(message)
        task_id = message.get("task_id") or message.get("content", {}).get("task_id") if isinstance(message.get("content"), dict) else message.get("task_id")
        logger.info(f"[{self.name}] Received message (ID: {message_id}) of type '{msg_type}' from {sender} (Task ID: {task_id})")

        # --- Idempotency Check ---
        if not super()._should_process_message(message):
            # If skipped, acknowledge and stop
            if message_id and self.transport:
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                logger.info(f"[{self.name}] Acknowledged duplicate task {task_id} (msg_id: {message_id})")
            return
        # --- End Idempotency Check ---

        if msg_type == "task":
            logger.info(f"[{self.name}] Queueing task {task_id} (message_id: {message_id}) from {sender}")
            content = message.get("content", {})
            # Ensure task_id and description are retrieved correctly from nested content if necessary
            current_task_id = content.get("task_id", message.get("task_id"))
            description = content.get("description", message.get("description"))
            reply_to = content.get("reply_to", message.get("reply_to"))

            if not current_task_id or not description:
                logger.error(f"[{self.name}] Task message missing required fields (task_id or description): {message}")
                # Acknowledge if possible, even if invalid, to prevent reprocessing
                if message_id and self.transport:
                     asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                return

            # Add message_id to task context for later acknowledgement
            task_context = {
                "type": "task", # Explicitly set type for process_tasks
                "task_id": current_task_id,
                "description": description,
                "reply_to": reply_to,
                "sender": sender,
                "message_id": message_id, # Store message_id for acknowledgement
                "original_message": message # Store original for context if needed
            }

            logger.debug(f"[{self.name}] Queueing task context: {task_context}")
            await self.task_queue.put(task_context)
            logger.debug(f"[{self.name}] Successfully queued task {current_task_id}")

        elif msg_type == "task_result":
            # Received a result, treat it as the next step in the conversation
            result_content = message.get("result")
            
            # --- Robust extraction for various formats ---
            content = message.get("content")
            if result_content is None and content is not None:
                # 1. Try content["result"]
                if isinstance(content, dict) and "result" in content:
                    result_content = content["result"]
                # 2. Try content["text"] as JSON
                elif isinstance(content, dict) and "text" in content:
                    text_val = content["text"]
                    if isinstance(text_val, str):
                        try:
                            parsed = json.loads(text_val)
                            if isinstance(parsed, dict) and "result" in parsed:
                                result_content = parsed["result"]
                        except Exception:
                            pass
                # 3. Try content itself as JSON string
                elif isinstance(content, str):
                    try:
                        parsed = json.loads(content)
                        if isinstance(parsed, dict) and "result" in parsed:
                            result_content = parsed["result"]
                    except Exception:
                        pass
                # 4. Fallback: use content["text"] as plain string
                if result_content is None and isinstance(content, dict) and "text" in content:
                    result_content = content["text"]

            # Add direct parsing of content["text"] structure
            if isinstance(result_content, str):
                try:
                    text_content = json.loads(result_content)
                    if isinstance(text_content, dict):
                        result_content = text_content
                except json.JSONDecodeError:
                    pass

            # Handle JSON string content
            if isinstance(result_content, str):
                try:
                    result_content = json.loads(result_content)
                except json.JSONDecodeError:
                    pass

            original_task_id = (
                (result_content.get("task_id") if isinstance(result_content, dict) else None)
                or message.get("task_id")
            )
            logger.info(f"[{self.name}] Received task_result from {sender} for task {original_task_id}. Content: '{str(result_content)[:100]}...'")

            if not result_content:
                logger.warning(f"[{self.name}] Received task_result from {sender} with empty content.")
                # Acknowledge the result message even if content is empty
                if message_id and self.transport:
                    asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                return

            # Create a *new* task for this agent based on the received result
            new_task_id = f"conv_{uuid.uuid4()}" # Generate a new ID for this conversational turn
            new_task_context = {
                "type": "task", # Still a task for this agent to process
                "task_id": new_task_id,
                "description": str(result_content), # The result becomes the new input/description
                "reply_to": message.get("reply_to") or result_content.get("reply_to"),
                "sender": sender, # This agent is the conceptual sender of this internal task
                "message_id": message_id # Carry over original message ID for acknowledgement
            }

            logger.info(f"[{self.name}] Queueing new conversational task {new_task_id} based on result from {sender}")
            await self.task_queue.put(new_task_context)
            logger.debug(f"[{self.name}] Successfully queued new task {new_task_id}")

        else:
            logger.warning(f"[{self.name}] Received unknown message type: {msg_type}. Message: {message}")
            # Acknowledge non-task messages immediately if they have an ID
            if message_id and self.transport:
                 asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))

# message processor loop making sure the message is a dictionary and then processing it
    async def process_messages(self):
        logger.info(f"[{self.name}] Message processor loop started.")
        while True:
            try:
                logger.debug(f"[{self.name}] Waiting for message from transport...")
                # Get message from transport (without agent_name parameter)
                message, message_id = await self.transport.receive_message()
                logger.debug(f"[{self.name}] Received raw message from transport: {message} (ID: {message_id})")


                if message is None:
                    logger.debug(f"[{self.name}] Received None message, continuing loop...")
                    await asyncio.sleep(0.1) # Avoid busy-waiting
                    continue

                # Ensure message is a dictionary before proceeding
                if not isinstance(message, dict):
                    logger.error(f"[{self.name}] Received non-dict message: {message} (type: {type(message)}), skipping.")
                    # Attempt to acknowledge if possible
                    if message_id and self.transport:
                         asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                    continue

                logger.info(f"[{self.name}] Processing message {message_id}: {message}")
                await self.handle_incoming_message(message, message_id)

            except asyncio.CancelledError:
                logger.info(f"[{self.name}] Message processor cancelled.")
                break
            except Exception as e:
                logger.error(f"[{self.name}] Error in message processor: {e}", exc_info=True)
                traceback.print_exc()
                # Avoid immediate exit on error, maybe add a delay
                await asyncio.sleep(1)
        logger.info(f"[{self.name}] Message processor loop finished.")


    async def process_tasks(self):
        logger.info(f"[{self.name}] Task processor loop started.")
        while True:
            try:
                logger.debug(f"[{self.name}] Waiting for task from queue...")
                task_context = await self.task_queue.get()
                logger.info(f"\n[{self.name}] Dequeued item from task queue: {task_context}")

                if not isinstance(task_context, dict):
                    logger.error(f"[{self.name}] Task item is not a dictionary: {task_context}")
                    self.task_queue.task_done()
                    continue

                # Extract task details from the context dictionary
                task_desc = task_context.get("description")
                task_id = task_context.get("task_id")
                reply_to = task_context.get("reply_to")
                message_id = task_context.get("message_id") # Retrieve message_id for ack
                task_type = task_context.get("type") # Should be 'task'

                logger.info(f"[{self.name}] Processing task details:")
                logger.info(f"  - Task ID: {task_id}")
                logger.info(f"  - Type: {task_type}")
                logger.info(f"  - Reply To: {reply_to}")
                logger.info(f"  - Description: {str(task_desc)[:100]}...")
                logger.info(f"  - Original Message ID: {message_id}")

                if not task_desc or not task_id:
                    logger.error(f"[{self.name}] Task context missing description or task_id: {task_context}")
                    self.task_queue.task_done()
                     # Acknowledge message even if task context is bad
                    if message_id and self.transport:
                         asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                         logger.warning(f"[{self.name}] Acknowledged message {message_id} for invalid task context.")
                    continue
                
                # Ensure it's actually a task we should process
                if task_type != "task":
                    logger.error(f"[{self.name}] Invalid item type in task queue: {task_type}. Item: {task_context}")
                    self.task_queue.task_done()
                    if message_id and self.transport:
                        asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                    continue

                logger.info(f"[{self.name}] Starting execution of task {task_id}: '{str(task_desc)[:50]}...'" )

                # --- Execute task using Camel AI agent ---
                result_str = None
                try:
                    logger.debug(f"[{self.name}] Calling camel_agent.astep with task description...")
                    # Use astep for asynchronous execution if available, otherwise step
                    if hasattr(self.camel_agent, 'astep'):
                        response = await self.camel_agent.astep(task_desc)
                    else:
                        # Fallback to synchronous step in executor if astep not available
                        # Note: This blocks the task processor loop. Consider running in executor.
                        logger.warning(f"[{self.name}] Camel agent does not have 'astep'. Using synchronous 'step'. This may block.")
                        # For safety, run sync 'step' in an executor to avoid blocking asyncio loop
                        loop = asyncio.get_running_loop()
                        response = await loop.run_in_executor(None, self.camel_agent.step, task_desc)


                    # Extract content from the response object
                    # Assuming response has a 'msg' attribute with 'content' based on docs example
                    if response and hasattr(response, 'msg') and hasattr(response.msg, 'content'):
                        result_str = response.msg.content
                        logger.debug(f"[{self.name}] Camel agent execution successful. Result: '{str(result_str)[:100]}...'" )
                    elif response and hasattr(response, 'messages') and response.messages:
                        # Handle cases where response might be a list of messages (e.g., RolePlaying)
                        # Take the last message content as the result for simplicity
                        last_msg = response.messages[-1]
                        if hasattr(last_msg, 'content'):
                           result_str = last_msg.content
                           logger.debug(f"[{self.name}] Camel agent execution successful (from messages). Result: '{str(result_str)[:100]}...'" )
                        else:
                            logger.warning(f"[{self.name}] Camel agent response's last message has no 'content'. Response: {response}")
                            result_str = str(response) # Fallback
                    elif response:
                         logger.warning(f"[{self.name}] Camel agent response format unexpected. Using str(response). Response: {response}")
                         result_str = str(response) # Fallback to string representation
                    else:
                        logger.warning(f"[{self.name}] Camel agent returned None or empty response.")
                        result_str = "Agent returned no response."


                except Exception as e:
                    logger.error(f"[{self.name}] Camel agent execution failed for task {task_id}: {e}", exc_info=True)
                    traceback.print_exc()
                    result_str = f"Agent execution failed due to an error: {str(e)}"

                # Ensure result is always a string before sending
                if not isinstance(result_str, str):
                    try:
                        result_str = json.dumps(result_str) # Try serializing complex types
                    except (TypeError, OverflowError):
                        result_str = str(result_str) # Fallback

                logger.info(f"[{self.name}] Sending result for task {task_id} to {reply_to}")
                # --- Send the result back ---
                if reply_to and self.transport:
                    try:
                        # Extract target agent name from reply_to (assuming format http://.../agent_name)
                        target_agent_name = reply_to # Default if parsing fails
                        try:
                            target_agent_name = reply_to.split('/')[-1]
                            if not target_agent_name: # Handle trailing slash case
                                target_agent_name = reply_to.split('/')[-2]
                        except IndexError:
                            logger.warning(f"[{self.name}] Could not reliably extract agent name from reply_to URL: {reply_to}. Using full URL.")


                        logger.debug(f"[{self.name}] Sending result to target agent: {target_agent_name} (extracted from {reply_to})")

                        await self.transport.send_message(
                            target_agent_name, # Send to the specific agent name/ID
                            {
                                "type": "task_result",
                                "task_id": task_id,
                                "result": result_str,
                                "sender": self.name,
                                "reply_to": self.name,  # Add this so the receiving agent knows where to send follow-up messages
                                "original_message_id": message_id # Include original message ID for tracing/ack
                            }
                        )
                        logger.debug(f"[{self.name}] Result sent successfully for task {task_id}")

                        # Acknowledge task completion *after* sending result, using message_id
                        if message_id:
                            await self.transport.acknowledge_message(self.name, message_id)
                            logger.info(f"[{self.name}] Task {task_id} acknowledged via message_id {message_id}")
                        else:
                            logger.warning(f"[{self.name}] No message_id found for task {task_id} in context, cannot acknowledge transport message.")

                    except Exception as send_error:
                        logger.error(f"[{self.name}] Failed to send result or acknowledge for task {task_id}: {send_error}", exc_info=True)
                        traceback.print_exc()
                        # Decide if task should be retried or marked done despite send failure
                        # For now, mark done to avoid loop, but log error clearly
                else:
                    logger.warning(f"[{self.name}] No reply_to address or transport configured for task {task_id}. Cannot send result or acknowledge.")
                    # If no reply_to, we might still need to acknowledge if we have a message_id
                    if message_id and self.transport:
                         logger.warning(f"[{self.name}] Acknowledging message {message_id} for task {task_id} even though result wasn't sent (no reply_to)." )
                         await self.transport.acknowledge_message(self.name, message_id)


                # Mark task as completed internally *after* processing and attempting send/ack
                super()._mark_task_completed(task_id) # Call base class method

                self.task_queue.task_done()
                logger.info(f"[{self.name}] Task {task_id} fully processed and marked done.")

            except asyncio.CancelledError:
                logger.info(f"[{self.name}] Task processor cancelled.")
                break
            except Exception as e:
                logger.error(f"[{self.name}] Unhandled error in task processing loop: {e}", exc_info=True)
                traceback.print_exc()
                # Ensure task_done is called even in unexpected error to prevent queue blockage
                try:
                    self.task_queue.task_done()
                except ValueError: # Already done
                    pass
                await asyncio.sleep(1) # Prevent fast error loop

        logger.info(f"[{self.name}] Task processor loop finished.")

    # --- Helper methods inherited or overridden from MCPAgent ---
    # _should_process_message and _mark_task_completed are inherited from MCPAgent
    # but shown here for clarity from the original langchain adapter template.
    # We rely on the super() calls within handle_incoming_message and process_tasks.

    # def _should_process_message(self, message: Dict[str, Any]) -> bool:
    #     """Check if a message should be processed based on idempotency"""
    #     # Implementation relies on MCPAgent's base method via super()

    # def _mark_task_completed(self, task_id: str) -> None:
    #     """Mark a task as completed for idempotency tracking"""
    #     # Implementation relies on MCPAgent's base method via super()

    async def run(self):
        """Start the agent's message and task processing loops."""
        if not self.transport:
            raise ValueError("Transport must be configured to run the agent.")

        logger.info(f"[{self.name}] Starting CamelMCPAdapter run loop...")

        # Start the message processing loop
        self._message_processor = asyncio.create_task(self.process_messages())
        # Start the task processing loop
        self._task_processor = asyncio.create_task(self.process_tasks())

        try:
            # Keep running until tasks are cancelled
            await asyncio.gather(self._message_processor, self._task_processor)
        except asyncio.CancelledError:
            logger.info(f"[{self.name}] Agent run loop cancelled.")
        finally:
            logger.info(f"[{self.name}] Agent run loop finished.")

    async def stop(self):
        """Stop the agent's processing loops gracefully."""
        logger.info(f"[{self.name}] Stopping agent...")
        if self._message_processor and not self._message_processor.done():
            self._message_processor.cancel()
        if self._task_processor and not self._task_processor.done():
            self._task_processor.cancel()

        # Wait for tasks to finish cancelling
        try:
            await asyncio.gather(self._message_processor, self._task_processor, return_exceptions=True)
        except asyncio.CancelledError:
            pass # Expected
        logger.info(f"[{self.name}] Agent stopped.")

# Example Usage (for demonstration purposes, would normally be in a separate script)
# async def main():
#     # Requires setting up a transport (e.g., MCPTransport)
#     # Requires creating a Camel ChatAgent instance
#     from camel.models import ModelFactory
#     from camel.types import ModelType
#     import os
#
#     # Ensure API key is set
#     # os.environ["OPENAI_API_KEY"] = "your_key_here"
#
#     # 1. Create a Camel ChatAgent
#     model = ModelFactory.create(model_type=ModelType.GPT_4O_MINI)
#     camel_agent_instance = ChatAgent(system_message="You are a helpful geography expert.", model=model)
#
#     # 2. Create a transport (replace with actual transport implementation)
#     class MockTransport(MCPTransport): # Replace with your actual transport
#         async def send_message(self, target: str, message: Dict[str, Any]):
#             print(f"[MockTransport] Sending to {target}: {message}")
#             # Simulate response for registration
#             if message.get("type") == "registration":
#                 return {"status": "ok"}
#             return {"status": "sent"}
#         async def receive_message(self):
#             print("[MockTransport] receive_message called, simulating task...")
#             await asyncio.sleep(5) # Simulate delay
#             # Simulate receiving a task message
#             return {
#                 "type": "task",
#                 "task_id": "task-123",
#                 "description": "What is the capital of France?",
#                 "sender": "user_agent",
#                 "reply_to": "http://localhost:8000/user_agent" # Example reply URL
#             }, "msg-abc" # Message and ID
#         async def acknowledge_message(self, agent_id: str, message_id: str):
#              print(f"[MockTransport] Acknowledging message {message_id} for agent {agent_id}")
#         async def connect(self): pass
#         async def disconnect(self): pass
#
#     transport_instance = MockTransport()
#
#     # 3. Create the adapter
#     adapter = CamelMCPAdapter(
#         name="CamelGeographyAgent",
#         transport=transport_instance,
#         camel_agent=camel_agent_instance
#     )
#
#     # 4. Run the adapter
#     print("Starting CamelMCPAdapter...")
#     try:
#         await adapter.run()
#     except KeyboardInterrupt:
#         await adapter.stop()
#     print("Adapter finished.")
#
# if __name__ == "__main__":
#      # Note: Requires OPENAI_API_KEY environment variable to be set
#      # if os.getenv("OPENAI_API_KEY"):
#      #    asyncio.run(main())
#      # else:
#      #    print("Please set the OPENAI_API_KEY environment variable to run the example.")
#      pass # Keep example code commented out in the main file 