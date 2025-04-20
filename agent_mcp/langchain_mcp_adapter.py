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
        
        # If not, check if it's inside the content field
        if not msg_type and "content" in message and isinstance(message["content"], dict):
            msg_type = message["content"].get("type")
            
        sender = message.get("sender", "Unknown")
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
            task_id = content.get("task_id") or message.get("task_id")
            description = content.get("description") or message.get("description")
            reply_to = content.get("reply_to")
            
            if not task_id or not description:
                print(f"[ERROR] {self.name}: Task message missing required fields: {message}")
                return
            
            # Add message_id to task
            message['message_id'] = message_id
                
            # Queue task for async processing
            print(f"[DEBUG] {self.name}: Queueing task {task_id} with message_id {message_id} for processing")
            await self.task_queue.put(message)
            print(f"[DEBUG] {self.name}: Successfully queued task {task_id}")
        else:
            print(f"[WARN] {self.name}: Received unknown message type: {msg_type}")
            
    async def _handle_task(self, message: Dict[str, Any]):
        """Handle incoming task"""
        print(f"{self.name}: Received task: {message}")
        await self.task_queue.put(message)
        return {"status": "ok"}
        
    async def process_messages(self):
        print(f"[{self.name}] Message processor loop started.")
        while True:
            try:
                print(f"[{self.name}] Waiting for message from queue...")
                message, message_id = await self.transport.receive_message()
                print(f"{self.name}: Processing message {message_id}: {message}")
                
                # Skip None messages
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
                print(f"\n[{self.name}] Got task from queue: {task}")
                
                if not isinstance(task, dict):
                    print(f"[ERROR] {self.name}: Task is not a dictionary: {task}")
                    self.task_queue.task_done()
                    continue
                
                # Get task details from content field if present
                content = task.get("content", {})
                task_desc = content.get("description") or task.get("description")
                task_id = content.get("task_id") or task.get("task_id")
                task_type = content.get("type") or task.get("type")
                reply_to = content.get("reply_to") or task.get("reply_to")
                
                print(f"[DEBUG] {self.name}: Task details:")
                print(f"  - Type: {task_type}")
                print(f"  - Task ID: {task_id}")
                print(f"  - Reply To: {reply_to}")
                print(f"  - Description: {task_desc}")
                
                if not task_desc or not task_id:
                    print(f"[ERROR] {self.name}: Task is missing description or task_id")
                    self.task_queue.task_done()
                    continue
                    
                if task_type != "task":
                    print(f"[ERROR] {self.name}: Invalid task type: {task_type}")
                    self.task_queue.task_done()
                    continue
                
                print(f"[DEBUG] {self.name}: Starting execution of task {task_id}")
                # Execute task using Langchain agent
                try:
                    print(f"[DEBUG] {self.name}: Calling agent_executor.arun with task description")
                    # Execute the task using the Langchain agent executor
                    #result = await self.agent_executor.arun(task_desc)
                    result = await self.agent_executor.ainvoke({"input": task_desc})
                    print(f"[DEBUG] {self.name}: Agent execution completed. Result type: {type(result)}")
                except Exception as e:
                    print(f"[ERROR] {self.name}: Agent execution failed: {e}")
                    print(f"[ERROR] {self.name}: Error type: {type(e)}")
                    traceback.print_exc() # Print the full traceback for detailed debugging
                    # Provide a user-friendly error message as the result
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
                            target_agent_name = reply_to.split('/')[-1]
                        except IndexError:
                            print(f"[ERROR] {self.name}: Could not extract agent name from reply_to URL: {reply_to}")
                            target_agent_name = reply_to # Fallback, though likely wrong
                            
                        print(f"[DEBUG] {self.name}: Sending result to target agent: {target_agent_name} (extracted from {reply_to})")
                        # --- END FIX ---
                        
                        await self.transport.send_message(
                            target_agent_name, # <<< Use extracted name, not full URL
                            {
                                "type": "task_result",
                                "task_id": task_id,
                                "result": result_str,
                                "sender": self.name,
                                "original_message_id": task.get('message_id')  # Include original message ID
                            }
                        )
                        print(f"[DEBUG] {self.name}: Result sent successfully")
                        
                        # Acknowledge task completion using message_id
                        message_id = task.get('message_id')
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
