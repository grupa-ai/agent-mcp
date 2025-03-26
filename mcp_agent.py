"""
MCPAgent - An AutoGen agent with Model Context Protocol capabilities.

This module provides a transparent implementation of the Model Context Protocol
for AutoGen agents, allowing them to standardize context provision to LLMs and
interact with other MCP-capable systems with minimal configuration.

For demonstration purposes, this implementation includes a fallback mode that works
without requiring the actual AutoGen library.
"""

import json
import uuid
import inspect
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

# For demonstration purposes, we'll always use a simple base class
# This allows us to run without requiring the full AutoGen library

# Define our simple base agent class for demonstration
class DemoBaseAgent:
    """Simple base agent class for demonstration when AutoGen is not available."""
    
    def __init__(
        self,
        name: str,
        system_message: Optional[str] = None,
        is_termination_msg: Optional[Callable] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: str = "NEVER",
        **kwargs
    ):
        self.name = name
        self.system_message = system_message or "I am a demo agent."
        self.is_termination_msg = is_termination_msg
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        self.human_input_mode = human_input_mode
        self.functions = {}
        self.llm_config = kwargs.get("llm_config")
        
    def register_function(self, function_map, name=None, description=None):
        """Register a function with this agent."""
        for func_name, func in function_map.items():
            self.functions[func_name] = func
            
    def generate_reply(self, messages=None, sender=None, exclude_list=None, **kwargs):
        """Generate a reply (stub for demo)."""
        return f"This is a demo reply from {self.name}. In a real implementation, this would use an LLM."
        
# Define a simple Agent class for use in type hints
class Agent(DemoBaseAgent):
    """Simple Agent class for demonstration."""
    pass

# Use the demo base agent class as our base
BaseAgentClass = DemoBaseAgent

print("Note: Running in demonstration mode.")
print("This implementation simulates MCP functionality without requiring the full AutoGen library.")


class MCPAgent(BaseAgentClass):
    """
    An AutoGen agent with Model Context Protocol capabilities.

    This agent extends the ConversableAgent to implement the Model Context Protocol,
    enabling standardized context provision to LLMs and seamless interaction with
    other MCP-capable systems.

    Attributes:
        context_store (Dict): Store for the agent's current context
        mcp_tools (Dict): Dictionary of MCP tools available to this agent
        mcp_id (str): Unique identifier for this MCP agent
        mcp_version (str): The MCP version implemented by this agent
    """

    def __init__(
        self,
        name: str,
        system_message: Optional[str] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: str = "NEVER",
        **kwargs,
    ):
        """
        Initialize an MCPAgent.

        Args:
            name: The name of the agent
            system_message: System message for the agent
            is_termination_msg: Function to determine if a message should terminate a conversation
            max_consecutive_auto_reply: Maximum number of consecutive automated replies
            human_input_mode: Human input mode setting
            **kwargs: Additional keyword arguments passed to ConversableAgent
        """
        if system_message is None:
            system_message = (
                "You are an AI assistant that follows the Model Context Protocol (MCP). "
                "You can access and manipulate context through the provided MCP tools. "
                "Use these tools to enhance your responses with relevant information."
            )

        super().__init__(
            name=name,
            system_message=system_message,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            **kwargs,
        )

        # MCP specific attributes
        self.context_store = {}
        self.mcp_tools = {}
        self.mcp_id = str(uuid.uuid4())
        self.mcp_version = "0.1.0"  # MCP version implemented

        # Register default MCP tools
        self._register_default_mcp_tools()

    def _register_default_mcp_tools(self):
        """Register default MCP tools that are available to all MCP agents."""
        
        # Context management tools
        self.register_mcp_tool(
            name="context.get",
            description="Get a specific context item by key",
            func=self._mcp_context_get,
        )
        
        self.register_mcp_tool(
            name="context.set",
            description="Set a context item with the given key and value",
            func=self._mcp_context_set,
        )
        
        self.register_mcp_tool(
            name="context.list",
            description="List all available context keys",
            func=self._mcp_context_list,
        )
        
        self.register_mcp_tool(
            name="context.remove",
            description="Remove a context item by key",
            func=self._mcp_context_remove,
        )

        # Metadata tools
        self.register_mcp_tool(
            name="mcp.info",
            description="Get information about this MCP agent's capabilities",
            func=self._mcp_info,
        )

    def register_mcp_tool(
        self, name: str, description: str, func: Callable, **kwargs
    ) -> None:
        """
        Register an MCP tool with this agent.

        Args:
            name: The name of the tool, used for invocation
            description: Description of what the tool does
            func: The function to be called when the tool is invoked
            **kwargs: Additional tool configuration
        """
        if name in self.mcp_tools:
            print(f"Warning: Overriding existing MCP tool '{name}'")

        # Inspect function signature to build parameter info
        sig = inspect.signature(func)
        params = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            param_info = {
                "name": param_name,
                "description": kwargs.get(f"{param_name}_description", f"Parameter {param_name}"),
                "required": param.default == inspect.Parameter.empty
            }
            
            # Add type information if available
            if param.annotation != inspect.Parameter.empty:
                param_info["type"] = str(param.annotation.__name__)
                
            params.append(param_info)

        # Register the tool
        self.mcp_tools[name] = {
            "name": name,
            "description": description,
            "parameters": params,
            "function": func,
        }

        # Also register as an AutoGen function tool
        def tool_wrapper(*args, **kwargs):
            return func(self, *args, **kwargs)
        
        # Different implementation based on whether we're using actual AutoGen or our demo version
        try:
            # For actual AutoGen, which has a different register_function signature
            self.register_function(
                function_map={name: tool_wrapper},
            )
        except TypeError:
            # For our demo version
            self.register_function(
                function_map={name: tool_wrapper},
                name=name,
                description=description,
            )

    def register_agent_as_tool(self, agent: Agent, name: Optional[str] = None) -> None:
        """
        Register another agent as a tool that can be called by this agent.

        Args:
            agent: The agent to register as a tool
            name: Optional custom name for the tool, defaults to agent's name
        """
        if name is None:
            name = f"agent.{agent.name}"
            
        def agent_tool_wrapper(self, message: str, **kwargs):
            """Wrapper to call another agent and return its response."""
            response = agent.generate_reply(sender=self, message=message)
            return {"response": response if response else "No response from agent."}
            
        self.register_mcp_tool(
            name=name,
            description=f"Send a message to agent '{agent.name}' and get their response",
            func=agent_tool_wrapper,
            message_description="The message to send to the agent"
        )

    # MCP Context Tool Implementations
    def _mcp_context_get(self, key: str) -> Dict:
        """
        Get a context item by key.
        
        Args:
            key: The key of the context item to retrieve
            
        Returns:
            Dict containing the value or an error message
        """
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
        self.context_store[key] = value
        return {"status": "success", "message": f"Context key '{key}' set successfully"}

    def _mcp_context_list(self) -> Dict:
        """
        List all available context keys.
        
        Returns:
            Dict containing the list of context keys
        """
        return {"status": "success", "keys": list(self.context_store.keys())}

    def _mcp_context_remove(self, key: str) -> Dict:
        """
        Remove a context item by key.
        
        Args:
            key: The key of the context item to remove
            
        Returns:
            Dict indicating success or failure
        """
        if key in self.context_store:
            del self.context_store[key]
            return {"status": "success", "message": f"Context key '{key}' removed successfully"}
        return {"status": "error", "message": f"Key '{key}' not found in context"}

    def _mcp_info(self) -> Dict:
        """
        Get information about this MCP agent's capabilities.
        
        Returns:
            Dict containing MCP agent information
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

    # Override ConversableAgent methods to integrate MCP
    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        exclude_list: Optional[List[str]] = None,
        **kwargs,
    ) -> Union[str, Dict, None]:
        """
        Generate a reply based on the conversation history and with MCP context.

        This overrides the base ConversableAgent method to integrate MCP context
        into the generation process.

        Args:
            messages: Optional list of messages to process
            sender: The sender agent of the message
            exclude_list: List of function names to exclude from auto-function calling
            **kwargs: Additional keyword arguments

        Returns:
            The generated reply
        """
        # Inject MCP context into the prompt if available
        if messages:
            last_message = messages[-1]
            if "content" in last_message and isinstance(last_message["content"], str):
                # Check if message contains MCP tool calls
                self._process_mcp_tool_calls(last_message)
                
        # Inject context information into system message
        original_system = self.system_message
        if hasattr(self, "llm_config") and self.llm_config:
            context_summary = self._generate_context_summary()
            
            if context_summary:
                self.system_message = f"{original_system}\n\nAvailable context:\n{context_summary}"
        
        try:
            # Call the parent class method to generate the reply
            reply = super().generate_reply(
                messages=messages, sender=sender, exclude_list=exclude_list, **kwargs
            )
            return reply
        finally:
            # Restore original system message
            self.system_message = original_system

    def _generate_context_summary(self) -> str:
        """
        Generate a summary of available context for inclusion in the system message.
        
        Returns:
            String summary of available context
        """
        if not self.context_store:
            return ""
            
        summary_parts = []
        for key, value in self.context_store.items():
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

    def _process_mcp_tool_calls(self, message: Dict) -> None:
        """
        Process any MCP tool calls in a message.
        
        Args:
            message: The message to process for tool calls
        """
        content = message.get("content", "")
        if not isinstance(content, str):
            return
            
        # Very simple parsing for tool calls - in production would use more robust methods
        tool_call_pattern = r"mcp\.call\(([^)]+)\)"
        import re
        
        tool_calls = re.findall(tool_call_pattern, content)
        for call in tool_calls:
            try:
                # Parse the tool call arguments
                call_args = json.loads(f"{{{call}}}")
                tool_name = call_args.get("tool")
                arguments = call_args.get("arguments", {})
                
                if tool_name in self.mcp_tools:
                    # Execute the tool
                    result = self.mcp_tools[tool_name]["function"](self, **arguments)
                    
                    # Store the result in the context
                    result_key = f"result_{uuid.uuid4().hex[:8]}"
                    self.context_store[result_key] = result
            except Exception as e:
                print(f"Error processing MCP tool call: {e}")

    def update_context(self, key: str, value: Any) -> None:
        """
        Update the MCP context with a new key-value pair.
        
        Args:
            key: The context key
            value: The context value
        """
        self.context_store[key] = value
    
    def get_context(self, key: str) -> Any:
        """
        Get a value from the MCP context.
        
        Args:
            key: The context key to retrieve
            
        Returns:
            The context value or None if not found
        """
        return self.context_store.get(key)
    
    def list_available_tools(self) -> List[Dict]:
        """
        Get a list of all available MCP tools.
        
        Returns:
            List of tool definitions
        """
        return [
            {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            for name, tool in self.mcp_tools.items()
        ]
        
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
            
        tool = self.mcp_tools[tool_name]
        return tool["function"](self, **kwargs)
