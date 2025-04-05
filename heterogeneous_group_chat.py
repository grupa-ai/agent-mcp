"""
HeterogeneousGroupChat - A group chat implementation for heterogeneous agents.

This module provides a high-level abstraction for creating group chats with agents
from different frameworks (Autogen, Langchain, etc.) that can collaborate on tasks.
"""

import asyncio
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
        host: str = "localhost",
        base_port: int = 8000,
        coordinator_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a heterogeneous group chat.
        
        Args:
            name: Name of the group chat
            host: Host for the agents (default: localhost)
            base_port: Starting port number (default: 8000)
            coordinator_config: Optional configuration for the coordinator agent
        """
        self.name = name
        self.host = host
        self.next_port = base_port
        self.agents: List[MCPAgent] = []
        self.coordinator: Optional[EnhancedMCPAgent] = None
        self.coordinator_config = coordinator_config or {}
        self.coordinator_url = f"http://{host}:{base_port}"
        
    def _get_next_port(self) -> int:
        """Get the next available port number"""
        port = self.next_port
        self.next_port += 1
        return port
        
    def create_coordinator(self, api_key: str) -> EnhancedMCPAgent:
        """Create the coordinator agent for the group chat"""
        if self.coordinator:
            return self.coordinator
            
        # Create transport for coordinator
        coordinator_transport = HTTPTransport(
            host=self.host,
            port=self._get_next_port()
        )
        
        # Create coordinator with default or custom config
        config = {
            "name": f"{self.name}Coordinator",
            "transport": coordinator_transport,
            "server_mode": True,
            "system_message": "You coordinate tasks between different agents",
            "llm_config": {
                "config_list": [{
                    "model": "gpt-3.5-turbo",
                    "api_key": api_key
                }]
            }
        }
        config.update(self.coordinator_config)
        
        self.coordinator = EnhancedMCPAgent(**config)
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
            if not isinstance(agent, MCPAgent):
                raise ValueError(f"Agent {agent.name} must be an MCPAgent or wrapped in an MCP adapter")
                
            # Set up transport if needed
            if not hasattr(agent, 'transport'):
                agent.transport = HTTPTransport(
                    host=self.host,
                    port=self._get_next_port()
                )
                
            # Set client mode if needed
            if hasattr(agent, 'client_mode'):
                agent.client_mode = True
                
            self.agents.append(agent)
            added_agents.append(agent)
            
        return added_agents
        
    # Alias for backward compatibility
    add_agent = add_agents
        
    async def connect(self):
        """Connect all agents in the group chat"""
        if not self.coordinator:
            raise ValueError("No coordinator created. Call create_coordinator first.")
            
        # Start coordinator
        print(f"\n=== Starting {self.name} ===")
        print("Starting coordinator...")
        self.coordinator.run()
        await asyncio.sleep(2)  # Give coordinator time to start
        
        # Start and connect agents
        print("Starting agents...")
        for agent in self.agents:
            agent.run()
            
        await asyncio.sleep(2)  # Give agents time to start
        
        print("Connecting agents to coordinator...")
        for agent in self.agents:
            if hasattr(agent, 'connect_to_server'):
                await agent.connect_to_server(self.coordinator_url)
                
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
        self.coordinator.task_dependencies = {}
        for step in task["steps"]:
            task_id = step["task_id"]
            self.coordinator.task_dependencies[task_id] = {
                "url": step["url"],
                "depends_on": step.get("depends_on", [])
            }
            
        print(f"Task dependencies: {self.coordinator.task_dependencies}")
        
        # Assign tasks to agents
        for step in task["steps"]:
            await self.coordinator.assign_task(step["url"], {
                "task_id": step["task_id"],
                "description": step["description"],
                "reply_to": self.coordinator_url
            })
            
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
                for task_id in self.coordinator.task_dependencies:
                    if task_id not in self.coordinator.task_results:
                        all_completed = False
                        break
                        
                if all_completed:
                    print("\n=== All tasks completed! ===")
                    print("\nResults:")
                    for task_id, result in self.coordinator.task_results.items():
                        print(f"\n{task_id}:")
                        print(result)
                    break
                    
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\nStopping group chat...")
