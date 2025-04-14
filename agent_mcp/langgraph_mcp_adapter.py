"""
LangGraph MCP Adapter - Adapt LangGraph agents to work with MCP.

This module provides an adapter that allows LangGraph agents to work within
the Model Context Protocol (MCP) framework, enabling them to collaborate
with agents from other frameworks like Autogen and CrewAI.

Supports both workflow-based and tool-based LangGraph agents:
1. Workflow-based: Uses StateGraph for defining agent behavior
2. Tool-based: Uses LangChain tools and agent executors
"""

import asyncio
import traceback
from typing import Dict, Any, Optional, Callable, List, Union
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph
from .mcp_agent import MCPAgent
from .mcp_transport import HTTPTransport
from fastapi import FastAPI, Request
import uvicorn
from threading import Thread
import time

class LangGraphMCPAdapter(MCPAgent):
    """
    Adapter for LangGraph agents to work with MCP.
    
    This adapter supports both:
    1. Workflow-based agents using StateGraph
    2. Tool-based agents using LangChain tools
    """
    
    def __init__(
        self,
        name: str,
        workflow: Optional[StateGraph] = None,
        tools: Optional[List[BaseTool]] = None,
        process_message: Optional[Callable] = None,
        transport: Optional[HTTPTransport] = None,
        client_mode: bool = True,
        state_type: Optional[type] = None,
        **kwargs
    ):
        """
        Initialize the LangGraph MCP adapter.
        
        Args:
            name: Name of the agent
            workflow: Optional StateGraph workflow for workflow-based agents
            tools: Optional list of tools for tool-based agents
            process_message: Optional custom message processing function
            transport: Optional transport layer
            client_mode: Whether to run in client mode
            **kwargs: Additional arguments to pass to MCPAgent
        """
        # Initialize MCPAgent with transport
        super().__init__(name=name, transport=transport, **kwargs)
        
        if workflow and tools:
            raise ValueError("Cannot specify both workflow and tools. Choose one pattern.")
            
        if workflow:
            # Workflow-based agent
            self.workflow = workflow
            self.state_type = state_type
            self.executor = None
        elif tools:
            # Tool-based agent
            llm = ChatOpenAI(temperature=0)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful AI assistant that can use tools to accomplish tasks."),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            agent = create_openai_tools_agent(llm, tools, prompt)
            self.executor = AgentExecutor.from_agent_and_tools(
                agent=agent,
                tools=tools,
                handle_parsing_errors=True
            )
            self.workflow = None
            self.state_type = None
        else:
            raise ValueError("Must specify either workflow or tools")
        
        self.custom_process_message = process_message
        self.transport = transport
        self.client_mode = client_mode
        self.task_queue = asyncio.Queue()
        self.state: Dict[str, Any] = {}
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
                        if message_id and self.transport:
                            asyncio.create_task(self.transport.acknowledge_message(self.name, message_id))
                            print(f"[{self.name}] Acknowledged duplicate task {message.get('task_id')} (msg_id: {message_id})")
                        continue
                    
                    if message.get('type') == 'task':
                        print(f"{self.name}: Queueing task with message_id {message_id}")
                        await self.task_queue.put(message)
                    elif self.custom_process_message:
                        await self.custom_process_message(self, message)
                    else:
                        print(f"{self.name}: Unknown message type: {message.get('type')}")
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
                
    async def execute_task(self, task: Dict[str, Any]):
        """Execute a task using either workflow or executor"""
        try:
            if self.workflow:
                # Always initialize state as a dictionary for LangGraph workflows here.
                # LangGraph itself handles the state type defined in StateGraph().
                state_dict = {"message": task, "result": None}
                
                # Run workflow
                try:
                    print(f"{self.name}: Running workflow with initial state_dict: {state_dict}")
                    # Compile the workflow if not already compiled
                    if not hasattr(self, '_compiled_workflow'):
                        self._compiled_workflow = self.workflow.compile()
                    # Pass the initial state dict directly
                    final_state = await self._compiled_workflow.ainvoke(state_dict)
                    # Use the workflow's final state
                    result = final_state
                    print(f"{self.name}: Workflow finished with final_state: {result}") 
                    return {"result": result, "error": None}
                except Exception as e:
                    print(f"Error running workflow: {str(e)}")
                    import traceback
                    traceback.print_exc() 
                    return {"result": None, "error": str(e)}
            elif self.executor:
                # Run with executor
                result = await self.executor.arun(task)
                return {"result": result, "error": None}
            else:
                return {"result": None, "error": "No workflow or executor configured"}
        except Exception as e:
            return {
                "result": f"[FROM EXECUTE_TASK] Error executing task: {str(e)}",
                "error": True
            }
            
    async def process_tasks(self):
        """Process tasks from the queue"""
        while True:
            try:
                task = await self.task_queue.get()
                
                # Extract task details
                task_content = task.get('content', task.get('task', {}))
                task_id = task.get('task_id') or task_content.get('task_id')
                task_description = task.get('description') or task_content.get('description')
                message_id = task.get('message_id')
                reply_to = task.get('reply_to')
                
                if not task_id or not task_description:
                    print(f"[ERROR] {self.name}: Task missing required fields: {task}")
                    self.task_queue.task_done()
                    continue
                
                print(f"\n{self.name}: Processing task {task_id} with message_id {message_id}")
                
                try:
                    # Execute the task
                    result = await self.execute_task(task_content)
                    
                    # Mark task completed
                    super()._mark_task_completed(task_id)
                    
                    # Send result back if reply_to is specified
                    if reply_to:
                        print(f"{self.name}: Sending result back to {reply_to}")
                        await self.transport.send_message(
                            reply_to,
                            {
                                "type": "task_result",
                                "task_id": task_id,
                                "result": result['result'],
                                "sender": self.name,
                                "original_message_id": message_id,
                                "error": result['error']
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
                    print(f"{self.name}: Error processing task: {e}")
                    traceback.print_exc()
                    
                    if reply_to:
                        await self.transport.send_message(
                            reply_to,
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
