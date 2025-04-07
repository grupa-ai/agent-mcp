"""
Enhanced MCP Agent with client/server capabilities.
"""

import asyncio
from typing import Optional, Dict, Any, List
from mcp_agent import MCPAgent
from mcp_transport import MCPTransport

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
        msg_type = message.get("type")
        
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
            await self._handle_task_result(message)
            
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
        print(f"{self.name}: Received task: {message}")
        
        # Store task info if we're the coordinator
        if self.server_mode:
            task_id = message.get("task_id")
            if task_id:
                self.task_results[task_id] = None
        
        await self.task_queue.put(message)
        return {"status": "ok"}
        
    async def _handle_task_result(self, message: Dict[str, Any]):
        """Handle task result"""
        task_id = message.get("task_id")
        result = message.get("result")
        print(f"\n{self.name}: Received result for task {task_id}:")
        print(f"Result: {result}\n")
        
        # If we're the coordinator, store the result and potentially forward it
        if self.transport and self.transport.remote_url:
            print(f"{self.name}: Storing result for task {task_id}")
            self.task_results[task_id] = result
            
            # Check for dependent tasks
            if hasattr(self, 'task_dependencies'):
                print(f"{self.name}: Task dependencies: {self.task_dependencies}")
                # Find tasks that depend on this one
                for dep_task_id, dep_info in self.task_dependencies.items():
                    if task_id in dep_info.get("depends_on", []):
                        # Check if all dependencies are met
                        all_deps_met = True
                        for dep_id in dep_info.get("depends_on", []):
                            if dep_id not in self.task_results:
                                all_deps_met = False
                                break
                        
                        if all_deps_met:
                            print(f"{self.name}: All dependencies met for {dep_task_id}, forwarding task")
                            try:
                                # Forward the task with all dependency results
                                await self.transport.send_message(
                                    f"{self.transport.remote_url}/message/{dep_info['agent']}",
                                    {
                                        "type": "task",
                                        "task_id": dep_task_id,
                                        "description": dep_info["description"],
                                        "depends_on": dep_info["depends_on"],  # Include dependencies
                                        "reply_to": self.transport.remote_url  # Send result back to coordinator
                                    }
                                )
                            except Exception as e:
                                print(f"{self.name}: Error forwarding task {dep_task_id}: {e}")
                        else:
                            print(f"{self.name}: Still waiting for other dependencies for {dep_task_id}")
        
        return {"status": "ok"}
        
    async def assign_task(self, target_url: str, task: Dict[str, Any]):
        """Assign a task to another agent"""
        message = {
            "type": "task",
            "task_id": task["task_id"],
            "description": task["description"],
            "reply_to": task["reply_to"],
            "from": self.mcp_id
        }
        
        return await self.transport.send_message(target_url, message)
        
    async def process_messages(self):
        """Process incoming messages from transport"""
        print(f"{self.name}: Starting message processor...")
        while True:
            message, message_id = await self.transport.receive_message() # Get message and ID
            print(f"{self.name}: Processing message ID: {message_id}, Content: {message}")
            try:
                await self.handle_incoming_message(message)
                # Acknowledge only after successful handling
                await self.transport.acknowledge_message(message_id)
            except Exception as e:
                print(f"{self.name}: Error handling message {message_id}: {e}")
                # Decide if you want to retry or discard on error
                # For now, we won't acknowledge, so it might be re-delivered

    async def process_tasks(self):
        """Process tasks from the queue"""
        print(f"{self.name}: Starting task processor...")
        while True:
            try:
                task = await self.task_queue.get()
                print(f"{self.name}: Processing task: {task}")
                
                # Get task description and task_id
                task_desc = task.get("description", "")
                task_id = task.get("task_id", "")
                
                if not task_desc or not task_id:
                    print(f"{self.name}: Error: Task is missing description or task_id")
                    continue

                # Check if this task has dependencies
                depends_on = task.get("depends_on", [])
                if depends_on:
                    # Wait for dependencies to complete
                    all_deps_met = False
                    while not all_deps_met:
                        all_deps_met = True
                        for dep_id in depends_on:
                            if dep_id not in self.task_results:
                                print(f"{self.name}: Waiting for dependency {dep_id}...")
                                all_deps_met = False
                                break
                        if not all_deps_met:
                            await asyncio.sleep(1)  # Wait before checking again
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
                    except Exception as e:
                        print(f"{self.name}: Error generating response: {e}")
                        response = f"Error generating response: {e}"
                    
                    # Send result back if there's a reply_to
                    if "reply_to" in task:
                        print(f"{self.name}: Sending result back to {task['reply_to']}")
                        try:
                            result = await self.transport.send_message(
                                task["reply_to"],
                                {
                                    "type": "task_result",
                                    "task_id": task_id,
                                    "result": response
                                }
                            )
                            print(f"{self.name}: Result sent successfully: {result}")
                        except Exception as e:
                            print(f"{self.name}: Error sending result: {e}")
                
                self.task_queue.task_done()
                
            except Exception as e:
                print(f"{self.name}: Error processing task: {str(e)}")
    
    def run(self):
        """Run the agent's main loop"""
        if self.transport:
            self.transport.start()
            
        # Get the event loop
        loop = asyncio.get_event_loop()
        
        # Start message processing in a new task
        self._message_processor = loop.create_task(self.process_messages())
        
        # Start task processing in a new task
        self._task_processor = loop.create_task(self.process_tasks())
