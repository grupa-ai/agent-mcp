"""
AgentMCP - Model Context Protocol for AI Agents
"""

__version__ = "0.1.7"

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

# Additional AI SDK adapters
try:
    from .claude_mcp_adapter import ClaudeMCPAdapter
except ImportError:
    ClaudeMCPAdapter = None

try:
    from .google_ai_mcp_adapter import GoogleAIMCPAdapter
except ImportError:
    GoogleAIMCPAdapter = None

# Agent Lightning (as enhancement library, not adapter)
try:
    from .agent_lightning_library import AgentLightningLibrary
    AGENT_LIGHTNING_AVAILABLE = True
    print("✅ Agent Lightning library: Available")
except ImportError:
    AGENT_LIGHTNING_AVAILABLE = False
    from .agent_lightning_mcp_adapter import AgentLightningMCPAdapter
    AgentLightningMCPAdapter = None
    print("⚠️  Agent Lightning library not available. Install with: pip install agentlightning")
