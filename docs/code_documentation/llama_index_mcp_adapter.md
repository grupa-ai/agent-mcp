# LlamaIndexMcpAdapter

## Overview

The `LlamaIndexMcpAdapter` class is designed to integrate LlamaIndex agents into the Multi-Agent Communication Protocol (MCP) ecosystem. This allows agents built with LlamaIndex, known for their powerful capabilities in retrieval augmented generation (RAG) and data interaction, to communicate and collaborate with other MCP-compatible agents, regardless of their underlying framework.

The adapter handles the translation of MCP messages to a format suitable for LlamaIndex agents (typically a task description or query string) and converts the LlamaIndex agent's responses back into MCP messages for transmission over the network.

**Note:** The initial implementation uses a `PlaceholderLlamaIndexAgent`. When using this adapter with actual LlamaIndex agents, the `llama_index_agent` parameter in the constructor should be an instance of your configured LlamaIndex agent (e.g., `OpenAIAgent`, `ReActAgent`, or a custom query engine).

## Class Definition

```python
from agent_mcp.mcp_agent import MCPAgent
from agent_mcp.mcp_transport import MCPTransport
from agent_mcp.llama_index_mcp_adapter import PlaceholderLlamaIndexAgent # Replace with actual LlamaIndex agent import
from typing import Dict, Any, Optional

class LlamaIndexMcpAdapter(MCPAgent):
    def __init__(self,
                 name: str,
                 llama_index_agent: PlaceholderLlamaIndexAgent, # Will be actual LlamaIndex agent type
                 transport: Optional[MCPTransport] = None,
                 client_mode: bool = False,
                 execution_method_name: str = "chat", # e.g., "chat", "query"
                 system_message: str = "I am a LlamaIndex agent integrated with MCP.",
                 **kwargs):
        # ... implementation ...
```

## Initialization Parameters

-   `name` (str): The unique name for this MCP agent instance.
-   `llama_index_agent` (PlaceholderLlamaIndexAgent | ActualLlamaIndexAgent): An instance of a LlamaIndex agent or query engine. This is the agent that will process tasks/queries.
-   `transport` (Optional[MCPTransport]): An instance of an MCPTransport implementation (e.g., `HTTPTransport`).
-   `client_mode` (bool): If `True`, the adapter operates primarily as a client.
-   `execution_method_name` (str): The name of the method on the `llama_index_agent` instance that should be called to process tasks. Common LlamaIndex methods include "chat" or "query". This allows flexibility in how the adapter interacts with different types of LlamaIndex agents or query engines.
-   `system_message` (str): A default system message or persona description.
-   `**kwargs`: Additional keyword arguments passed to the base `MCPAgent` constructor.

## Key Methods

### `handle_incoming_message(message: Dict[str, Any], message_id: Optional[str] = None)`

Processes messages received from the MCP network. Tasks are identified and queued for processing by the `process_tasks` method. It uses `MCPAgent._should_process_message` for idempotency.

### `process_tasks()`

An asynchronous loop that dequeues tasks. For each task:
1.  It dynamically calls the method specified by `execution_method_name` (e.g., `llama_index_agent.chat()`) on the `llama_index_agent` instance, passing the task description.
2.  LlamaIndex agents often return a response object (like `AgentChatResponse`). The adapter converts this response object to a string (typically by calling `str()` on it, assuming the response object has a sensible string representation) to get the result data.
3.  If a `reply_to` field was present, the result is sent back to the requesting MCP agent via the transport.
4.  Acknowledges the original message if an `original_message_id` and transport are available.
5.  Marks the task as completed using `MCPAgent._mark_task_completed`.

### `run()`

Starts the agent's main operational loops: the task processor and, if applicable, a client message receiver.

### `stop()`

Gracefully stops the agent's running loops.

### `connect_to_mcp_server(server_url: str, registration_payload: Optional[Dict[str, Any]] = None)`

An example utility for client agents to register with an MCP server/coordinator.

## Usage Example

```python
import asyncio
from agent_mcp import LlamaIndexMcpAdapter, PlaceholderLlamaIndexAgent
from agent_mcp.mcp_transport import HTTPTransport # Example transport

async def main():
    # 1. Initialize a (Placeholder) LlamaIndex Agent
    # In a real scenario, this would be your configured LlamaIndex agent
    # e.g., from llama_index.agent.openai import OpenAIAgent
    my_llama_bot = PlaceholderLlamaIndexAgent(name="MyLlamaBot")

    # 2. Initialize transport (optional here, depends on deployment)
    # client_transport = HTTPTransport()

    # 3. Initialize the Adapter
    llama_mcp_adapter = LlamaIndexMcpAdapter(
        name="LlamaAdapter1",
        llama_index_agent=my_llama_bot,
        # transport=client_transport,
        client_mode=True,
        execution_method_name="chat" # Or "query", matching your LlamaIndex agent's API
    )

    # Example of simulating a received task
    mock_task_message = {
        "type": "task",
        "task_id": "llama_task_001",
        "description": "What are the latest advancements in quantum computing?",
        "reply_to": "ResearcherAgent42",
        "content": {
            "task_id": "llama_task_001",
            "description": "What are the latest advancements in quantum computing?",
            "reply_to": "ResearcherAgent42"
        }
    }
    mock_message_id = "msg_xyz_789"

    # Start adapter (typically in a managed environment or its own task)
    # run_task = asyncio.create_task(llama_mcp_adapter.run())

    # Simulate message handling
    # await llama_mcp_adapter.handle_incoming_message(mock_task_message, mock_message_id)

    print(f"{llama_mcp_adapter.name} initialized.")

    # await asyncio.sleep(5) # Allow time for processing if tasks were real
    # await llama_mcp_adapter.stop()
    # run_task.cancel()

if __name__ == "__main__":
    # asyncio.run(main())
    print("LlamaIndexMcpAdapter documentation snippet. Run full examples from the /demos directory.")
```

## Integration with MCP Core and LlamaIndex

-   **MCP Core**: Leverages `MCPAgent` for common functionalities like MCP ID, message idempotency, and sender identification.
-   **LlamaIndex**: Interacts with the provided LlamaIndex agent instance by calling a specified method (e.g., `chat`, `query`). The adapter is designed to be flexible; ensure the `execution_method_name` matches an existing method on your LlamaIndex agent that accepts a string input and returns a value convertible to a string result.
-   **Transport Agnostic**: Like other MCP adapters, it works with any `MCPTransport`-compliant transport layer.
```
