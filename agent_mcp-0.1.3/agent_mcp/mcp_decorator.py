"""
Simple one-line integration decorator for connecting agents to the AgentMCP network.
"""

import functools
import aiohttp
import asyncio
import os
import json
import logging
import uuid
from typing import Optional, Any, Callable, Tuple, Dict
from .mcp_agent import MCPAgent
from .mcp_transport import HTTPTransport

# Default to environment variable or fallback to localhost
DEFAULT_MCP_SERVER = os.getenv('MCP_SERVER_URL', "https://mcp-server-ixlfhxquwq-ew.a.run.app")

# Set up logging
logger = logging.getLogger(__name__)

# Standalone registration function (no longer primary path for decorator, but keep for potential direct use)
async def register_with_server(agent_id: str, agent_info: dict, server_url: str = DEFAULT_MCP_SERVER):
    """Register an agent with the MCP server"""
    # Revert to using the default ClientSession
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{server_url}/register",
            json={"agent_id": agent_id, "info": agent_info}
        ) as response:
            data = await response.json()
            # Parse the response body which is a JSON string
            if isinstance(data, dict) and 'body' in data:
                try:
                    body = json.loads(data['body'])
                    return body
                except json.JSONDecodeError:
                    return data
            return data

class MCPAgentDecorator:
    """Decorator class to wrap a function as an MCP agent"""
    def __init__(self, agent_function: Callable, agent_class: type, mcp_id: Optional[str] = None, mcp_server: Optional[str] = None, tools: Optional[list] = None, version: Optional[str] = "1.0"):
        # Store original function and configuration
        self._original_agent_function = agent_function
        self._agent_class = agent_class
        self._mcp_id_provided = mcp_id
        self._mcp_server = mcp_server or DEFAULT_MCP_SERVER
        self._tools_funcs = tools or []
        self._mcp_version = version

        # --- Configuration that will be set on the INSTANCE --- 
        # Note: We use a separate __call__ method or similar pattern later 
        # to actually create the instance and set these.
        # For now, we define the methods the decorator will add.

    # Methods to be added to the decorated class
    
    def _initialize_mcp_instance(self, instance):
        """Called when an instance of the decorated class is created."""
        instance._mcp = MCPAgent(
            name=self._agent_class.__name__,
            system_message=None # Or derive from docstring?
        )
        instance._mcp_id = self._mcp_id_provided or str(uuid.uuid4())
        instance._registered_agent_id: Optional[str] = None
        instance._mcp_tools = {}
        instance.transport = HTTPTransport.from_url(self._mcp_server)
        instance.context_store = {} # Simple dict for context

        # Process tools provided to the decorator
        if self._tools_funcs:
            for tool_func in self._tools_funcs:
                # Ensure the tool_func is bound to the instance if it's a method
                bound_tool_func = tool_func.__get__(instance, self._agent_class) 
                
                tool_name = getattr(bound_tool_func, '_mcp_tool_name', bound_tool_func.__name__)
                tool_desc = getattr(bound_tool_func, '_mcp_tool_description', 
                                  bound_tool_func.__doc__ or f"Call {tool_name}")
                
                instance._mcp_tools[tool_name] = {
                    'func': bound_tool_func,
                    'description': tool_desc
                }
                
    async def connect(self): # 'self' here refers to the instance of the decorated class
        """Connects the decorated agent: registers and starts transport polling."""
        if not hasattr(self, 'transport') or self.transport is None:
             raise RuntimeError("MCP Transport not initialized. Did you call __init__?")
             
        agent_info = {
            "name": self._mcp.name,
            "type": self.__class__.__name__, # Use instance's class name
            "tools": list(self._mcp_tools.keys()),
            "version": self._mcp_version # Use the version stored on the instance
        }
        
        # --- Begin integrated registration logic (mimicking HTTPTransport) ---
        connector = aiohttp.TCPConnector(ssl=False) 
        timeout = aiohttp.ClientTimeout(total=30)   
        register_url = f"{self.transport.remote_url}/register"

        logger.info(f"Attempting registration for {self._mcp_id} at {register_url}")
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                async with session.post(
                    register_url,
                    json={"agent_id": self._mcp_id, "info": agent_info}
                ) as response:
                    response.raise_for_status() 
                    data = await response.json()
                    logger.debug(f"Raw registration response data: {data}")
                    
                    result = None
                    token = None
                    if isinstance(data, dict) and 'body' in data:
                        try:
                            body = json.loads(data['body'])
                            result = body 
                            if isinstance(result, dict) and 'token' in result:
                                token = result['token']
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Failed to decode 'body' from registration response: {data.get('body')}. Error: {e}")
                            result = data 
                    else:
                        result = data 
                    
                    if not token and isinstance(result, dict) and 'token' in result:
                         token = result['token']

                    if not token:
                        raise ValueError(f"No token could be extracted from registration response: {result}")
                        
                    self._registered_agent_id = result.get('agent_id') 
                    if not self._registered_agent_id:
                        raise ValueError(f"Registration response missing 'agent_id': {result}")
                        
                    print(f"Registered with MCP server (result parsed): {result}")

                    self.transport.token = token
                    self.transport.auth_token = token 
                    print(f"Token set for agent {self._registered_agent_id}") 
                    
                    # Connect and start polling for messages
                    await self.transport.connect(agent_name=self._registered_agent_id, token=token)
                    
            except aiohttp.ClientResponseError as e:
                error_body = await response.text() 
                logger.error(f"HTTP error during registration: Status={e.status}, Message='{e.message}', URL={e.request_info.url}, Response Body: {error_body[:500]}")
                print(f"HTTP error during registration: {e.status} - {e.message}. Check logs for details.")
                raise
            except aiohttp.ClientConnectionError as e:
                logger.error(f"Connection error during registration to {register_url}: {e}")
                print(f"Connection error during registration: {e}")
                raise
            except Exception as e:
                logger.exception(f"Unexpected error during registration/connection for agent {self._mcp_id}: {e}")
                print(f"Error during registration/connection: {e}")
                raise

    async def disconnect(self): # 'self' here refers to the instance
        """Disconnects the transport layer."""
        if hasattr(self, 'transport') and self.transport:
            await self.transport.disconnect()
        else:
            logger.warning("Attempted to disconnect but transport was not initialized.")

    def get_id(self) -> Optional[str]: # 'self' here refers to the instance
        """Returns the agent ID assigned by the server after registration."""
        return self._registered_agent_id

    async def send_message(self, target: str, message: Any): # 'self' here refers to the instance
        """Sends a message via the transport layer."""
        if hasattr(self, 'transport') and self.transport:
            await self.transport.send_message(target, message)
        else:
            raise RuntimeError("Transport not initialized, cannot send message.")
        
    async def receive_message(self, timeout: float = 1.0) -> Tuple[Optional[Dict[str, Any]], Optional[str]]: 
        """Receives a message via the transport layer."""
        if hasattr(self, 'transport') and self.transport:
             return await self.transport.receive_message(timeout=timeout)
        else:
             logger.warning("Attempted to receive message but transport was not initialized.")
             return None, None
             
    # This method makes the decorator work on classes
    def __call__(self, Cls): 
        # Modify the class's __init__ to include our initialization
        original_init = Cls.__init__

        decorator_self = self # Capture the decorator instance itself

        def new_init(instance, *args, **kwargs):
            decorator_self._initialize_mcp_instance(instance) # Use decorator's init logic
            original_init(instance, *args, **kwargs) # Call original class __init__
            
            # Store the version on the instance too, might be useful
            instance._mcp_version = decorator_self._mcp_version 

        Cls.__init__ = new_init
        
        # Add the methods directly to the class
        # Assign the unbound methods from the decorator class itself
        Cls.connect = MCPAgentDecorator.connect
        Cls.disconnect = MCPAgentDecorator.disconnect
        Cls.get_id = MCPAgentDecorator.get_id
        Cls.send_message = MCPAgentDecorator.send_message
        Cls.receive_message = MCPAgentDecorator.receive_message
        
        # Add properties for MCP attributes if needed
        # Cls.mcp_tools = property(lambda instance: instance._mcp_tools)
        # Cls.context_store = property(lambda instance: instance.context_store)
        # Cls.mcp_id = property(lambda instance: instance._mcp_id)

        return Cls

# Global decorator instance (adjust if configuration needs to vary per use)
def mcp_agent(agent_class=None, mcp_id: Optional[str] = None, mcp_server: Optional[str] = None, tools: Optional[list] = None, version: Optional[str] = "1.0"):
    """Decorator to turn a class into an MCP agent."""
    
    if agent_class is None:
        # Called with arguments like @mcp_agent(mcp_id="...")
        return functools.partial(mcp_agent, mcp_id=mcp_id, mcp_server=mcp_server, tools=tools, version=version)
    else:
        # Called as @mcp_agent
        decorator = MCPAgentDecorator(None, agent_class, mcp_id, mcp_server, tools, version)
        return decorator(agent_class) # Apply the decorator logic via __call__

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
