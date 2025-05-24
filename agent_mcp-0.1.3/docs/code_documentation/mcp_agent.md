# MCPAgent Documentation

## Overview
The `MCPAgent` class is a core component of the AgentMCP ecosystem that extends AutoGen's `ConversableAgent` to implement the Model Context Protocol (MCP). It provides standardized context management, tool registration, and inter-agent communication capabilities.

## Class Structure

### Core Attributes
- `context_store`: Dictionary storing agent's contextual information
- `mcp_tools`: Registry of MCP-compatible tools
- `mcp_id`: Unique identifier for the agent instance
- `mcp_version`: Version of MCP protocol implemented
- `completed_task_ids`: Set tracking completed tasks for idempotency

### Constructor Parameters
- `name`: Agent's name
- `system_message`: Initial system message (optional)
- `is_termination_msg`: Function to determine conversation termination
- `max_consecutive_auto_reply`: Maximum consecutive automated replies
- `human_input_mode`: Human input mode setting (default: "NEVER")

## Core Functionality

### Tool Management
1. `register_mcp_tool(name, description, func, **kwargs)`
   - Registers new MCP-compatible tools
   - Automatically inspects function signatures
   - Creates AutoGen-compatible function schemas

2. `register_agent_as_tool(agent, name=None)`
   - Registers another agent as a callable tool
   - Enables direct agent-to-agent communication

### Context Management
1. Basic Operations:
   - `has_context(key)`: Checks existence of context key
   - `update_context(key, value)`: Updates context
   - `get_context(key)`: Retrieves context value

2. MCP Protocol Methods:
   - `_mcp_context_get(key)`: Gets context with status
   - `_mcp_context_set(key, value)`: Sets context with confirmation
   - `_mcp_context_list()`: Lists all context keys
   - `_mcp_context_remove(key)`: Removes context items

### Message Processing
1. `generate_reply(messages, sender, exclude_list, **kwargs)`
   - Overrides base AutoGen method
   - Integrates MCP context into generation
   - Processes tool calls in messages

2. `_process_mcp_tool_calls(message)`
   - Handles multiple tool call formats:
     - OpenAI function calls
     - Explicit MCP calls
     - Natural language detection

### Task Management
1. `_mark_task_completed(task_id)`
   - Tracks completed tasks
   - Ensures idempotent processing

2. `_should_process_message(message)`
   - Prevents duplicate task processing
   - Validates message format

## Helper Functions
1. `_generate_context_summary()`
   - Creates human-readable context summaries
   - Handles different value types appropriately

2. `list_available_tools()`
   - Returns list of registered tools
   - Includes descriptions and parameters

3. `execute_tool(tool_name, **kwargs)`
   - Direct tool execution interface
   - Validates tool existence and parameters

## Default MCP Tools
The agent comes with pre-registered tools for basic operations:
- `context_get`: Retrieve context values
- `context_set`: Store context values
- `context_list`: List available context keys
- `context_remove`: Remove context entries
- `mcp_info`: Get agent capability information

## Usage Example
```python
# Create an MCP agent
agent = MCPAgent(name="my_agent")

# Register a custom tool
agent.register_mcp_tool(
    name="my_tool",
    description="Does something",
    func=my_func
)

# Use context management
agent.context_set("key", "value")
context = agent.context_get("key")
```

## Best Practices
1. Always check tool existence before execution
2. Use appropriate error handling for context operations
3. Implement idempotency for critical operations
4. Maintain clear tool documentation
5. Follow MCP protocol standards for compatibility