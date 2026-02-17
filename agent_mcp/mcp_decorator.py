"""
Simple one-line integration decorator for connecting agents to the AgentMCP network.

Now with Social Handle Support (@handle style) for scalable discovery!
"""

import functools
import aiohttp
import asyncio
import os
import json
import logging
import uuid
import hashlib
import re
from typing import Optional, Any, Callable, Tuple, Dict, List
from .mcp_agent import MCPAgent
from .mcp_transport import HTTPTransport


# Handle validation regex
HANDLE_PATTERN = re.compile(r'^@?[a-zA-Z][a-zA-Z0-9_-]*(?:@[a-zA-Z][a-zA-Z0-9_-]*)?(?:\.[a-zA-Z][a-zA-Z0-9_-]*)?$')


def parse_handle(mcp_id: str) -> Dict[str, Any]:
    """
    Parse a handle string into components.
    
    Supported formats:
        @alice@acme.corp       -> Company mode (no external)
        @alice@acme.business   -> Business mode (sanitized)
        @alice@acme.public    -> Public mode (minimal)
        @claude.code-assistant -> global, name=claude, service=code-assistant
        @jane@corp.hr         -> org=jane, service=corp
    
    Network Modes (determined by suffix):
        .corp     -> Company/Intranet (no external connection)
        .business -> Business network (trusted partners, sanitized)
        .public  -> Public MACNet (minimal filter)
    
    Args:
        mcp_id: The handle string
        
    Returns:
        Dict with keys: name, org, service, scope, is_handle, network_mode
    """
    # Check if it's a handle (starts with @ or contains @ in middle)
    is_handle = mcp_id.startswith('@') or '@' in mcp_id
    
    # Determine network mode from suffix
    def get_network_mode(handle_str: str) -> str:
        handle_lower = handle_str.lower()
        if '.corp' in handle_lower:
            return "company"  # No external - fully isolated
        elif '.business' in handle_lower:
            return "business"  # Sanitized - partners
        elif '.public' in handle_lower:
            return "public"  # Minimal - public
        return "public"  # Default to public
    
    network_mode = get_network_mode(mcp_id)
    
    if not is_handle:
        # Plain string ID - convert to handle format for consistency
        return {
            "name": mcp_id,
            "org": None,
            "service": None,
            "scope": "global",
            "network_mode": "public",  # Default for plain strings
            "is_handle": False,
            "original": mcp_id,
            "handle_format": f"@{mcp_id}.agent"
        }
    
    # Parse handle
    handle = mcp_id.lstrip('@')
    parts = handle.split('@')
    
    if len(parts) == 2:
        # @name@org.service format
        name, rest = parts
        org_parts = rest.rsplit('.', 1)
        if len(org_parts) > 1:
            org, service = org_parts
            scope = "public"
        else:
            org = None
            service = org_parts[0]
            scope = "global"
    else:
        # @name.service format
        name = parts[0]
        if '.' in name:
            name_parts = name.split('.', 1)
            name = name_parts[0]
            service = name_parts[1] if len(name_parts) > 1 else None
        else:
            service = None
        org = None
        scope = "global"
    
    return {
        "name": name,
        "org": org,
        "service": service,
        "scope": scope,
        "network_mode": network_mode,
        "is_handle": True,
        "original": mcp_id,
        "handle_format": f"@{handle}"
    }


def is_valid_handle(mcp_id: str) -> bool:
    """Check if a string is a valid handle format"""
    if not mcp_id:
        return False
    
    # Allow plain strings too (backward compatibility)
    if not mcp_id.startswith('@') and '@' not in mcp_id:
        return True
    
    # Validate handle format
    cleaned = mcp_id.lstrip('@')
    return bool(HANDLE_PATTERN.match(cleaned))

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
            system_message=None
        )
        
        # Handle social @handle style for agent ID
        raw_id = self._mcp_id_provided or str(uuid.uuid4())
        handle_info = parse_handle(raw_id)
        
        # Store the handle info for discovery
        instance._handle_info = handle_info
        # Use handle format as the canonical ID
        instance._mcp_id = handle_info["handle_format"] if handle_info["is_handle"] else raw_id
        instance._mcp_id_raw = raw_id  # Keep original for backward compat
        
        # For DNS-style discovery
        instance._handle = instance._mcp_id
        instance._org = handle_info.get("org")
        instance._service = handle_info.get("service")
        
        instance._registered_agent_id = None
        instance._mcp_tools = {}
        instance.transport = HTTPTransport.from_url(self._mcp_server)
        instance.context_store = {}

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
             
        # Include handle info for DNS-style discovery
        handle_info = getattr(self, '_handle_info', parse_handle(self._mcp_id))
        
        agent_info = {
            "name": self._mcp.name,
            "type": self.__class__.__name__,
            "tools": list(self._mcp_tools.keys()),
            "version": self._mcp_version,
            # Handle info for discovery
            "handle": self._mcp_id,
            "is_handle": handle_info.get("is_handle", False),
            "org": handle_info.get("org"),
            "service": handle_info.get("service"),
            "scope": handle_info.get("scope", "global")
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
            # Check if this is an MCP-decorated agent (has _mcp attribute)
            if hasattr(self, '_mcp') or hasattr(self, '_mcp_tools'):
                return func(self, *args, **kwargs)
            raise TypeError("register_tool can only be used with MCP agents")
        
        # Store tool metadata
        wrapper._mcp_tool = True
        wrapper._mcp_tool_name = name
        wrapper._mcp_tool_description = description or func.__doc__ or f"Call {name}"
        
        return wrapper
    return decorator


# --- Social Handle Convenience Functions ---

def create_handle(name: str, org: Optional[str] = None, service: str = "agent") -> str:
    """
    Create a social handle for an agent.
    
    Args:
        name: Agent name (e.g., "claude", "gpt4", "researcher")
        org: Organization (e.g., "bio-ai", "corp", "finance")
        service: Service type (e.g., "agent", "mcp", "ai")
    
    Returns:
        Formatted handle string
        
    Examples:
        create_handle("claude", service="code-assistant") 
            -> "@claude.code-assistant"
        create_handle("jane", org="corp", service="hr")
            -> "@jane@corp.hr"
    """
    if org:
        return f"@{name}@{org}.{service}"
    return f"@{name}.{service}"


def extract_handle_parts(handle: str) -> Dict[str, Any]:
    """
    Extract parts from a handle for display/logging.
    
    Args:
        handle: Handle string like "@claude.code-assistant" or "@jane@corp.hr"
    
    Returns:
        Dict with name, org, service, scope
    """
    return parse_handle(handle)


# --- Demo/Usage Examples ---

"""
Example Usage with Social Handles:

# 1. Basic handle (global scope)
@mcp_agent(mcp_id="@claude.code-assistant")
class MyCodingAgent:
    def code_review(self, code):
        return "Looks good!"

# 2. Organization handle
@mcp_agent(mcp_id="@researcher@bio-ai.medical")
class BioResearchAgent:
    def analyze_dna(self, sequence):
        return "Analysis complete!"

# 3. Corporate handle
@mcp_agent(mcp_id="@jane@acme.hr")
class HRAgent:
    def process_payroll(self, employee_id):
        return "Payroll processed!"

# 4. Plain string still works (backward compatible)
@mcp_agent(mcp_id="MyAgent123")
class LegacyAgent:
    pass

# 5. Using convenience function
handle = create_handle("assistant", org="startup", service="ai")
# Result: "@assistant@startup.ai"
"""

__all__ = [
    'mcp_agent',
    'MCPAgentDecorator', 
    'register_tool',
    'register_with_server',
    'parse_handle',
    'is_valid_handle',
    'create_handle',
    'extract_handle_parts',
    'HANDLE_PATTERN',
]
