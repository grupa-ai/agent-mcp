"""
CrewAI MCP Adapter - Adapt CrewAI agents to work with MCP.

This module provides an adapter that allows CrewAI agents to work within
the Model Context Protocol (MCP) framework, enabling them to collaborate
with agents from other frameworks like Autogen and Langchain.
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from crewai import Agent as CrewAgent
from fastapi import FastAPI, Request
from .mcp_agent import MCPAgent
from .mcp_transport import HTTPTransport
import uvicorn
from threading import Thread
import time

class CrewAIMCPAdapter(MCPAgent):
    """
    Adapter for CrewAI agents to work with MCP.
    
    This adapter wraps a CrewAI agent and makes it compatible with the MCP framework,
    allowing it to communicate with other agents through the transport layer.
    """
    
    def __init__(
        self,
        name: str,
        crewai_agent: CrewAgent,
        process_message: Optional[Callable] = None,
        transport: Optional[HTTPTransport] = None,
        client_mode: bool = True,
        **kwargs
    ):
        """
        Initialize the CrewAI MCP adapter.
        
        Args:
            name: Name of the agent
            crewai_agent: CrewAI agent to adapt
            process_message: Optional custom message processing function
            transport: Optional transport layer
            client_mode: Whether to run in client mode
            **kwargs: Additional arguments to pass to MCPAgent
        """
        super().__init__(name=name, **kwargs)
        
        self.crewai_agent = crewai_agent
        self.custom_process_message = process_message
        self.transport = transport
        self.client_mode = client_mode
        self.task_queue = asyncio.Queue()
        self.server_ready = asyncio.Event()
        
        # Create FastAPI app for server mode
        self.app = FastAPI()
        
        @self.app.post("/message")
        async def handle_message(request: Request):
            return await self._handle_message(request)
            
        @self.app.on_event("startup")
        async def startup_event():
            self.server_ready.set()
            
        self.server_thread = None
        
    async def _handle_message(self, request: Request):
        """Handle incoming HTTP messages"""
        try:
            message = await request.json()
            await self.task_queue.put(message)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
            
    async def process_messages(self):
        """Process incoming messages from the transport layer"""
        while True:
            try:
                message, message_id = await self.transport.receive_message()
                print(f"{self.name}: Received message {message_id}: {message}")
                
                if message and isinstance(message, dict):
                    # Add message_id to message for tracking
                    message['message_id'] = message_id
                    
                    # Standardize message structure
                    if 'content' not in message and message.get('type') == 'task':
                        message = {
                            'type': 'task',
                            'content': {
                                'task_id': message.get('task_id'),
                                'description': message.get('description'),
                                'type': 'task'
                            },
                            'message_id': message_id,
                            'from': message.get('from', 'unknown')
                        }
                    
                    # --- Idempotency Check ---
                    if not super()._should_process_message(message):
                        # If skipped, acknowledge and continue
                        if message_id and self.transport:
                            asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                            print(f"[{self.name}] Acknowledged duplicate task {message.get('task_id')} (msg_id: {message_id})")
                        continue
                    
                    if message.get("type") == "task":
                        print(f"{self.name}: Queueing task with message_id {message_id}")
                        await self.task_queue.put(message)
                    elif self.custom_process_message:
                        await self.custom_process_message(self, message)
                    else:
                        print(f"{self.name}: Unknown message type: {message.get('type')}")
                        # Acknowledge unknown messages
                        if message_id and self.transport:
                            await self.transport.acknowledge_message(self.name, message_id)
                            print(f"{self.name}: Acknowledged unknown message {message_id}")
            except asyncio.CancelledError:
                print(f"{self.name}: Message processor cancelled")
                break
            except Exception as e:
                print(f"{self.name}: Error processing message: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)
                
    async def process_tasks(self):
        """Process tasks from the queue using the CrewAI agent"""
        while True:
            try:
                task = await self.task_queue.get()
                task_id = task.get('task', {}).get('task_id')
                message_id = task.get('message_id')
                
                print(f"\n{self.name}: Processing task {task_id} with message_id {message_id}")
                
                try:
                    # Extract task details from content or root level
                    # Standardized task extraction
                    # Unified content extraction with backward compatibility
                    task_content = task.get('content', task.get('task', {}))
                    task_id = task_content.get('task_id')
                    task_description = task_content.get('description')
                    
                    # Validate required fields
                    if not all([task_id, task_description]):
                        raise ValueError(f"Missing required task fields in message {message_id}")
                    message_id = task.get('message_id')
                    reply_to = task.get('reply_to')
                    
                    if not task_id or not task_description:
                        print(f"[{self.name}] ERROR: Invalid task structure received: {task}")
                        # Acknowledge bad tasks
                        if message_id and self.transport:
                             await self.transport.acknowledge_message(self.name, message_id)
                        print(f"[ERROR] {self.name}: Task missing required fields: {task}")
                        self.task_queue.task_done()
                        continue
                        
                    print(f"\n{self.name}: Processing task {task_id} (from msg {message_id}) Desc: {task_description}")
                    
                    result = await self.execute_task(task_description)
                    
                    # --- Mark task completed (Uses Base Class Method) ---
                    super()._mark_task_completed(task_id)
                    # --- End mark task completed ---
                    
                    # Send result back if reply_to is specified
                    if reply_to:
                        await self.transport.send_message(
                            reply_to,
                            {
                                "type": "task_result",
                                "task_id": task_id,
                                "result": result,
                                "sender": self.name,
                                "original_message_id": message_id  # Include original message ID
                            }
                        )
                        print(f"{self.name}: Result sent successfully")
                        
                        # Acknowledge task completion
                        if message_id:
                            await self.transport.acknowledge_message(self.name, message_id)
                            print(f"{self.name}: Task {task_id} acknowledged with message_id {message_id}")
                        else:
                            print(f"{self.name}: No message_id for task {task_id}, cannot acknowledge")
                except Exception as e:
                    print(f"{self.name}: Error executing task: {e}")
                    traceback.print_exc()
                    
                    # Send error result back if reply_to is specified
                    if reply_to:
                        await self.transport.send_message(
                            task['reply_to'],
                            {
                                "type": "task_result",
                                "task_id": task_id,
                                "result": f"Error: {str(e)}",
                                "sender": self.name,
                                "original_message_id": message_id,
                                "error": True
                            }
                        )
                
                self.task_queue.task_done()
                
            except Exception as e:
                print(f"{self.name}: Error processing task: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)
                
    async def execute_task(self, task_description: str) -> str:
        """
        Execute a task using the CrewAI agent.
        
        Args:
            task_description: Description of the task to execute
            
        Returns:
            The result of the task execution
        """
        try:
            # Execute task using CrewAI agent
            result = await asyncio.to_thread(
                self.crewai_agent.execute,
                task_description
            )
            return str(result)
        except Exception as e:
            return f"Error executing task: {e}"
            
    def run(self):
        """Start the message and task processors"""
        if not self.transport:
            raise ValueError(f"{self.name}: No transport configured")
            
        # Start the transport server if not in client mode
        if not self.client_mode:
            def run_server():
                config = uvicorn.Config(
                    app=self.app,
                    host=self.transport.host,
                    port=self.transport.port,
                    log_level="info"
                )
                server = uvicorn.Server(config)
                server.run()
                
            self.server_thread = Thread(target=run_server, daemon=True)
            self.server_thread.start()
        else:
            # In client mode, we're ready immediately
            self.server_ready.set()
            
        print(f"{self.name}: Starting message processor...")
        asyncio.create_task(self.process_messages())
        
        print(f"{self.name}: Starting task processor...")
        asyncio.create_task(self.process_tasks())
        
    async def connect_to_server(self, server_url: str):
        """Connect to a coordinator server"""
        if not self.client_mode:
            raise ValueError("Agent not configured for client mode")
            
        # Wait for server to be ready before connecting
        if not self.server_ready.is_set():
            await asyncio.wait_for(self.server_ready.wait(), timeout=10)
            
        # Register with the coordinator
        await self.transport.send_message(
            server_url,
            {
                "type": "register",
                "agent_name": self.name,
                "agent_url": self.transport.get_url()
            }
        )
