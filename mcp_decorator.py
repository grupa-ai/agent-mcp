"""
Simple one-line integration decorator for connecting agents to the AgentMCP network.
"""

import functools
import aiohttp
import asyncio
from typing import Optional, Any, Callable
from mcp_agent import MCPAgent

async def register_with_server(agent_id: str, agent_info: dict, server_url: str = "http://localhost:8000"):
    """Register an agent with the MCP server"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{server_url}/register",
            json={"agent_id": agent_id, "info": agent_info}
        ) as response:
            return await response.json()

def mcp_agent(name: Optional[str] = None, system_message: Optional[str] = None):
    """
    Decorator to convert any agent class into an MCP-compatible agent.
    
    Args:
        name (str, optional): Name for the agent. If not provided, uses the class name
        system_message (str, optional): System message for the agent
        
    Usage:
        @mcp_agent(name="MyAgent")
        class MyCustomAgent:
            def generate_response(self, message):
                return "Hello from MyAgent!"
    """
    def decorator(agent_class: Any) -> Any:
        # Store original __init__
        original_init = agent_class.__init__
        
        def new_init(self, *args, **kwargs):
            # Call original __init__
            original_init(self, *args, **kwargs)
            
            # Create MCP instance
            self._mcp = MCPAgent(
                name=name or agent_class.__name__,
                system_message=system_message
            )
            
            # Add MCP methods to the instance (not the class)
            self._mcp_tools = {}
            self._context_store = {}
            self._mcp_id = self._mcp.mcp_id
            self._mcp_version = self._mcp.mcp_version
            
            # Map the agent's methods to MCP tools
            self._map_methods_to_tools()
            
            # Register with MCP server
            agent_info = {
                "name": name or agent_class.__name__,
                "type": agent_class.__name__,
                "tools": list(self._mcp_tools.keys()),
                "version": self._mcp_version
            }
            
            # Use asyncio to register with server
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                result = loop.run_until_complete(register_with_server(self._mcp_id, agent_info))
                print(f"Registered with MCP server: {result}")
            except Exception as e:
                print(f"Warning: Could not register with MCP server: {e}")
        
        def _map_methods_to_tools(self):
            """Map the agent's public methods to MCP tools."""
            for attr_name in dir(agent_class):
                if not attr_name.startswith('_'):  # Only public methods
                    attr = getattr(agent_class, attr_name)
                    if callable(attr):
                        # Get tool metadata if available
                        tool_name = getattr(attr, '_mcp_tool_name', attr_name)
                        tool_desc = getattr(attr, '_mcp_tool_description', 
                                          attr.__doc__ or f"Call {attr_name} method")
                        
                        # Register the method as an MCP tool
                        self._mcp_tools[tool_name] = {
                            'func': getattr(self, attr_name),
                            'description': tool_desc
                        }
        
        def generate_reply(self, *args, **kwargs):
            return self._mcp.generate_reply(*args, **kwargs)
        
        def register_tool(self, *args, **kwargs):
            return self._mcp.register_tool(*args, **kwargs)
        
        # Add new methods to the class
        agent_class.__init__ = new_init
        agent_class._map_methods_to_tools = _map_methods_to_tools
        agent_class.generate_reply = generate_reply
        agent_class.register_tool = register_tool
        
        # Add properties for MCP attributes
        agent_class.mcp_tools = property(lambda self: self._mcp_tools)
        agent_class.context_store = property(lambda self: self._context_store)
        agent_class.mcp_id = property(lambda self: self._mcp_id)
        agent_class.mcp_version = property(lambda self: self._mcp_version)
        
        return agent_class
    
    return decorator

def register_tool(name: str, description: Optional[str] = None):
    """
    Decorator to register a method as an MCP tool.
    
    Args:
        name (str): Name of the tool
        description (str, optional): Description of what the tool does
        
    Usage:
        @register_tool("greet", "Send a greeting message")
        def greet(self, message):
            return f"Hello, {message}!"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if isinstance(self, MCPAgent):
                return func(self, *args, **kwargs)
            raise TypeError("register_tool can only be used with MCP agents")
        
        # Store tool metadata
        wrapper._mcp_tool = True
        wrapper._mcp_tool_name = name
        wrapper._mcp_tool_description = description or func.__doc__ or f"Call {name}"
        
        return wrapper
    return decorator
