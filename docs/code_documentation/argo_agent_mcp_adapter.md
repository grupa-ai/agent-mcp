# ArgoAgentMcpAdapter

## Overview

The `ArgoAgentMcpAdapter` class facilitates the integration of Argo Agents with the Multi-Agent Communication Protocol (MCP) ecosystem. It allows Argo Agents to send and receive messages, participate in collaborative tasks, and interact with agents developed using other frameworks that are also MCP-compatible.

This adapter acts as a bridge, translating MCP messages into a format that Argo Agents can understand and process, and converting Argo Agent responses back into MCP messages.

**Note:** The initial implementation uses a `PlaceholderArgoAgent` as the direct Argo Agent library details were not fully available. This placeholder simulates the expected behavior of an Argo Agent. When integrating with a live Argo Agent system, the `argo_agent` parameter in the constructor should be an instance of the actual Argo Agent.

## Class Definition

```python
from agent_mcp.mcp_agent import MCPAgent
from agent_mcp.mcp_transport import MCPTransport
from agent_mcp.argo_agent_mcp_adapter import PlaceholderArgoAgent # Replace with actual ArgoAgent import
from typing import Dict, Any, Optional

class ArgoAgentMcpAdapter(MCPAgent):
    def __init__(self,
                 name: str,
                 argo_agent: PlaceholderArgoAgent, # Will be the actual Argo Agent type
                 transport: Optional[MCPTransport] = None,
                 client_mode: bool = False,
                 system_message: str = "I am an Argo agent integrated with MCP.",
                 **kwargs):
        # ... implementation ...
```

## Initialization Parameters

-   `name` (str): The unique name for this MCP agent instance.
-   `argo_agent` (PlaceholderArgoAgent | ActualArgoAgent): An instance of an Argo Agent (or its placeholder). This is the agent that will perform tasks.
-   `transport` (Optional[MCPTransport]): An instance of an MCPTransport implementation (e.g., `HTTPTransport`, `FirebaseTransport`). This handles the low-level communication.
-   `client_mode` (bool): If `True`, the adapter operates primarily as a client, often initiating connections or relying on a polling mechanism set up by the transport to receive messages. If `False`, it might imply a server role, though this adapter's current primary focus is client-side interaction or interaction within a managed group.
-   `system_message` (str): A default system message or persona description for the agent.
-   `**kwargs`: Additional keyword arguments passed to the base `MCPAgent` constructor.

## Key Methods

### `handle_incoming_message(message: Dict[str, Any], message_id: Optional[str] = None)`

Processes messages received from the MCP network. If the message is a "task", it's added to an internal queue for the `process_tasks` method. It utilizes `MCPAgent._should_process_message` for idempotency.

### `process_tasks()`

An asynchronous loop that retrieves tasks from the internal queue. For each task:
1.  It calls the `arun` method of the `argo_agent` instance, passing the task description. (This assumes the Argo Agent has a compatible async execution method).
2.  It takes the result from the Argo Agent.
3.  If a `reply_to` field was present in the original task, it sends the result back to the specified MCP agent using the transport layer.
4.  It acknowledges the original message if an `original_message_id` and transport are available.
5.  It marks the task as completed using `MCPAgent._mark_task_completed`.

### `run()`

Starts the agent's main operations. It typically launches the `process_tasks` loop and, if in `client_mode` with a suitable transport, a `_client_message_receiver` loop to poll for incoming messages.

### `stop()`

Gracefully shuts down the agent's running loops (task processor and message receiver).

### `connect_to_mcp_server(server_url: str, registration_payload: Optional[Dict[str, Any]] = None)`

An example utility method for client agents to register themselves with a central MCP server or coordinator. The actual registration message format may vary based on the server's requirements.

## Usage Example

```python
import asyncio
from agent_mcp import ArgoAgentMcpAdapter, PlaceholderArgoAgent
from agent_mcp.mcp_transport import HTTPTransport # Example transport

async def main():
    # 1. Initialize a (Placeholder) Argo Agent
    my_argo_bot = PlaceholderArgoAgent(name="MyArgoBot")

    # 2. Initialize a transport (if this agent needs to actively send/receive)
    # For client mode, transport might be used for sending and polling.
    # For a more complex setup, this agent might be part of a HeterogeneousGroupChat
    # which manages transport and message routing.

    # Example: if this agent is a client connecting to a known MCP service
    # client_transport = HTTPTransport() # Configure as needed

    # 3. Initialize the Adapter
    argo_mcp_adapter = ArgoAgentMcpAdapter(
        name="ArgoAdapter1",
        argo_agent=my_argo_bot,
        # transport=client_transport, # Assign if used
        client_mode=True # Example
    )

    # To make it do something, you'd typically have it connect to an MCP network
    # or receive tasks through its transport if it's set up to listen.

    # Example: Simulate receiving a task (in a real scenario, this comes via transport)
    mock_task_message = {
        "type": "task",
        "task_id": "argo_task_001",
        "description": "Summarize the latest AI news.",
        "reply_to": "RequestingAgent789", # MCP ID of the agent that sent the task
        "content": { # Often, details are in a 'content' sub-object
            "task_id": "argo_task_001",
            "description": "Summarize the latest AI news.",
            "reply_to": "RequestingAgent789"
        }
    }
    mock_message_id = "msg_abc_123"

    # Start the adapter's processing loops (in a background task if non-blocking needed)
    # run_task = asyncio.create_task(argo_mcp_adapter.run())

    # Simulate the adapter receiving a message
    # await argo_mcp_adapter.handle_incoming_message(mock_task_message, mock_message_id)

    # In a real system, the adapter would run its loops and interact over the network.
    # For this example, we are not running full network loops.
    print(f"{argo_mcp_adapter.name} initialized.")

    # To properly test, you'd need a running asyncio loop and potentially other agents.
    # await asyncio.sleep(5) # Keep alive for a bit if tasks were real
    # await argo_mcp_adapter.stop()
    # run_task.cancel()

if __name__ == "__main__":
    # asyncio.run(main())
    print("ArgoAgentMcpAdapter documentation snippet. Run full examples from the /demos directory.")
```

## Integration with MCP Core

The `ArgoAgentMcpAdapter` relies on the core functionalities provided by `MCPAgent` for:
-   Unique MCP ID generation (`mcp_id`).
-   Idempotent message processing (`_should_process_message`, `_mark_task_completed`).
-   Standardized message sender extraction (`_extract_sender`).

It uses an `MCPTransport` instance for actual network communication, making it transport-agnostic (e.g., can use HTTP, WebSockets, Firebase, etc., as long as the transport conforms to the `MCPTransport` interface).
```
