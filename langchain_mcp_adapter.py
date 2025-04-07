"""
Adapter for Langchain agents to work with MCP.
"""

import asyncio
from typing import Dict, Any, Optional
from mcp_agent import MCPAgent
from mcp_transport import MCPTransport
from langchain.agents import AgentExecutor
from langchain.agents.openai_functions_agent.base import OpenAIFunctionsAgent

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
            
    async def handle_incoming_message(self, message: Dict[str, Any]):
        """Handle incoming messages from other agents"""
        msg_type = message.get("type")
        
        if msg_type == "task":
            # Handle new task assignment
            print(f"{self.name}: Received message: {message}")
            await self._handle_task(message)
            
    async def _handle_task(self, message: Dict[str, Any]):
        """Handle incoming task"""
        print(f"{self.name}: Received task: {message}")
        await self.task_queue.put(message)
        return {"status": "ok"}
        
    async def process_messages(self):
        """Process incoming messages from transport"""
        print(f"{self.name}: Starting message processor...")
        while True:
            message = await self.transport.receive_message()
            print(f"{self.name}: Processing message: {message}")
            await self.handle_incoming_message(message)
            
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
                
                # Run the Langchain agent
                result = await self.agent_executor.arun(task_desc)
                
                # Send result back if there's a reply_to
                if "reply_to" in task:
                    print(f"{self.name}: Sending result back to {task['reply_to']}")
                    await self.transport.send_message(
                        task["reply_to"],
                        {
                            "type": "task_result",
                            "task_id": task_id,
                            "result": result
                        }
                    )
                self.task_queue.task_done()
                
            except Exception as e:
                print(f"{self.name}: Error processing task: {str(e)}")
    
    def run(self):
        """Run the agent's main loop"""
        # Get the event loop
        loop = asyncio.get_event_loop()
        
        # Start message processing in a new task
        self._message_processor = loop.create_task(self.process_messages())
        
        # Start task processing in a new task
        self._task_processor = loop.create_task(self.process_tasks())
