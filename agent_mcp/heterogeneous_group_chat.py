"""
HeterogeneousGroupChat - A group chat implementation for heterogeneous agents.

This module provides a high-level abstraction for creating group chats with agents
from different frameworks (Autogen, Langchain, etc.) that can collaborate on tasks.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Union, Sequence
from .mcp_transport import HTTPTransport
from .enhanced_mcp_agent import EnhancedMCPAgent
from .mcp_agent import MCPAgent

class HeterogeneousGroupChat:
    """
    A group chat for heterogeneous agents that abstracts away the complexity
    of setting up connections and coordinating tasks between different frameworks.
    """
    
    def __init__(
        self,
        name: str,
        server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app",
        coordinator_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a heterogeneous group chat.
        
        Args:
            name: Name of the group chat
            server_url: URL of the deployed MCP server
            coordinator_config: Optional configuration for the coordinator agent
        """
        self.name = name
        self.server_url = server_url
        self.agents: List[MCPAgent] = []
        self.coordinator: Optional[EnhancedMCPAgent] = None
        self.coordinator_config = coordinator_config or {}
        self.coordinator_url = server_url
        self.agent_tokens: Dict[str, str] = {} # Store agent tokens
        self._register_event = asyncio.Event()
        self._agent_tasks = [] # Initialize list to store agent tasks
        # Initialize directly on the group chat instance first
        self.task_results: Dict[str, Any] = {} 
        self.task_dependencies: Dict[str, Dict] = {}

    def _get_agent_url(self, agent_name: str) -> str:
        """Get the URL for an agent on the deployed server"""
        return f"{self.server_url}/agents/{agent_name}"
        
    def create_coordinator(self, api_key: str) -> EnhancedMCPAgent:
        """Create the coordinator agent for the group chat"""
        # Avoid creating coordinator if it already exists
        if self.coordinator:
            return self.coordinator
            
        # Define coordinator name (use config if provided, else default)
        coordinator_name = self.coordinator_config.get("name", f"{self.name}Coordinator")
        
        # Create transport for coordinator, passing its name
        coordinator_transport = HTTPTransport.from_url(
            self.server_url, 
            agent_name=coordinator_name
        )
        
        # --- Default Coordinator Configuration ---
        default_config = {
            "name": coordinator_name, 
            "transport": coordinator_transport,
            "system_message": "You are a helpful AI assistant coordinating tasks between other specialized agents. You receive task results and ensure the overall goal is achieved.",
            "llm_config": {
                 # Default model, can be overridden by coordinator_config
                "config_list": [{
                    "model": "gpt-3.5-turbo", 
                    "api_key": api_key
                }],
                "cache_seed": 42 # Or None for no caching
            },
        }
        
        # --- Merge Default and User Config --- 
        # User config takes precedence
        final_config = default_config.copy() # Start with defaults
        final_config.update(self.coordinator_config) # Update with user overrides
        
        # Ensure llm_config is properly structured if overridden
        if "llm_config" in self.coordinator_config and "config_list" not in final_config["llm_config"]:
             print("Warning: coordinator_config provided llm_config without config_list. Re-structuring.")
             # Assume the user provided a simple dict like {"api_key": ..., "model": ...}
             # We need to wrap it in config_list for AutoGen
             user_llm_config = final_config["llm_config"]
             final_config["llm_config"] = {
                 "config_list": [user_llm_config],
                 "cache_seed": user_llm_config.get("cache_seed", 42)
             }
        elif "llm_config" in final_config and "api_key" not in final_config["llm_config"].get("config_list", [{}])[0]:
             # If llm_config exists but api_key is missing in the primary config
             print("Warning: api_key missing in llm_config config_list. Injecting from create_coordinator argument.")
             if "config_list" not in final_config["llm_config"]:
                 final_config["llm_config"]["config_list"] = [{}]
             final_config["llm_config"]["config_list"][0]["api_key"] = api_key


        # --- Create Coordinator Agent --- 
        print(f"Creating coordinator with config: {final_config}") # Debug: Log final config
        self.coordinator = EnhancedMCPAgent(**final_config)
        
        # --- Set Message Handler ---
        self.coordinator.transport.set_message_handler(self._handle_coordinator_message)
        return self.coordinator
        
    def add_agents(self, agents: Union[MCPAgent, Sequence[MCPAgent]]) -> List[MCPAgent]:
        """
        Add one or more agents to the group chat.
        
        Args:
            agents: A single MCPAgent or a sequence of MCPAgents
            
        Returns:
            List of added agents
            
        Example:
            # Add a single agent
            group.add_agents(agent1)
            
            # Add multiple agents
            group.add_agents([agent1, agent2, agent3])
            
            # Add agents as separate arguments
            group.add_agents(agent1, agent2, agent3)
        """
        if not isinstance(agents, (list, tuple)):
            agents = [agents]
            
        added_agents = []
        for agent in agents:
            # Retrieve token if agent was already registered
            token = self.agent_tokens.get(agent.name)
            if not self.server_url:
                 raise ValueError("Cannot add agents before connecting. Call connect() first.")
                 
            # Create transport for the agent, passing its name and token
            agent.transport = HTTPTransport.from_url(self.server_url, agent_name=agent.name, token=token)
                
            # Set client mode if needed
            if hasattr(agent, 'client_mode'):
                agent.client_mode = True
                
            self.agents.append(agent)
            added_agents.append(agent)
            
        return added_agents
        
    # Alias for backward compatibility
    add_agent = add_agents
        
    async def connect(self):
        """Register all agents and start their processing loops."""
        print("Registering coordinator...")
        coord_task = await self._register_and_start_agent(self.coordinator)
        if not coord_task:
             print("Coordinator registration failed. Aborting connect.")
             return

        print("Registering agents...")
        tasks = [coord_task] # Start with coordinator task
        for agent in self.agents:
            agent_task = await self._register_and_start_agent(agent)
            if agent_task: # Only add task if registration was successful
                tasks.append(agent_task)
            else:
                print(f"Skipping agent {agent.name} due to registration failure.")
                # Optionally, handle failed agents (e.g., remove from group?)

        if not tasks:
            print("No agents were successfully registered and started.")
            return
            
        print(f"All {len(tasks)} agents registered and started.")
        # Store tasks but don't wait for them - they'll run in the background
        self._agent_tasks = tasks
        print("Group chat ready for task submission.")

    async def _register_and_start_agent(self, agent: MCPAgent):
        """Register an agent, start its event stream, and its processors."""
        if not agent.transport or not isinstance(agent.transport, HTTPTransport):
             raise ValueError(f"Agent {agent.name} has no valid HTTPTransport defined.")
             
        response = await agent.transport.register_agent(agent)
        
        # Parse response which may be in {'body': '{...}'} format
        if isinstance(response, dict):
            if 'body' in response:
                # Response is wrapped, parse the body string
                try:
                    response = json.loads(response['body'])
                except json.JSONDecodeError:
                    print(f"Error parsing agent registration response body: {response}")
                    
        if response and isinstance(response, dict) and "token" in response:
            token = response["token"]
            self.agent_tokens[agent.name] = token
            agent.transport.token = token
            agent.transport.auth_token = token
            print(f"Agent {agent.name} registered successfully with token.")

            # Start polling *before* starting the agent's run loop
            await agent.transport.start_polling()
            
            # Start agent's main run loop (message processing, etc.)
            # We create the task but don't await it here; the calling function (connect) will gather tasks.
            task = asyncio.create_task(agent.run())
            self._agent_tasks.append(task) # Store the task
            return task # Return the task for potential gathering
        else:
            print(f"Warning: Agent {agent.name} registration failed or did not return a token. Response: {response}")
            # Don't run the agent if registration fails - it won't be able to communicate
            return None # Indicate failure
        
    async def submit_task(self, task: Dict[str, Any]) -> None:
        """Submit a task to the group chat."""
        print(f"***** [{self.name}] ENTERING submit_task *****", flush=True) # Ensure entry is logged
        if not self.coordinator:
            raise ValueError("Group chat not connected. Call connect() first.")
            
        self.task_results = {} # Reset results for new task submission
        print("\n=== Submitting task to group ===")

        # Ensure task is in the correct format
        if not isinstance(task, dict) or 'type' not in task:
            task = {'type': 'task', 'content': task}

        # Store task dependencies from the input task definition
        # We need a dictionary where keys are the step task_ids
        if isinstance(task['content'], dict) and all(isinstance(v, dict) for v in task['content'].values()):
            # If task is already a dict mapping task_ids to task info
            self.task_dependencies = task['content']
        else:
            # If task has a steps list, convert it to a dict
            self.task_dependencies = {step["task_id"]: step for step in task['content'].get("steps", [])}
        print(f"Parsed Step Dependencies: {self.task_dependencies}")

        # Also store in coordinator instance if it exists
        if self.coordinator:
            # Ensure the coordinator has the dict initialized
            if not hasattr(self.coordinator, 'task_dependencies') or not isinstance(getattr(self.coordinator, 'task_dependencies', None), dict):
                self.coordinator.task_dependencies = {}
            self.coordinator.task_dependencies.update(self.task_dependencies)

        if not self.coordinator or not self.coordinator.transport:
             print("CRITICAL ERROR: Coordinator is not initialized or has no transport. Cannot submit task.")
             return
        
        coordinator_transport = self.coordinator.transport

        print(f"[DEBUG - {self.name}] Starting submit_task loop over {len(self.task_dependencies)} dependencies.", flush=True)
        print(f"***** [{self.name}] Dependencies Content: {self.task_dependencies} *****", flush=True) # Log content before loop

        # Assign tasks to agents based on the structure
        # Submit tasks to their respective agents
        for task_id, task_info in self.task_dependencies.items():
            print(f"[DEBUG - {self.name}] Loop Iteration: Processing task_id '{task_id}' for agent '{task_info['agent']}'", flush=True)
            agent_name = task_info["agent"]
            message = {
                "type": "task",
                "task_id": task_id,
                "description": task_info["description"],
                "depends_on": task_info.get("depends_on", []),  # Include dependencies
                "reply_to": f"{self.server_url}/message/{self.coordinator.name}" # Full URL for reply
            }
            print(f"Sending task to {agent_name}")
            print(f"Task message: {message}")
            # Use coordinator's transport to send task to agent
            await coordinator_transport.send_message(agent_name, message)
            
        print("Task submitted. Waiting for completion...")
        
    async def wait_for_completion(self, check_interval: float = 1.0):
        """
        Wait for all tasks to complete.
        
        Args:
            check_interval: How often to check for completion in seconds
        """
        if not self.coordinator:
            raise ValueError("Group chat not connected. Call connect() first.")
            
        try:
            while True:
                # Check if all tasks have results
                all_completed = True
                # Use the dependencies stored in the coordinator
                for task_id in self.task_dependencies:
                    # Check both group chat and coordinator results
                    if task_id not in self.task_results and task_id not in self.coordinator.task_results:
                        all_completed = False
                        print(f"Waiting for task {task_id}...")
                        break
                        
                if all_completed:
                    print("\n=== All tasks completed! ===")
                    print("\nResults:")
                    # Merge results from both sources
                    all_results = {**self.task_results, **self.coordinator.task_results}
                    for task_id, result in all_results.items():
                        print(f"\n{task_id}:")
                        print(result)
                    break
                    
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\nStopping group chat...")
            
    async def _handle_coordinator_message(self, message: Dict, message_id: str):
        """Handles messages received by the coordinator's transport."""
        if not self.coordinator: # Ensure coordinator exists
            print("[Coordinator Handler] Error: Coordinator not initialized.")
            return
            
        print(f"\n[Coordinator {self.coordinator.name}] Received message: {message}")
        
        # Handle messages wrapped in 'body' field
        if isinstance(message, dict) and 'body' in message:
            try:
                if isinstance(message['body'], str):
                    message = json.loads(message['body'])
                else:
                    message = message['body']
                print(f"[Coordinator {self.coordinator.name}] Unwrapped message body: {message}")
            except json.JSONDecodeError:
                print(f"[Coordinator {self.coordinator.name}] Error decoding message body: {message}")
                return
        
        # Look for type and task_id at top level
        msg_type = message.get("type")
        task_id = message.get("task_id")
        
        print(f"[Coordinator {self.coordinator.name}] Processing message type '{msg_type}' for task {task_id}")
        
        if msg_type in ["result", "task_result"]:  # Handle both result types
            result_content = message.get("result") or message.get("description")  # Try both fields
            if task_id and result_content is not None:
                print(f"[Coordinator {self.coordinator.name}] Storing result for task {task_id}")
                # Store result in both the group chat and coordinator
                self.task_results[task_id] = result_content
                self.coordinator.task_results[task_id] = result_content
                print(f"[Coordinator {self.coordinator.name}] Stored result: {result_content[:100]}...")
                print(f"[Coordinator {self.coordinator.name}] Current task results: {list(self.task_results.keys())}")
                print(f"[Coordinator {self.coordinator.name}] Current dependencies: {self.task_dependencies}")
                
                # Acknowledge the message
                try:
                    if message_id:  # Only acknowledge if we have a message ID
                        await self.coordinator.transport.acknowledge_message(self.coordinator.name, message_id)
                        print(f"[Coordinator {self.coordinator.name}] Acknowledged message {message_id}")
                except Exception as e:
                    print(f"[Coordinator {self.coordinator.name}] Error acknowledging message {message_id}: {e}")
            else:
                print(f"[Coordinator {self.coordinator.name}] Received invalid result message (missing task_id or result): {message}")
        elif msg_type == "get_result":  # Handle get result request
            result = None
            if task_id in self.task_results:
                result = self.task_results[task_id]
            elif task_id in self.coordinator.task_results:
                result = self.coordinator.task_results[task_id]
            
            if result:
                print(f"[Coordinator {self.coordinator.name}] Found result for task {task_id}")
                # Send result back
                try:
                    await self.coordinator.transport.send_message(
                        f"{self.server_url}/message/{message.get('sender', 'unknown')}",
                        {
                            "type": "task_result",
                            "task_id": task_id,
                            "result": result
                        }
                    )
                    print(f"[Coordinator {self.coordinator.name}] Sent result for task {task_id}")
                except Exception as e:
                    print(f"[Coordinator {self.coordinator.name}] Error sending result: {e}")
            else:
                print(f"[Coordinator {self.coordinator.name}] No result found for task {task_id}")
        else:
            print(f"[Coordinator {self.coordinator.name}] Received unhandled message type '{msg_type}': {message}")
            # Optionally, acknowledge other messages too or handle errors
            try:
                await self.coordinator.transport.acknowledge_message(message_id)
            except Exception as e:
                print(f"[Coordinator {self.coordinator.name}] Error acknowledging message {message_id}: {e}")

    async def shutdown(self):
        """Gracefully disconnect all agents and cancel their tasks."""
        print(f"Initiating shutdown for {len(self._agent_tasks)} agent tasks...")

        # 1. Cancel all running agent tasks
        for task in self._agent_tasks:
            if task and not task.done():
                print(f"Cancelling task {task.get_name()}...")
                task.cancel()
            
        # Wait for all tasks to be cancelled
        if self._agent_tasks:
            await asyncio.gather(*[t for t in self._agent_tasks if t], return_exceptions=True)
            print("All agent tasks cancelled or finished.")
        self._agent_tasks.clear() # Clear the list of tasks

        # 2. Disconnect transports for all agents (coordinator + regular agents)
        all_agents = [self.coordinator] + self.agents
        disconnect_tasks = []
        for agent in all_agents:
             if hasattr(agent, 'transport') and hasattr(agent.transport, 'disconnect'):
                 print(f"Disconnecting transport for {agent.name}...")
                 disconnect_tasks.append(agent.transport.disconnect())
             
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
            print("All agent transports disconnected.")
            
        print("Shutdown complete.")
