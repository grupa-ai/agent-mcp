"""
HeterogeneousGroupChat - A group chat implementation for heterogeneous agents.

This module provides a high-level abstraction for creating group chats with agents
from different frameworks (Autogen, Langchain, etc.) that can collaborate on tasks.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Union, Sequence
from mcp_transport import HTTPTransport
from enhanced_mcp_agent import EnhancedMCPAgent
from mcp_agent import MCPAgent

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
        """Connect all agents to the deployed server"""
        if not self.coordinator:
            raise ValueError("No coordinator created. Call create_coordinator first.")
            
        print(f"\n=== Connecting {self.name} to {self.server_url} ===\n")
        
        # Register and start coordinator
        print("Registering coordinator...")
        coord_response = await self.coordinator.transport.register_agent(self.coordinator)
        
        # Parse response which may be in {'body': '{...}'} format
        if isinstance(coord_response, dict):
            if 'body' in coord_response:
                # Response is wrapped, parse the body string
                try:
                    coord_response = json.loads(coord_response['body'])
                except json.JSONDecodeError:
                    print(f"Error parsing coordinator registration response body: {coord_response}")
                    
        if coord_response and isinstance(coord_response, dict) and "token" in coord_response:
            token = coord_response["token"]
            self.agent_tokens[self.coordinator.name] = token
            # Set the token for the coordinator's own transport (for sending messages AND receiving events)
            self.coordinator.transport.token = token
            print(f"Coordinator {self.coordinator.name} registered successfully")
            # Start coordinator's event stream AFTER successful registration
            self.coordinator.transport.start_event_stream()
            # Start the coordinator's internal processing loops
            self.coordinator.run()
        else:
            print(f"Warning: Coordinator {self.coordinator.name} registration failed or did not return a token. Response: {coord_response}")
            # Potentially raise an error or handle this case more robustly
            
        print("Registering agents...")
        tasks = []
        for agent in self.agents:
            tasks.append(self._register_and_start_agent(agent))
            
        await asyncio.gather(*tasks)
        
        # Ensure all agents are registered before proceeding
        self._register_event.set()
        print("All agents registered and started successfully!")
                
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
             # Set the token for the agent's transport (needed for event stream)
             agent.transport.token = token 
             print(f"Agent {agent.name} registered successfully with token.")
             
             # Now that we have the token, start the event stream connection
             agent.transport.start_event_stream()
             
             # Start agent processors after registration and event stream start
             agent.run() 
        else:
             print(f"Warning: Agent {agent.name} registration failed or did not return a token. Response: {response}")
             # Decide if agent should still run or if this is a critical failure
             # agent.run() # Maybe don't run if registration fails?
             
    async def submit_task(self, task: Dict[str, Any]):
        """
        Submit a task to the group chat.
        
        Args:
            task: Task definition including steps and dependencies
        """
        if not self.coordinator:
            raise ValueError("Group chat not connected. Call connect() first.")
            
        print("\n=== Submitting task to group ===")
        
        # Store task dependencies
        self.task_dependencies = {}
        for step in task["steps"]:
            task_id = step["task_id"]
            agent_name = step["agent"]
            self.task_dependencies[task_id] = {
                "agent": agent_name,
                "description": step["description"],  # Store description
                "depends_on": step.get("depends_on", [])
            }
            # Also store in coordinator instance
            if self.coordinator:
                self.coordinator.task_dependencies[task_id] = self.task_dependencies[task_id]
            
        print(f"Task dependencies: {self.task_dependencies}")
        
        # Assign tasks to agents
        for step in task["steps"]:
            agent_name = step["agent"]
            agent_url = f"{self.server_url}/message/{agent_name}"
            message = {
                "type": "task",
                "task_id": step["task_id"],
                "description": step["description"],
                "depends_on": step.get("depends_on", []),  # Include dependencies
                "reply_to": self.server_url  # Full server URL
            }
            print(f"Sending task to {agent_name} at {agent_url}")
            # Use coordinator's transport to send task to agent
            await self.coordinator.transport.send_message(agent_url, message)
            
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
                    if task_id not in self.task_results:
                        all_completed = False
                        break
                        
                if all_completed:
                    print("\n=== All tasks completed! ===")
                    print("\nResults:")
                    for task_id, result in self.task_results.items():
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
            
        print(f"[Coordinator {self.coordinator.name}] Received message: {message}")
        
        # Handle messages wrapped in 'body' field
        if isinstance(message, dict) and 'body' in message:
            try:
                if isinstance(message['body'], str):
                    message = json.loads(message['body'])
                else:
                    message = message['body']
            except json.JSONDecodeError:
                print(f"[Coordinator {self.coordinator.name}] Error decoding message body: {message}")
                return
        
        # Look for type and task_id at top level
        msg_type = message.get("type")
        task_id = message.get("task_id")
        
        if msg_type == "result":
            result_content = message.get("result") or message.get("description")  # Try both fields
            if task_id and result_content is not None:
                print(f"[Coordinator {self.coordinator.name}] Storing result for task {task_id}")
                # Store result in the group chat's dictionary
                self.task_results[task_id] = result_content
                # if self.coordinator:
                #     self.coordinator.task_results[task_id] = result_content 
                # Acknowledge the message
                try:
                    await self.coordinator.transport.acknowledge_message(message_id)
                    print(f"[Coordinator {self.coordinator.name}] Acknowledged message {message_id}")
                except Exception as e:
                    print(f"[Coordinator {self.coordinator.name}] Error acknowledging message {message_id}: {e}")
            else:
                print(f"[Coordinator {self.coordinator.name}] Received invalid result message (missing task_id or result): {message}")
        else:
            print(f"[Coordinator {self.coordinator.name}] Received unhandled message type '{msg_type}': {message}")
            # Optionally, acknowledge other messages too or handle errors
            try:
                await self.coordinator.transport.acknowledge_message(message_id)
            except Exception as e:
                 print(f"[Coordinator {self.coordinator.name}] Error acknowledging message {message_id}: {e}")
