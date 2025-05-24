"""
Adapter for Langchain agents to work with MCP.
"""

import asyncio
from typing import Dict, Any, Optional
from .mcp_agent import MCPAgent
from .mcp_transport import MCPTransport
from langchain.agents import AgentExecutor
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent
import traceback
import json
import uuid

# --- Setup Logger ---
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# --- End Logger Setup ---

class LangchainMCPAdapter(MCPAgent):
    """Adapter for Langchain agents to work with MCP"""
    
    def __init__(self, 
                 name: str,
                 transport: Optional[MCPTransport] = None,
                 client_mode: bool = False,
                 langchain_agent: OpenAIFunctionsAgent = None,
                 agent_executor: AgentExecutor = None,
                 system_message: str = "",
                 **kwargs):
        # Set default system message if none provided
        if not system_message:
            system_message = "I am a Langchain agent that can help with various tasks."
            
        # Initialize parent with system message
        super().__init__(name=name, system_message=system_message, **kwargs)
        
        # Set instance attributes
        self.transport = transport
        self.client_mode = client_mode
        self.langchain_agent = langchain_agent
        self.agent_executor = agent_executor
        self.task_queue = asyncio.Queue()
        self._task_processor = None
        self._message_processor = None
        self._processed_tasks = set()  # For idempotency check

    async def connect_to_server(self, server_url: str):
        """Connect to another agent's server"""
        if not self.client_mode or not self.transport:
            raise ValueError("Agent not configured for client mode")
            
        # Register with the server
        registration = {
            "type": "registration",
            "agent_id": self.mcp_id,
            "name": self.name,
            "capabilities": []
        }
        
        response = await self.transport.send_message(server_url, registration)
        if response.get("status") == "ok":
            print(f"Successfully connected to server at {server_url}")
            
    async def handle_incoming_message(self, message: Dict[str, Any], message_id: Optional[str] = None):
        """Handle incoming messages from other agents"""
        # First check if type is directly in the message
        msg_type = message.get("type")
        logger.info(f"[{self.name}] Raw message: {message}")

        # If not, check if it's inside the content field
        if not msg_type and "content" in message and isinstance(message["content"], dict):
            msg_type = message["content"].get("type")
            
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
            current_task_id = content.get("task_id") or message.get("task_id") # Handle potential nesting
            description = content.get("description") or message.get("description")
            reply_to = content.get("reply_to") or message.get("reply_to")

            if not current_task_id or not description:
                logger.error(f"[{self.name}] Task message missing required fields: {message}")
                # Acknowledge if possible to prevent reprocessing bad message
                if message_id and self.transport:
                     asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                return

            # Add message_id to task context for processing
            message['message_id'] = message_id

            #task_context = {
            #    "type": "task", # Ensure type is explicitly set for process_tasks
            #    "task_id": current_task_id,
            #    "description": description,
            #    "reply_to": reply_to,
            #    "sender": sender,
            #    "message_id": message_id
            #}
            #logger.debug(f"[{self.name}] Queueing task context: {task_context}")
            logger.debug(f"[DEBUG] {self.name}: Queueing task {task_id} with message_id {message_id} for processing")

            await self.task_queue.put(message)
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

            # Handle JSON string content
            if isinstance(result_content, str):
                try:
                    result_content = json.loads(result_content)
                except json.JSONDecodeError:
                    pass

            # Direct parsing of content["text"] structure
            if isinstance(result_content, str):
                try:
                    text_content = json.loads(result_content)
                    if isinstance(text_content, dict):
                        result_content = text_content
                except json.JSONDecodeError:
                    pass

            # --- End Robust extraction ---
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
            #new_task_id = f"conv_{uuid.uuid4()}" # Generate a new ID for this conversational turn
            #new_task_context = {
            #    "type": "task", # Still a task for this agent to process
            #    "task_id": new_task_id,
            #    "description": str(result_content), # The result becomes the new input/description
            #    "reply_to": message.get("reply_to") or result_content.get("reply_to"),
            #    "sender": sender, # This agent is the conceptual sender of this internal task
            #    "message_id": message_id # Carry over original message ID for acknowledgement
            #}

            #logger.info(f"[{self.name}] Queueing new conversational task {new_task_id} based on result from {sender}")
            #await self.task_queue.put(new_task_context)
            #logger.debug(f"[{self.name}] Successfully queued new task {new_task_id}")

        else:
            logger.warning(f"[{self.name}] Received unknown message type: {msg_type}. Message: {message}")
            # Acknowledge other message types immediately if they have an ID
            #if message_id and self.transport:
            #     asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))

    async def _handle_task(self, message: Dict[str, Any]):
        """Handle incoming task"""
        print(f"{self.name}: Received task: {message}")
        await self.task_queue.put(message)
        return {"status": "ok"}
        
    async def process_messages(self):
        logger.info(f"[{self.name}] Message processor loop started.")
        while True:
            try:
                logger.debug(f"[{self.name}] Waiting for message from transport...")
                # Pass agent name to receive_message
                message, message_id = await self.transport.receive_message()
                logger.debug(f"[{self.name}] Received raw message from transport: {message} (ID: {message_id})")

                if message is None:
                    print(f"[{self.name}] Received None message, skipping...")
                    continue
                    
                await self.handle_incoming_message(message, message_id)
            except asyncio.CancelledError:
                print(f"[{self.name}] Message processor cancelled.")
                break
            except Exception as e:
                print(f"[{self.name}] Error in message processor: {e}")
                traceback.print_exc()
                break
            except Exception as e:
                print(f"[{self.name}] Error in message processor: {e}")
                await asyncio.sleep(1)
        print(f"[{self.name}] Message processor loop finished.")

    async def process_tasks(self):
        print(f"[{self.name}] Task processor loop started.")
        while True:
            try:
                print(f"[{self.name}] Waiting for task from queue...")
                task = await self.task_queue.get()
                print(f"\n[{self.name}] Got item from queue: {task}")
                
                if not isinstance(task, dict):
                    print(f"[ERROR] {self.name}: Task item is not a dictionary: {task}")
                    self.task_queue.task_done()
                    continue
                
                # Extract task details (handle both original message format and task_context format)
                task_desc = task.get("description")
                task_id = task.get("task_id")
                task_type = task.get("type") # Should always be 'task' if queued correctly
                reply_to = task.get("reply_to")
                message_id = task.get("message_id") # For acknowledgement
                sender = self._extract_sender(task)
                # Fallback for nested content (less likely now but safe)
                if not task_desc and isinstance(task.get("content"), dict):
                     content = task.get("content", {})
                     task_desc = content.get("description")
                     if not task_id: task_id = content.get("task_id")
                     if not task_type: task_type = content.get("type")
                     if not reply_to: reply_to = content.get("reply_to")
                     if not sender: sender = content.get("sender", "from")

                print(f"[DEBUG] {self.name}: Processing task details:")
                print(f"  - Task ID: {task_id}")
                print(f"  - Type: {task_type}")
                print(f"  - Sender: {sender}")
                print(f"  - Reply To: {reply_to}")
                print(f"  - Description: {str(task_desc)[:100]}...")
                print(f"  - Original Message ID: {message_id}")
                
                if not task_desc or not task_id:
                    print(f"[ERROR] {self.name}: Task is missing description or task_id: {task}")
                    self.task_queue.task_done()
                    # Acknowledge if possible
                    #if message_id and self.transport:
                    #    asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                    continue
                    
                # We only queue tasks now, so this check might be redundant but safe
                if task_type != "task":
                    print(f"[ERROR] {self.name}: Invalid item type received in task queue: {task_type}. Item: {task}")
                    self.task_queue.task_done()
                    #if message_id and self.transport:
                    #    asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                    continue
                
                print(f"[DEBUG] {self.name}: Starting execution of task {task_id}")
                # Execute task using Langchain agent
                try:
                    print(f"[DEBUG] {self.name}: Calling agent_executor.ainvoke with task description")
                    # Execute the task using the Langchain agent executor's ainvoke method
                    # Pass input AND agent_name in a dictionary matching the prompt's input variables
                    input_data = {
                        "input": task_desc,
                        "agent_name": self.name # Add agent_name here to indicate this agent as the executor (who's currently executing the task)
                    }
                    result_dict = await self.agent_executor.ainvoke(input_data)
                    print(f"[DEBUG] {self.name}: Agent execution completed. Full result: {result_dict}")
                    # Extract the final output string, typically under the 'output' key
                    if isinstance(result_dict, dict) and 'output' in result_dict:
                        result = result_dict['output']
                        print(f"[DEBUG] {self.name}: Extracted output: {result}")
                    else:
                        logger.warning(f"[{self.name}] Could not find 'output' key in agent result: {result_dict}. Using full dict as string.")
                        result = str(result_dict)
                except Exception as e:
                    print(f"[ERROR] {self.name}: Agent execution failed: {e}")
                    print(f"[ERROR] {self.name}: Error type: {type(e)}")
                    traceback.print_exc() # Print the full traceback for detailed debugging
                    # Assign error message to result variable for graceful failure
                    result = f"Agent execution failed due to an error: {str(e)}"

                # Ensure result is always a string before sending
                if not isinstance(result, str):
                    try:
                        result_str = json.dumps(result) # Try serializing if complex type
                    except (TypeError, OverflowError):
                        result_str = str(result) # Fallback to string conversion
                else:
                    result_str = result

                print(f"[DEBUG] {self.name}: Sending task result for task_id: {task_id}")
                # Send the result back
                if reply_to and self.transport:
                    try:
                        # --- FIX: Extract agent name from reply_to URL --- 
                        try:
                            # Handle both URL paths and direct agent names
                            if '/' in reply_to:
                                target_agent_name = reply_to.split('/')[-1]
                            else:
                                target_agent_name = reply_to
                        except IndexError:
                            print(f"[ERROR] {self.name}: Could not extract agent name from reply_to: {reply_to}")
                            target_agent_name = reply_to # Fallback, though likely wrong
                            
                        print(f"[DEBUG] Conversation Routing - Original sender: {reply_to}, Current agent: {self.name}, Final reply_to: {reply_to}")
                        print(f"[DEBUG] Derived target agent: {target_agent_name} from reply_to: {reply_to}")
                        print(f"[DEBUG] TASK_MESSAGE: {task}")
                        print(f"[DEBUG] Message Chain - From: {sender} -> To: {self.name} -> ReplyTo: {reply_to}")
                        
                        print(f"[DEBUG] {self.name}: Sending result to target agent: {target_agent_name} (extracted from {reply_to})")
                        # --- END FIX ---
                        
                        await self.transport.send_message(
                            target_agent_name, # <<< Use extracted name, not full URL
                            {
                                "type": "task_result",
                                "task_id": task_id,
                                "result": result_str,
                                "sender": self.name,
                                "original_message_id": message_id # Include original message ID
                            }
                        )
                        print(f"[DEBUG] {self.name}: Result sent successfully")
                        
                        # Acknowledge task completion using message_id
                        if message_id:
                            await self.transport.acknowledge_message(self.name, message_id)
                            print(f"[DEBUG] {self.name}: Task {task_id} acknowledged with message_id {message_id}")
                        else:
                            print(f"[WARN] {self.name}: No message_id for task {task_id}, cannot acknowledge")
                    except Exception as send_error:
                        print(f"[ERROR] {self.name}: Failed to send result: {str(send_error)}")
                        traceback.print_exc()
                else:
                    print(f"[WARN] {self.name}: No reply_to URL in task {task_id}, cannot send result")
                    
                super()._mark_task_completed(task_id) # Call base class method
                
                self.task_queue.task_done()
                print(f"[DEBUG] {self.name}: Task {task_id} fully processed")
                
            except Exception as e:
                print(f"[ERROR] {self.name}: Error processing task: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)
        print(f"[{self.name}] Task processor loop finished.")

    def _should_process_message(self, message: Dict[str, Any]) -> bool:
        """Check if a message should be processed based on idempotency"""
        task_id = message.get("content", {}).get("task_id") if isinstance(message.get("content"), dict) else message.get("task_id")
        if task_id in self._processed_tasks:
            logger.info(f"[{self.name}] Skipping duplicate task {task_id}")
            return False
        return True

    def _mark_task_completed(self, task_id: str) -> None:
        """Mark a task as completed for idempotency"""
        self._processed_tasks.add(task_id)
        logger.info(f"[{self.name}] Marked task {task_id} as completed")

    async def run(self):
        """Run the agent's main loop asynchronously."""
        print(f"[{self.name}] Starting agent run loop...")
        
        # Ensure transport is ready (polling should be started by HeterogeneousGroupChat)
        if not self.transport:
            print(f"[ERROR] {self.name}: Transport is not configured. Cannot run agent.")
            return

        # We no longer call connect_to_server here, as registration and polling start
        # are handled by HeterogeneousGroupChat._register_and_start_agent
        # if self.client_mode and hasattr(self.transport, 'connect'):
        #     print(f"[{self.name}] Client mode: connecting transport...")
        #     # Assuming connect handles polling start now
        #     await self.transport.connect(agent_name=self.name, token=self.transport.token) 
        # else:
        #     print(f"[{self.name}] Not in client mode or transport does not support connect. Assuming ready.")
            
        # Start message and task processors as background tasks
        try:
            print(f"[{self.name}] Creating message and task processor tasks...")
            self._message_processor = asyncio.create_task(self.process_messages())
            self._task_processor = asyncio.create_task(self.process_tasks())
            print(f"[{self.name}] Processor tasks created.")

            # Wait for either task to complete (or be cancelled)
            # This keeps the agent alive while processors are running
            done, pending = await asyncio.wait(
                [self._message_processor, self._task_processor],
                return_when=asyncio.FIRST_COMPLETED,
            )
            
            print(f"[{self.name}] One of the processor tasks completed or was cancelled.")
            # Handle completion or cancellation if needed
            for task in done:
                try:
                    # Check if task raised an exception
                    exc = task.exception()
                    if exc:
                         print(f"[{self.name}] Processor task ended with error: {exc}")
                         # Optionally re-raise or handle
                except asyncio.CancelledError:
                    print(f"[{self.name}] Processor task was cancelled.")
            
            # Cancel any pending tasks to ensure clean shutdown
            for task in pending:
                 print(f"[{self.name}] Cancelling pending processor task...")
                 task.cancel()
                 try:
                     await task # Await cancellation
                 except asyncio.CancelledError:
                     pass # Expected
                 
        except Exception as e:
            print(f"[ERROR] {self.name}: Unhandled exception in run loop: {e}")
            traceback.print_exc()
        finally:
            print(f"[{self.name}] Agent run loop finished.")
            # Ensure processors are stopped if they weren't already cancelled
            if self._message_processor and not self._message_processor.done():
                self._message_processor.cancel()
            if self._task_processor and not self._task_processor.done():
                self._task_processor.cancel()
            # Note: Transport disconnect should be handled by HeterogeneousGroupChat.shutdown()
