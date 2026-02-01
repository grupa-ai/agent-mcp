"""
AgentMCP - Model Context Protocol for AI Agents
"""

__version__ = "0.1.4"

# Core components
try:
    from .mcp_agent import MCPAgent
except ImportError:
    MCPAgent = None

try:
    from .mcp_decorator import mcp_agent
except ImportError:
    mcp_agent = None

try:
    from .enhanced_mcp_agent import EnhancedMCPAgent
except ImportError:
    EnhancedMCPAgent = None

try:
    from .mcp_transport import MCPTransport, HTTPTransport
except ImportError:
    MCPTransport = None
    HTTPTransport = None

try:
    from .heterogeneous_group_chat import HeterogeneousGroupChat
except ImportError:
    HeterogeneousGroupChat = None

# Framework adapters (conditional imports to avoid dependency conflicts)
try:
    from .langchain_mcp_adapter import LangchainMCPAdapter
except ImportError:
    LangchainMCPAdapter = None

try:
    from .crewai_mcp_adapter import CrewAIMCPAdapter
except ImportError:
    CrewAIMCPAdapter = None

try:
    from .langgraph_mcp_adapter import LangGraphMCPAdapter
except ImportError:
    LangGraphMCPAdapter = None
