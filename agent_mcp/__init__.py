"""
AgentMCP - Model Context Protocol for AI Agents
"""

from .mcp_agent import MCPAgent
from .mcp_decorator import mcp_agent
from .enhanced_mcp_agent import EnhancedMCPAgent
from .mcp_transport import MCPTransport, HTTPTransport
from .heterogeneous_group_chat import HeterogeneousGroupChat

# Framework adapters
from .langchain_mcp_adapter import LangchainMCPAdapter
from .crewai_mcp_adapter import CrewAIMCPAdapter
from .langgraph_mcp_adapter import LangGraphMCPAdapter
from .argo_agent_mcp_adapter import ArgoAgentMcpAdapter, PlaceholderArgoAgent
from .llama_index_mcp_adapter import LlamaIndexMcpAdapter, PlaceholderLlamaIndexAgent

__version__ = "0.1.2"

__all__ = [
    "MCPAgent",
    "mcp_agent", # Corresponds to AgentMCPDecorator functionality
    "EnhancedMCPAgent",
    "MCPTransport",
    "HTTPTransport",
    "HeterogeneousGroupChat",
    "LangchainMCPAdapter",
    "CrewAIMCPAdapter",
    "LangGraphMCPAdapter",
    "ArgoAgentMcpAdapter",
    "PlaceholderArgoAgent",
    "LlamaIndexMcpAdapter",
    "PlaceholderLlamaIndexAgent",
]