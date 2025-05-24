"""
Enhanced MCP Agent with client/server capabilities.
"""

import asyncio
import collections
from typing import Optional, Dict, Any, List
from .mcp_agent import MCPAgent
from .mcp_transport import MCPTransport

class EnhancedMCPAgent(MCPAgent):
    """MCPAgent with client/server capabilities"""
    
    def __init__(self, 
                 name: str,
                 transport: Optional[MCPTransport] = None,
                 server_mode: bool = False,
                 client_mode: bool = False,
                 **kwargs):
        super().__init__(name=name, **kwargs)
        
        self.transport = transport
        self.server_mode = server_mode
        self.client_mode = client_mode
        self.connected_agents = {}
        self.task_queue = asyncio.Queue()
        self.task_results = {}
        self.task_dependencies = {}
        self._pending_tasks = {}
        self._task_processor = None
        self._message_processor = None
        
    def start_server(self):
        """Start agent in server mode"""
        if not self.server_mode or not self.transport:
            raise ValueError("Agent not configured for server mode")
        
        # Start the transport server
        self.transport.start()
        
    async def connect_to_server(self, server_url: str):
        """Connect to another agent's server"""
        if not self.client_mode or not self.transport:
            raise ValueError("Agent not configured for client mode")
            
        # Register with the server
        registration = {
            "type": "registration",
            "agent_id": self.mcp_id,
            "name": self.name,
            "capabilities": self.list_available_tools()
        }
        
        response = await self.transport.send_message(server_url, registration)
        if response.get("status") == "ok":
            self.connected_agents[server_url] = response.get("server_id")
            print(f"Successfully connected to server at {server_url}")
            
    async def handle_incoming_message(self, message: Dict[str, Any]):
        """Handle incoming messages from other agents"""
        # First check if type is directly in the message
        msg_type = message.get("type")
        
        # If not, check if it's inside the content field
        if not msg_type and "content" in message and isinstance(message["content"], dict):
            msg_type = message["content"].get("type")
            
        print(f"[DEBUG] {self.name}: Received message of type: {msg_type}")
        
        if msg_type == "registration":
            # Handle new agent registration
            await self._handle_registration(message)
        elif msg_type == "tool_call":
            # Handle tool execution request
            await self._handle_tool_call(message)
        elif msg_type == "task":
            # Handle new task assignment
            await self._handle_task(message)
        elif msg_type == "task_result":
            # Handle task result
            print(f"[DEBUG] {self.name}: Processing task_result message: {message}")
            await self._handle_task_result(message)
        elif msg_type == "get_result":
            # Handle get result request
            await self._handle_get_result(message)
        else:
            print(f"[WARN] {self.name}: Received unknown message type: {msg_type}")
            
    async def _handle_registration(self, message: Dict[str, Any]):
        """Handle agent registration"""
        agent_id = message.get("agent_id")
        agent_name = message.get("name")
        capabilities = message.get("capabilities", [])
        
        self.connected_agents[agent_id] = {
            "name": agent_name,
            "capabilities": capabilities
        }
        
        print(f"New agent registered: {agent_name} ({agent_id})")
        return {"status": "ok", "server_id": self.mcp_id}
        
    async def _handle_tool_call(self, message: Dict[str, Any]):
        """Handle tool execution request"""
        tool_name = message.get("tool")
        arguments = message.get("arguments", {})
        
        if tool_name in self.mcp_tools:
            result = await self.execute_tool(tool_name, **arguments)
            return {"status": "ok", "result": result}
        else:
            return {"status": "error", "message": f"Tool {tool_name} not found"}
            
    async def _handle_task(self, message: Dict[str, Any]):
        """Handle incoming task"""
        print(f"[DEBUG] {self.name}: Received task message: {message}")
        
        # --- Idempotency Check ---
        # Check if we should process this message based on task_id
        if not self._should_process_message(message):
            # If not, acknowledge it immediately if possible and stop
            message_id = message.get("message_id")
            if message_id and self.transport:
                # Run acknowledge in background, don't wait
                asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                print(f"[DEBUG] {self.name}: Acknowledged duplicate task {message.get('task_id')} (msg_id: {message_id})")
            return {"status": "skipped", "message": "Task already completed"}
        # --- End Idempotency Check ---
        
        task_id = message.get("task_id") or message.get("content", {}).get("task_id")
        depends_on = message.get("depends_on", [])
        message_id = message.get("message_id")  # Get the message ID for acknowledgment
        
        if not task_id:
            print(f"[ERROR] {self.name}: Received task without task_id: {message}")
            return {"status": "error", "message": "No task_id provided"}
        
        # If this task has dependencies, check if they're met
        if depends_on:
            print(f"[DEBUG] {self.name}: Task {task_id} depends on: {depends_on}")
            # Check if all dependencies are in task_results
            for dep_id in depends_on:
                if dep_id not in self.task_results:
                    print(f"[DEBUG] {self.name}: Dependency {dep_id} not met for task {task_id}, waiting...")
                    return {"status": "waiting", "message": f"Waiting for dependency {dep_id}"}
            print(f"[DEBUG] {self.name}: All dependencies met for task {task_id}")
        
        # Store task info if we're the coordinator
        if self.server_mode:
            print(f"[DEBUG] {self.name}: Storing task {task_id} in coordinator")
            self.task_results[task_id] = None
        
        print(f"[DEBUG] {self.name}: Queueing task {task_id} for processing")
        await self.task_queue.put(message)
        print(f"[DEBUG] {self.name}: Successfully queued task {task_id}")
        
        return {"status": "ok"}
        
    async def _handle_task_result(self, message: Dict[str, Any]):
        """Handle task result from an agent"""
        content = message.get("content", {})
        if isinstance(content, dict) and "text" in content:
            # Handle case where content has a text field containing JSON
            try:
                import json
                text_content = json.loads(content["text"])
                task_id = text_content.get("task_id")
                result = text_content.get("result")
            except (json.JSONDecodeError, AttributeError) as e:
                print(f"[ERROR] {self.name}: Failed to parse text content: {e}")
                task_id = content.get("task_id")
                result = content.get("result")
        else:
            # Normal case - extract directly from content or root
            task_id = content.get("task_id") if isinstance(content, dict) else message.get("task_id")
            result = content.get("result") if isinstance(content, dict) else message.get("result")
        original_message_id = message.get('id')
        sender_name = message.get('from', 'Unknown Sender') 

        print(f"[DEBUG] {self.name}: Handling task result for task_id: {task_id}")
        
        if not task_id:
            print(f"[ERROR] {self.name}: Received task result without task_id: {message}")
            return
            
        print(f"[DEBUG] {self.name}: Received result for task {task_id} from {sender_name} (original_message_id: {original_message_id})")
        
        # Store result
        self.task_results[task_id] = result
        
        # Check for dependent tasks
        if task_id in self.task_dependencies:
            print(f"[DEBUG] {self.name}: Found dependent tasks for {task_id}")
            
            # Get tasks that depend on this one
            task_ids = self.task_dependencies[task_id]
            dependent_tasks = [self._pending_tasks[tid] for tid in task_ids if tid in self._pending_tasks]
            
            # Remove this task from dependencies
            del self.task_dependencies[task_id]
            
            # Process each dependent task
            for dependent_task in dependent_tasks:
                print(f"[DEBUG] {self.name}: Processing dependent task {dependent_task}")
                # Ensure task_info is a dictionary
                if not isinstance(dependent_task, dict):
                    print(f"[WARNING] {self.name}: Skipping invalid task_info (not a dictionary): {dependent_task}")
                    continue
                
                # Check if all dependencies are met
                dependencies = dependent_task.get("depends_on", [])
                all_deps_met = True
                
                for dep in dependencies:
                    if dep not in self.task_results:
                        all_deps_met = False
                        # Re-add to dependencies since not all deps are met
                        task_id = dependent_task.get('task_id')
                        if not task_id:
                            print(f"[WARNING] {self.name}: Skipping task without task_id: {dependent_task}")
                            continue
                        # Add task_id to dependencies and store full task info
                        if dep not in self.task_dependencies:
                            self.task_dependencies[dep] = set()
                        self.task_dependencies[dep].add(task_id)
                        self._pending_tasks[task_id] = dependent_task
                        break
                
                if all_deps_met:
                    task_id = dependent_task.get('task_id')
                    if task_id in self._pending_tasks:
                        full_task = self._pending_tasks[task_id]
                        print(f"[DEBUG] {self.name}: All dependencies met for task {task_id}")
                        # Forward task to agent
                        # Ensure task has proper structure
                        task_to_assign = {
                            "task_id": task_id,
                            "description": full_task.get("description"),
                            "type": "task",
                            "depends_on": dependencies,
                            "content": full_task.get("content", {})
                        }
                        await self.assign_task(full_task["agent"], task_to_assign)
                        # Clean up
                        del self._pending_tasks[task_id]
                for dep in dependencies:
                    if dep not in self.task_results:
                        # Extract fields from content if present
                        content = dependent_task.get("content", {})
                        task_id = content.get("task_id") or dependent_task.get("task_id")
                        description = content.get("description") or dependent_task.get("description")
                        depends_on = content.get("depends_on") or dependent_task.get("depends_on", [])
                        agent = dependent_task.get("agent")
                        
                        if not task_id or not agent or not description:
                            print(f"[ERROR] {self.name}: Missing required fields in dependent task: {dependent_task}")
                            continue
                            
                        # Maintain consistent message structure
                        validated_task_info = {
                            "type": "task",
                            "content": {
                                "task_id": task_id,
                                "description": description,
                                "depends_on": depends_on,
                                "type": "task"
                            },
                            "agent": agent
                        }
                        task_id = validated_task_info.get('task_id')
                        if task_id:
                            if dep not in self.task_dependencies:
                                self.task_dependencies[dep] = set()
                            self.task_dependencies[dep].add(task_id)
                            # Store full task info
                            self._pending_tasks[task_id] = validated_task_info
        
        # Acknowledge the task result if we have the original message ID
        if original_message_id and self.transport:
            try:
                await self.transport.acknowledge_message(self.name, original_message_id)
                print(f"[DEBUG] {self.name}: Acknowledged task result for {task_id} with message_id {original_message_id}")
            except Exception as e:
                print(f"[ERROR] {self.name}: Error acknowledging task result: {e}")
                traceback.print_exc()
        
        return {"status": "ok"}
        
    async def _handle_get_result(self, message: Dict[str, Any]):
        """Handle get result request"""
        task_id = message.get("task_id")
        if task_id in self.task_results:
            return {"status": "ok", "result": self.task_results[task_id]}
        else:
            return {"status": "error", "message": f"Result for task {task_id} not found"}
        
    async def assign_task(self, target_url: str, task: Dict[str, Any]):
        """Assign a task to another agent"""
        print(f"{self.name}: Assigning task {task} to {target_url}")

        # Extract task details from either content or root level
        task_id = task.get("task_id")
        description = task.get("description")
        depends_on = task.get("depends_on", [])
        
        # If task details are in content, use those instead
        if "content" in task and isinstance(task["content"], dict):
            content = task["content"]
            task_id = content.get("task_id", task_id)
            description = content.get("description", description)
            depends_on = content.get("depends_on", depends_on)

        message = {
            "type": "task",
            "content": {
                "task_id": task_id,
                "description": description,
                "depends_on": depends_on,
                "type": "task"
            },
            "from": self.mcp_id
        }
        
        # Only include reply_to if it exists in the task
        if "reply_to" in task:
            message["content"]["reply_to"] = task["reply_to"]
        
        return await self.transport.send_message(target_url, message)
        
    async def process_messages(self):
        """Process incoming messages from transport"""
        print(f"{self.name}: Starting message processor...")
        while True:
            try:
                # Get message with timeout (transport now handles this)
                message, message_id = await self.transport.receive_message()
                
                # Handle timeout case
                if message is None:
                    await asyncio.sleep(0.1)  # Prevent tight loop
                    continue
                    
                # Skip invalid messages
                if not isinstance(message, dict):
                    print(f"{self.name}: Skipping invalid message format: {message}")
                    if message_id:  # Still acknowledge to avoid retries
                        await self.transport.acknowledge_message(self.name, message_id)
                    continue
                    
                print(f"{self.name}: Processing message ID: {message_id}, Type: {message.get('type', 'unknown')}")
                
                # Add message_id for tracking
                message['message_id'] = message_id
                
                try:
                    # Process the message
                    await self.handle_incoming_message(message)
                    
                    # Only acknowledge after successful processing
                    if message_id:
                        await self.transport.acknowledge_message(self.name, message_id)
                        print(f"{self.name}: Acknowledged message {message_id}")
                except Exception as e:
                    print(f"{self.name}: Error handling message {message_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Don't acknowledge on error so it can be retried
                    
            except asyncio.CancelledError:
                print(f"{self.name}: Message processor cancelled")
                break
            except Exception as e:
                print(f"{self.name}: Error in message processor: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1)  # Brief pause on unexpected error

    async def process_tasks(self):
        """Process tasks from the queue"""
        print(f"{self.name}: Starting task processor...")
        while True:
            try:
                task = await self.task_queue.get()
                print(f"{self.name}: Processing task: {task}")
                
                # Get task description and task_id
                task_desc = task.get("description") or task.get("content", {}).get("description") if isinstance(task.get("content"), dict) else task.get("description", "")
                task_id = task.get("task_id") or task.get("content", {}).get("task_id") if isinstance(task.get("content"), dict) else task.get("task_id")
                message_id = task.get('message_id')

                if not task_desc or not task_id:
                    print(f"{self.name}: Error: Task is missing description or task_id")
                    continue

                # Check if this task has dependencies
                depends_on = task.get("depends_on", [])
                if depends_on:
                    print(f"{self.name}: Task {task_id} depends on: {depends_on}")
                    # Check if we have all dependencies
                    missing_deps = []
                    for dep_id in depends_on:
                        if dep_id not in self.task_results:
                            # Try to get dependency result from coordinator
                            if self.transport and self.transport.remote_url:
                                try:
                                    result = await self.transport.send_message(
                                        f"{self.transport.remote_url}/message/{self.name}",
                                        {
                                            "type": "get_result",
                                            "task_id": dep_id, 
                                            "result": "",
                                            "sender": self.name,
                                            "original_message_id": message_id,
                                        }
                                    )
                                    if result and result.get("result"):
                                        self.task_results[dep_id] = result["result"]
                                        continue
                                except Exception as e:
                                    print(f"{self.name}: Error getting dependency result: {e}")
                            
                            missing_deps.append(dep_id)
                    
                    if missing_deps:
                        print(f"{self.name}: Task {task_id} is missing dependencies: {missing_deps}. Putting back in queue.")
                        # Put task back in queue and wait
                        await self.task_queue.put(task)
                        await asyncio.sleep(1)
                        continue
                    
                    # Add dependency results as context
                    task_context = "\nBased on the following findings:\n"
                    for dep_id in depends_on:
                        task_context += f"\nFrom {dep_id}:\n{self.task_results[dep_id]}"
                else:
                    task_context = ""
                
                # Generate response using LLM if configured
                if hasattr(self, 'llm_config') and self.llm_config:
                    print(f"{self.name}: Generating response for task {task_id}...")
                    try:
                        response = self.generate_reply(
                            messages=[{
                                "role": "user",
                                "content": f"Please help with this task: {task_desc}{task_context}"
                            }]
                        )
                        print(f"{self.name}: Generated response for task {task_id}: {response}")
                        
                        # Store result locally
                        self.task_results[task_id] = response
                        
                        # --- Mark task completed for idempotency ---
                        self._mark_task_completed(task_id)
                        # --- End mark task completed ---
                        
                        # Send result back if there's a reply_to
                        if "reply_to" in task and self.transport:
                            try:
                                await self.transport.send_message(
                                    task["reply_to"],
                                    {
                                        "type": "task_result",
                                        "task_id": task_id,
                                        "result": response,
                                        "sender": self.name,
                                        "original_message_id": message_id
                                    }
                                )
                                print(f"{self.name}: Result sent successfully")
                                
                                # Try to acknowledge task completion
                                if "message_id" in task:
                                    await self.transport.acknowledge_message(self.name, task["message_id"])
                                    print(f"{self.name}: Task {task_id} acknowledged with message_id {task['message_id']}")
                            except Exception as send_error:
                                print(f"{self.name}: Error sending result: {send_error}")
                                traceback.print_exc()
                    except Exception as e:
                        print(f"{self.name}: Error generating response: {e}")
                        traceback.print_exc()
                        response = f"Error generating response: {e}"
                    
                    # Send result back if there's a reply_to
                    if "reply_to" in task and self.transport:
                        reply_url = task["reply_to"]
                        print(f"{self.name}: Sending result back to {reply_url}")
                        try:
                            result = await self.transport.send_message(
                                reply_url,
                                {
                                    "type": "task_result",
                                    "task_id": task_id,
                                    "result": response,
                                    "sender": self.name,
                                    "original_message_id": message_id
                                }
                            )
                            print(f"{self.name}: Result sent successfully: {result}")
                            
                            # Store result locally too
                            self.task_results[task_id] = response
                            
                            # Try to acknowledge task completion
                            try:
                                if "message_id" in task:
                                    await self.transport.acknowledge_message(self.name, task["message_id"])
                                    print(f"{self.name}: Acknowledged completion of task {task_id} with message_id {task['message_id']}")
                                else:
                                    print(f"{self.name}: No message_id found for task {task_id}, cannot acknowledge")
                            except Exception as e:
                                print(f"{self.name}: Error acknowledging task completion: {e}")
                                traceback.print_exc()
                        except Exception as e:
                            print(f"{self.name}: Error sending result: {e}")
                            traceback.print_exc()
                        # Store result locally if no reply_to or transport info is available
                        print(f"{self.name}: No reply_to or transport info, storing result locally for task {task_id}")
                        self.task_results[task_id] = response
                
                self.task_queue.task_done()
                
            except Exception as e:
                print(f"{self.name}: Error processing task: {str(e)}")
    
    async def run(self):
        """Run the agent's main loop"""
        if not self.transport:
            raise ValueError("Transport not configured for agent")
            
        # For remote connections, we need to connect() instead of start()
        if hasattr(self.transport, 'is_remote') and self.transport.is_remote:
            # Connect to remote server
            await self.transport.connect(agent_name=self.name)
            # Brief pause to ensure connection is ready
            await asyncio.sleep(1)
        else:
            # For local server, just start it
            self.transport.start()
            
        # Start message and task processing in new tasks
        self._message_processor = asyncio.create_task(
            self.process_messages(),
            name=f"messages_{self.name}"
        )
        self._task_processor = asyncio.create_task(
            self.process_tasks(),
            name=f"tasks_{self.name}"
        )
        
        # Brief pause to let tasks start
        await asyncio.sleep(0.1)
        
        # Create a task to monitor the processors
        monitor_task = asyncio.create_task(
            self._monitor_processors(),
            name=f"monitor_{self.name}"
        )
        
        # Return the monitor task so it can be awaited
        return monitor_task
        
    async def _monitor_processors(self):
        """Monitor the message and task processors"""
        try:
            # Wait for both processors to complete or error
            await asyncio.gather(
                self._message_processor,
                self._task_processor
            )
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            await self.shutdown()
            raise
        except Exception as e:
            print(f"{self.name}: Error in processors: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Shutdown the agent's tasks and disconnect transport"""
        if hasattr(self, '_message_processor'):
            self._message_processor.cancel()
            try:
                await self._message_processor
            except asyncio.CancelledError:
                pass
                
        if hasattr(self, '_task_processor'):
            self._task_processor.cancel()
            try:
                await self._task_processor
            except asyncio.CancelledError:
                pass
                
        # Disconnect transport if remote
        if hasattr(self.transport, 'is_remote') and self.transport.is_remote:
            try:
                await self.transport.disconnect()
            except Exception as e:
                print(f"{self.name}: Error during disconnect: {e}")
