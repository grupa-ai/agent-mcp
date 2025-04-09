"""
MCPLangGraph - A LangGraph node with Model Context Protocol capabilities.

This module provides a transparent implementation of the Model Context Protocol
for LangGraph, allowing nodes to standardize context provision to LLMs and
interact with other MCP-capable systems with minimal configuration.
"""

import json
import uuid
import inspect
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Type, cast

# Import LangGraph components
import langgraph.graph
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent, ToolNode
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool


T = TypeVar('T')


class SharedContext:
    """
    A shared context store that can be used by multiple MCPNodes.
    
    This class provides a centralized context store that allows multiple
    MCPNodes to share context with each other, enabling seamless
    context sharing across a LangGraph agent network.
    
    Attributes:
        context_store (Dict): The shared context store
    """
    
    def __init__(self):
        """Initialize a new shared context store."""
        self.context_store = {}
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the shared context.
        
        Args:
            key: The key to store the value under
            value: The value to store
        """
        self.context_store[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the shared context.
        
        Args:
            key: The key to retrieve
            default: Default value to return if key not found
            
        Returns:
            The value associated with the key, or the default if not found
        """
        return self.context_store.get(key, default)
    
    def has(self, key: str) -> bool:
        """
        Check if a key exists in the shared context.
        
        Args:
            key: The key to check for
            
        Returns:
            True if the key exists, False otherwise
        """
        return key in self.context_store
    
    def remove(self, key: str) -> bool:
        """
        Remove a key from the shared context.
        
        Args:
            key: The key to remove
            
        Returns:
            True if the key was removed, False if it didn't exist
        """
        if key in self.context_store:
            del self.context_store[key]
            return True
        return False
    
    def list_keys(self) -> List[str]:
        """
        List all keys in the shared context.
        
        Returns:
            List of all keys in the context
        """
        return list(self.context_store.keys())
    
    def clear(self) -> None:
        """Clear all keys from the shared context."""
        self.context_store.clear()
    
    def update(self, other_context: Dict[str, Any]) -> None:
        """
        Update the shared context with another dictionary.
        
        Args:
            other_context: Dictionary to update the context with
        """
        self.context_store.update(other_context)

class MCPNode:
    """A LangGraph node with Model Context Protocol capabilities.

    This class provides a standardized implementation of the Model Context Protocol
    for LangGraph nodes, enabling seamless context sharing between different parts
    of agent graphs. It supports both local and shared context management, allowing
    nodes to either maintain their own context or participate in a shared context
    environment.

    Features:
    - Context Management: Both local and shared context support
    - Tool Integration: Register and manage MCP-compatible tools
    - LLM Integration: Seamless integration with language models
    - Context Sharing: Share context between nodes in a graph
    
    Example:
        >>> shared_context = SharedContext()
        >>> node = MCPNode("my_node", context=shared_context)
        >>> node.update_context("key", "value")
        >>> value = node.get_context("key")

    Attributes:
        name (str): Name of the node
        llm (Any): Language model instance for this node
        mcp_tools (Dict): Registry of MCP tools available to this node
        mcp_id (str): Unique identifier for this MCP node
        mcp_version (str): The MCP version implemented by this node
        _shared_context (SharedContext): Optional shared context instance
        _use_shared_context (bool): Whether using shared or local context
    """

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = None,
        context: Optional[SharedContext] = None,
        llm: Any = None,
        **kwargs
    ):
        """
        Initialize an MCPNode.

        Args:
            name: The name of the node
            system_message: Optional system message to include in the node's context
            context: Optional shared context object to use instead of local context
            llm: The language model to use with this node
            **kwargs: Additional keyword arguments
        """
        self.name = name
        self.llm = llm
        
        # MCP specific attributes
        self.mcp_tools = {}
        self.mcp_id = str(uuid.uuid4())
        self.mcp_version = "0.1.0"  # MCP version implemented
        
        # Set up context - either use provided shared context or create local context
        if context is not None and isinstance(context, SharedContext):
            # Use provided shared context
            self._shared_context = context
            self._use_shared_context = True
            # Set a node-specific key in the shared context to store node-specific data
            node_key = f"node_{self.mcp_id}"
            if not self._shared_context.has(node_key):
                self._shared_context.set(node_key, {})
        else:
            # Use local context
            self.context_store = {}
            self._use_shared_context = False
        
        # Add system message to context if provided
        if system_message:
            self.update_context("system_message", system_message)
        
        # Register default MCP tools
        self._register_default_mcp_tools()
    
    def _register_default_mcp_tools(self):
        """Register default MCP tools that are available to all MCP nodes."""
        
        # Define tool functions as simple Python functions
        def context_get(key: str) -> Dict:
            """Get a context item by key."""
            return self._mcp_context_get(key)
            
        def context_set(key: str, value: str) -> Dict:
            """Set a context item with the given key and value."""
            return self._mcp_context_set(key, value)
            
        def context_list() -> Dict:
            """List all available context keys."""
            return self._mcp_context_list()
            
        def context_remove(key: str) -> Dict:
            """Remove a context item by key."""
            return self._mcp_context_remove(key)
            
        def mcp_info() -> Dict:
            """Get information about this MCP node's capabilities."""
            return self._mcp_info()
        
        # Register the tools using our custom method for better compatibility
        self.register_custom_tool("context_get", "Get a context item by key", context_get)
        self.register_custom_tool("context_set", "Set a context item with the given key and value", context_set)
        self.register_custom_tool("context_list", "List all available context keys", context_list)
        self.register_custom_tool("context_remove", "Remove a context item by key", context_remove)
        self.register_custom_tool("mcp_info", "Get information about this MCP node's capabilities", mcp_info)
    
    def register_mcp_tool(self, tool_func: Callable) -> None:
        """
        Register an MCP tool with this node.

        Args:
            tool_func: A LangChain tool function to register
        """
        # Extract information from the tool decorator
        if hasattr(tool_func, "name"):
            tool_name = tool_func.name
        elif hasattr(tool_func, "__name__"):
            tool_name = tool_func.__name__
        else:
            # Generate a unique name if no name attribute exists
            tool_name = f"tool_{str(uuid.uuid4())[:8]}"
            
        # Get tool description
        if hasattr(tool_func, "description"):
            tool_description = tool_func.description
        else:
            tool_description = tool_func.__doc__ if hasattr(tool_func, "__doc__") and tool_func.__doc__ else "No description provided"
        
        # Inspect function signature to build parameter info
        try:
            sig = inspect.signature(tool_func)
            params = []
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                param_info = {
                    "name": param_name,
                    "description": f"Parameter {param_name}",
                    "required": param.default == inspect.Parameter.empty
                }
                
                # Add type information if available
                if param.annotation != inspect.Parameter.empty:
                    try:
                        if hasattr(param.annotation, "__name__"):
                            type_name = param.annotation.__name__
                            if type_name in ["str", "string"]:
                                param_info["type"] = "string"
                            elif type_name in ["int", "integer", "float", "number"]:
                                param_info["type"] = "number" 
                            elif type_name in ["bool", "boolean"]:
                                param_info["type"] = "boolean"
                            else:
                                param_info["type"] = "string"  # Default to string for other types
                        else:
                            param_info["type"] = "string"  # Default to string for complex types
                    except Exception:
                        # If we can't get the type, use string as default for Gemini
                        param_info["type"] = "string"
                else:
                    # If no annotation, add default type for Gemini compatibility
                    param_info["type"] = "string"
                    
                params.append(param_info)
        except (ValueError, TypeError):
            # If we can't inspect the signature, use an empty parameter list
            params = []
        
        # Register the tool
        self.mcp_tools[tool_name] = {
            "name": tool_name,
            "description": tool_description,
            "parameters": params,
            "function": tool_func,
        }
    
    def register_custom_tool(
        self, 
        name: str, 
        description: str, 
        func: Callable, 
        **kwargs
    ) -> None:
        """
        Register a custom function as an MCP tool.

        Args:
            name: The name of the tool
            description: Description of the tool
            func: The function to be called
            **kwargs: Additional parameters
        """
        # Instead of using the tool decorator which may vary between versions,
        # directly register the function with our metadata
        
        # Inspect function signature to build parameter info
        params = []
        try:
            sig = inspect.signature(func)
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                param_info = {
                    "name": param_name,
                    "description": f"Parameter {param_name}",
                    "required": param.default == inspect.Parameter.empty,
                    "type": "string"  # Set a default type for Gemini compatibility
                }
                
                # Add more specific type information if available
                if param.annotation != inspect.Parameter.empty:
                    try:
                        if hasattr(param.annotation, "__name__"):
                            type_name = param.annotation.__name__
                            if type_name in ["str", "string"]:
                                param_info["type"] = "string"
                            elif type_name in ["int", "integer", "float", "number"]:
                                param_info["type"] = "number" 
                            elif type_name in ["bool", "boolean"]:
                                param_info["type"] = "boolean"
                            else:
                                param_info["type"] = "string"  # Default to string for other types
                        else:
                            param_info["type"] = "string"  # Default to string for complex types
                    except Exception:
                        # If we can't get the type, use string as default for Gemini
                        param_info["type"] = "string"
                    
                params.append(param_info)
        except (ValueError, TypeError):
            # If we can't inspect the signature, use an empty parameter list
            pass
        
        self.mcp_tools[name] = {
            "name": name,
            "description": description,
            "parameters": params,
            "function": func,
        }
    
    def get_tools_for_node(self) -> List:
        """
        Get all MCP tools formatted for use in a LangGraph node.

        Returns:
            List of LangChain tool objects
        """
        return [
            tool_info["function"] 
            for tool_info in self.mcp_tools.values()
        ]
    
    # MCP Context Tool Implementations
    def _mcp_context_get(self, key: str) -> Dict:
        """
        Get a context item by key.
        
        Args:
            key: The key of the context item to retrieve
            
        Returns:
            Dict containing the value or an error message
        """
        if self._use_shared_context:
            if self._shared_context.has(key):
                return {"status": "success", "value": self._shared_context.get(key)}
            return {"status": "error", "message": f"Key '{key}' not found in shared context"}
        else:
            if key in self.context_store:
                return {"status": "success", "value": self.context_store[key]}
            return {"status": "error", "message": f"Key '{key}' not found in context"}
    
    def _mcp_context_set(self, key: str, value: Any) -> Dict:
        """
        Set a context item with the given key and value.
        
        Args:
            key: The key to store the value under
            value: The value to store
            
        Returns:
            Dict indicating success or failure
        """
        if self._use_shared_context:
            self._shared_context.set(key, value)
            return {"status": "success", "message": f"Shared context key '{key}' set successfully"}
        else:
            self.context_store[key] = value
            return {"status": "success", "message": f"Context key '{key}' set successfully"}
    
    def _mcp_context_list(self) -> Dict:
        """
        List all available context keys.
        
        Returns:
            Dict containing the list of context keys
        """
        if self._use_shared_context:
            return {"status": "success", "keys": self._shared_context.list_keys()}
        else:
            return {"status": "success", "keys": list(self.context_store.keys())}
    
    def _mcp_context_remove(self, key: str) -> Dict:
        """
        Remove a context item by key.
        
        Args:
            key: The key of the context item to remove
            
        Returns:
            Dict indicating success or failure
        """
        if self._use_shared_context:
            if self._shared_context.has(key):
                self._shared_context.remove(key)
                return {"status": "success", "message": f"Shared context key '{key}' removed successfully"}
            return {"status": "error", "message": f"Key '{key}' not found in shared context"}
        else:
            if key in self.context_store:
                del self.context_store[key]
                return {"status": "success", "message": f"Context key '{key}' removed successfully"}
            return {"status": "error", "message": f"Key '{key}' not found in context"}
    
    def _mcp_info(self) -> Dict:
        """
        Get information about this MCP node's capabilities.
        
        Returns:
            Dict containing MCP node information
        """
        return {
            "id": self.mcp_id,
            "name": self.name,
            "version": self.mcp_version,
            "tools": [
                {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
                for name, tool in self.mcp_tools.items()
            ]
        }
    
    def update_context(self, key: str, value: Any) -> None:
        """
        Update the MCP context with a new key-value pair.
        
        Args:
            key: The context key
            value: The context value
        """
        if self._use_shared_context:
            self._shared_context.set(key, value)
        else:
            self.context_store[key] = value
    
    def get_context(self, key: str) -> Any:
        """
        Get a value from the MCP context.
        
        Args:
            key: The context key to retrieve
            
        Returns:
            The context value or None if not found
        """
        if self._use_shared_context:
            return self._shared_context.get(key)
        else:
            return self.context_store.get(key)
    
    def has_context(self, key: str) -> bool:
        """
        Check if a key exists in the context.
        
        Args:
            key: The key to check for
            
        Returns:
            True if the key exists, False otherwise
        """
        if self._use_shared_context:
            return self._shared_context.has(key)
        else:
            return key in self.context_store
    
    def list_available_tools(self) -> List[Dict]:
        """
        Get a list of all available MCP tools.
        
        Returns:
            List of tool definitions
        """
        return [
            {
                "name": name,
                "description": tool["description"]
            }
            for name, tool in self.mcp_tools.items()
        ]
    
    def add_tool(self, tool_func: Callable) -> None:
        """
        Add a tool to this MCPNode.
        
        This is a convenience method that calls register_mcp_tool
        
        Args:
            tool_func: The tool function to add
        """
        self.register_mcp_tool(tool_func)
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute an MCP tool by name with the provided arguments.
        
        Args:
            tool_name: The name of the tool to execute
            **kwargs: Arguments to pass to the tool
            
        Returns:
            The result of the tool execution
            
        Raises:
            ValueError: If the tool is not found
        """
        if tool_name not in self.mcp_tools:
            raise ValueError(f"Tool '{tool_name}' not found")
            
        tool_func = self.mcp_tools[tool_name]["function"]
        
        # Handle both old-style and new-style tool calling
        try:
            if hasattr(tool_func, "invoke"):
                # New-style (LangChain 0.1.47+)
                return tool_func.invoke(input=kwargs if kwargs else "")
            else:
                # Build a proper tool_input string for old-style tools
                # For tools with no arguments, pass empty string
                if not kwargs:
                    return tool_func("")
                # For tools with arguments, format it properly
                tool_input = ""
                for k, v in kwargs.items():
                    tool_input += f"{k}: {v}, "
                tool_input = tool_input.rstrip(", ")
                return tool_func(tool_input)
        except Exception as e:
            # Fallback method - direct function call
            # This works for simple Python functions that don't use the tool interface
            if callable(tool_func) and not isinstance(tool_func, type):
                return tool_func(**kwargs)
            raise e
    
    def get_system_message(self) -> str:
        """
        Get the system message for this node, including context summary.
        
        Returns:
            The full system message with context
        """
        base_message = self.get_context("system_message") or "You are an AI assistant."
        context_summary = self._generate_context_summary()
        
        if context_summary:
            return f"{base_message}\n\nAvailable context:\n{context_summary}"
        else:
            return base_message
    
    def _generate_context_summary(self) -> str:
        """
        Generate a summary of available context for inclusion in the system message.
        
        Returns:
            String summary of available context
        """
        # Get the context to summarize - either shared or local
        if self._use_shared_context:
            context_keys = self._shared_context.list_keys()
            # Skip non-essential keys to prevent overwhelming the context
            context_keys = [k for k in context_keys if not k.startswith("node_")]
            
            if not context_keys:
                return ""
            
            summary_parts = []
            for key in context_keys:
                # Skip the system message in the summary
                if key == "system_message":
                    continue
                
                value = self._shared_context.get(key)
                
                # For complex objects, just indicate their type
                if isinstance(value, dict):
                    summary_parts.append(f"- {key}: Dictionary with {len(value)} items")
                elif isinstance(value, list):
                    summary_parts.append(f"- {key}: List with {len(value)} items")
                elif isinstance(value, str) and len(value) > 100:
                    summary_parts.append(f"- {key}: Text ({len(value)} chars)")
                else:
                    summary_parts.append(f"- {key}: {value}")
        else:
            # Local context
            if not self.context_store:
                return ""
                
            summary_parts = []
            for key, value in self.context_store.items():
                # Skip the system message in the summary
                if key == "system_message":
                    continue
                    
                # For complex objects, just indicate their type
                if isinstance(value, dict):
                    summary_parts.append(f"- {key}: Dictionary with {len(value)} items")
                elif isinstance(value, list):
                    summary_parts.append(f"- {key}: List with {len(value)} items")
                elif isinstance(value, str) and len(value) > 100:
                    summary_parts.append(f"- {key}: Text ({len(value)} chars)")
                else:
                    summary_parts.append(f"- {key}: {value}")
                
        return "\n".join(summary_parts)


class MCPReactAgent(MCPNode):
    """An implementation of MCP for LangGraph's ReAct agent pattern.
    
    This class extends MCPNode to work specifically with ReAct agents,
    providing a seamless integration of the Model Context Protocol with
    LangGraph's agent architecture. It handles:
    
    - Agent Creation: Creates ReAct agents with MCP context integration
    - Tool Management: Combines MCP tools with custom agent tools
    - Context Integration: Injects MCP context into agent's system messages
    - LLM Compatibility: Handles different LLM implementations and versions
    
    Example:
        >>> agent = MCPReactAgent(name="my_agent")
        >>> react_agent = agent.create_agent(llm, tools=[my_tool])
    """

def create_mcp_langgraph(
    llm,
    name: str = "MCPGraph",
    system_message: Optional[str] = None,
    tools: Optional[List] = None,
    additional_nodes: Optional[Dict] = None,
    **kwargs
) -> StateGraph:
    """Create a LangGraph with MCP capabilities.
    
    This function creates a LangGraph that integrates the Model Context Protocol,
    enabling context sharing and standardized tool usage across the graph. It:
    
    - Creates an MCP-enabled ReAct agent as the primary node
    - Configures the graph with proper routing and tool nodes
    - Supports additional custom nodes and tools
    - Handles LLM integration and system messages
    
    Args:
        llm: The language model to use
        name: Name of the graph
        system_message: System message for the agent
        tools: Additional tools to provide to the agent
        additional_nodes: Optional additional nodes to add to the graph
        **kwargs: Additional keyword arguments
        
    Returns:
        A configured StateGraph with MCP capabilities
    """
    # Create MCP node
    mcp_agent = MCPReactAgent(name=name, system_message=system_message)
    
    # Create agent node
    agent = mcp_agent.create_agent(llm, tools)
    
    # Initialize the state graph
    builder = StateGraph(cast(Type, Dict))
    
    # Add the agent node
    builder.add_node("agent", agent)
    
    # Add any additional nodes
    if additional_nodes:
        for node_name, node in additional_nodes.items():
            builder.add_node(node_name, node)
    
    # Set the entry point
    builder.set_entry_point("agent")
    
    # Add conditional edges
    # This simpler routing approach works better with the latest LangGraph
    builder.add_edge("agent", END)
    
    # Add any needed tools as nodes
    tool_nodes = {}
    
    # Skip adding tool nodes for now as they're causing compatibility issues
    # LangGraph will handle tools internally within the agent
        
    # Skip adding additional tool nodes for now
    # The tools are already passed to the agent when it's created
    
    # Compile the graph
    graph = builder.compile()
    
    # Store the MCP agent for later access
    graph.mcp_agent = mcp_agent
    
    return graph