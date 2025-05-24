"""Proxy agent that can discover and represent remote agents."""

from typing import Optional
from agent_mcp.enhanced_mcp_agent import EnhancedMCPAgent
from agent_mcp.mcp_transport import HTTPTransport

class ProxyAgent(EnhancedMCPAgent):
    """A proxy that represents a remote agent in the local group."""
    
    async def connect_to_remote_agent(self, agent_name: str, server_url: str) -> bool:
        """Connect to a remote agent and copy its capabilities."""
        try:
            # Create transport for remote connection
            self.transport = HTTPTransport.from_url(server_url, agent_name=self.name)
            
            # Connect to remote agent
            await self.connect_to_server(f"{server_url}/agents/{agent_name}")
            
            # Copy capabilities from remote agent
            self.capabilities = self.connected_agents.get(agent_name, [])
            return True
        except Exception as e:
            print(f"Error connecting to remote agent {agent_name}: {e}")
            return False
