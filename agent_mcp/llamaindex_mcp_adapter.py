"""
LlamaIndex MCP Adapter
Integration between LlamaIndex agents and Model Context Protocol

This adapter allows LlamaIndex agents to:
1. Expose their tools as MCP tools
2. Consume MCP tools from other agents
3. Participate in multi-agent networks
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
import logging

try:
    from llama_index.core.agent import Agent
    from llama_index.core.tools import BaseTool
    from llama_index.core.llms import LLM
    from llama_index.core.query_engine import QueryEngine
    from llama_index.core.indices import VectorStoreIndex
    from llama_index.core.readers import base as readers
    from llama_index.tools.mcp import McpToolSpec
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    Agent = None
    BaseTool = None
    LLM = None

from .mcp_transport import HTTPTransport

logger = logging.getLogger(__name__)

@dataclass
class LlamaIndexMCPConfig:
    """Configuration for LlamaIndex MCP integration"""
    agent_id: str
    name: str
    description: str
    server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app"
    auto_register_tools: bool = True
    expose_index_as_tool: bool = True
    index_query_mode: str = "default"  # "default", "tree", "sub_question"

class MCPLlamaIndexAgent:
    """LlamaIndex Agent with MCP capabilities"""
    
    def __init__(
        self,
        agent: Agent,
        config: LlamaIndexMCPConfig,
        transport: HTTPTransport = None
    ):
        if not LLAMA_INDEX_AVAILABLE:
            raise ImportError("LlamaIndex is not installed. Install with: pip install llama-index")
            
        self.llama_agent = agent
        self.config = config
        self.mcp_tools = {}
        self.transport = transport or HTTPTransport.from_url(config.server_url)
        self.mcp_id = config.agent_id
        self.mcp_version = "0.1.0"
        
        # Extract tools from LlamaIndex agent
        self._extract_tools_from_agent()
        
    def _extract_tools_from_agent(self):
        """Extract tools from LlamaIndex agent and register as MCP tools"""
        try:
            # Get tools from the agent if available
            if hasattr(self.llama_agent, 'tools') and self.llama_agent.tools:
                for tool in self.llama_agent.tools:
                    self._register_llama_tool_as_mcp(tool)
            
            # Get tools from agent's query engine
            if hasattr(self.llama_agent, 'query_engine') and self.llama_agent.query_engine:
                self._register_query_engine_as_tool()
                
        except Exception as e:
            logger.error(f"Error extracting tools from LlamaIndex agent: {e}")
    
    def _register_llama_tool_as_mcp(self, tool: BaseTool):
        """Register a LlamaIndex tool as MCP tool"""
        tool_name = tool.metadata.name
        tool_description = tool.metadata.description
        
        async def mcp_tool_wrapper(**kwargs):
            """Wrapper to call LlamaIndex tool through MCP"""
            try:
                # Convert args to the format LlamaIndex expects
                result = await tool.acall(**kwargs)
                return {
                    "status": "success",
                    "result": result,
                    "tool_name": tool_name
                }
            except Exception as e:
                logger.error(f"Error calling LlamaIndex tool {tool_name}: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "tool_name": tool_name
                }
        
        self.mcp_tools[tool_name] = {
            "name": tool_name,
            "description": tool_description,
            "parameters": self._extract_tool_parameters(tool),
            "function": mcp_tool_wrapper
        }
    
    def _register_query_engine_as_tool(self):
        """Register the agent's query engine as an MCP tool"""
        async def query_tool_wrapper(query: str, **kwargs) -> Dict[str, Any]:
            """Wrapper to query the agent's knowledge base"""
            try:
                response = await self.llama_agent.query_engine.aquery(query)
                return {
                    "status": "success",
                    "result": str(response),
                    "query": query,
                    "source_nodes": [
                        {"text": node.text, "score": node.score}
                        for node in getattr(response, 'source_nodes', [])
                    ]
                }
            except Exception as e:
                logger.error(f"Error querying LlamaIndex agent: {e}")
                return {
                    "status": "error", 
                    "message": str(e),
                    "query": query
                }
        
        self.mcp_tools["query_knowledge_base"] = {
            "name": "query_knowledge_base",
            "description": f"Query the knowledge base of {self.config.name}",
            "parameters": [
                {
                    "name": "query",
                    "description": "The query to search for",
                    "type": "string",
                    "required": True
                }
            ],
            "function": query_tool_wrapper
        }
    
    def _extract_tool_parameters(self, tool: BaseTool) -> List[Dict[str, Any]]:
        """Extract parameter information from LlamaIndex tool"""
        parameters = []
        
        if hasattr(tool.metadata, 'fn_schema') and tool.metadata.fn_schema:
            # Get parameters from function schema
            schema = tool.metadata.fn_schema
            if hasattr(schema, 'model_fields'):
                for field_name, field_info in schema.model_fields.items():
                    param = {
                        "name": field_name,
                        "description": field_info.description or f"Parameter {field_name}",
                        "type": "string",  # Default to string for compatibility
                        "required": field_info.default is None
                    }
                    
                    # Try to determine type
                    if hasattr(field_info, 'annotation'):
                        type_str = str(field_info.annotation)
                        if "int" in type_str.lower():
                            param["type"] = "number"
                        elif "bool" in type_str.lower():
                            param["type"] = "boolean"
                        elif "list" in type_str.lower():
                            param["type"] = "array"
                    
                    parameters.append(param)
        
        return parameters
    
    async def register_with_mcp_server(self) -> Dict[str, Any]:
        """Register this LlamaIndex agent with MCP server"""
        registration_data = {
            "agent_id": self.mcp_id,
            "info": {
                "name": self.config.name,
                "description": self.config.description,
                "framework": "LlamaIndex",
                "capabilities": list(self.mcp_tools.keys()),
                "version": self.mcp_version,
                "tools": [
                    {
                        "name": tool_info["name"],
                        "description": tool_info["description"],
                        "parameters": tool_info["parameters"]
                    }
                    for tool_info in self.mcp_tools.values()
                ]
            }
        }
        
        return await self.transport.register_agent(self)
    
    async def execute_mcp_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute an MCP tool (could be local or remote)"""
        if tool_name in self.mcp_tools:
            # Execute local tool
            tool_func = self.mcp_tools[tool_name]["function"]
            return await tool_func(**kwargs)
        else:
            # Try to execute remote tool via MCP transport
            try:
                message = {
                    "type": "tool_call",
                    "tool_name": tool_name,
                    "arguments": kwargs,
                    "sender": self.mcp_id
                }
                
                response = await self.transport.send_message("network", message)
                return response
            except Exception as e:
                logger.error(f"Error executing remote MCP tool {tool_name}: {e}")
                return {
                    "status": "error",
                    "message": str(e),
                    "tool_name": tool_name
                }
    
    async def query_with_context(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Query using LlamaIndex with additional MCP context"""
        try:
            # Add MCP context to the query if provided
            if context:
                # Create a contextual query string
                context_str = json.dumps(context, indent=2)
                enhanced_query = f"""
                Context: {context_str}
                
                Question: {query}
                """
            else:
                enhanced_query = query
            
            # Query using LlamaIndex
            response = await self.llama_agent.aquery(enhanced_query)
            
            return {
                "status": "success",
                "result": str(response),
                "query": query,
                "context_used": context is not None,
                "source_nodes": [
                    {"text": node.text, "score": node.score}
                    for node in getattr(response, 'source_nodes', [])
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in query_with_context: {e}")
            return {
                "status": "error",
                "message": str(e),
                "query": query
            }
    
    def get_mcp_tool_info(self) -> Dict[str, Any]:
        """Get information about all available MCP tools"""
        return {
            "agent_id": self.mcp_id,
            "framework": "LlamaIndex",
            "tools": [
                {
                    "name": tool_info["name"],
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
                for tool_info in self.mcp_tools.values()
            ]
        }

class LlamaIndexMCPBridge:
    """Bridge to connect LlamaIndex agents with MCP network"""
    
    def __init__(self, server_url: str = "https://mcp-server-ixlfhxquwq-ew.a.run.app"):
        self.server_url = server_url
        self.connected_agents = {}
        
    async def create_llama_mcp_agent(
        self,
        agent: Agent,
        agent_id: str,
        name: str = None,
        description: str = None
    ) -> MCPLlamaIndexAgent:
        """Create and register a LlamaIndex MCP agent"""
        
        config = LlamaIndexMCPConfig(
            agent_id=agent_id,
            name=name or agent_id,
            description=description or f"LlamaIndex agent {agent_id}",
            server_url=self.server_url
        )
        
        mcp_agent = MCPLlamaIndexAgent(agent, config)
        
        # Register with MCP server
        registration_result = await mcp_agent.register_with_mcp_server()
        
        if registration_result.get("status") == "registered":
            logger.info(f"LlamaIndex agent {agent_id} registered with MCP server")
            self.connected_agents[agent_id] = mcp_agent
        else:
            logger.error(f"Failed to register LlamaIndex agent {agent_id}: {registration_result}")
        
        return mcp_agent
    
    async def connect_mcp_tools_to_llama(
        self,
        agent: Agent,
        mcp_server_url: str = None
    ) -> List[BaseTool]:
        """Connect MCP tools to a LlamaIndex agent"""
        
        if not LLAMA_INDEX_AVAILABLE:
            raise ImportError("LlamaIndex is not installed")
            
        mcp_tools = []
        
        # Use McpToolSpec if available
        try:
            if McpToolSpec:
                mcp_spec = McpToolSpec(
                    mcp_server_url or self.server_url
                )
                mcp_tools = await mcp_spec.as_tool_list()
                logger.info(f"Loaded {len(mcp_tools)} MCP tools for LlamaIndex agent")
        except Exception as e:
            logger.warning(f"Could not use McpToolSpec: {e}")
            
            # Fallback: manually discover and create tools
            mcp_tools = await self._create_manual_mcp_tools(mcp_server_url or self.server_url)
        
        # Add tools to LlamaIndex agent
        if hasattr(agent, 'update_tool_mapping'):
            agent.update_tool_mapping(mcp_tools)
        elif hasattr(agent, 'tools'):
            agent.tools.extend(mcp_tools)
        
        return mcp_tools
    
    async def _create_manual_mcp_tools(self, server_url: str) -> List[BaseTool]:
        """Manually create MCP tools for LlamaIndex"""
        tools = []
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{server_url}/tools") as response:
                    if response.status == 200:
                        tools_data = await response.json()
                        
                        for tool_data in tools_data.get("tools", []):
                            # Create custom LlamaIndex tool
                            tool = self._create_llama_tool_from_mcp_data(tool_data, server_url)
                            tools.append(tool)
                            
        except Exception as e:
            logger.error(f"Error creating manual MCP tools: {e}")
        
        return tools
    
    def _create_llama_tool_from_mcp_data(self, tool_data: Dict[str, Any], server_url: str) -> BaseTool:
        """Create a LlamaIndex tool from MCP tool data"""
        
        class CustomMCPTool(BaseTool):
            def __init__(self, tool_data: Dict[str, Any], server_url: str):
                self._tool_data = tool_data
                self._server_url = server_url
                super().__init__(
                    name=tool_data["name"],
                    description=tool_data["description"]
                )
            
            async def acall(self, **kwargs):
                """Call the MCP tool"""
                import aiohttp
                
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "tool_name": self._tool_data["name"],
                        "arguments": kwargs
                    }
                    
                    async with session.post(
                        f"{self._server_url}/execute_tool",
                        json=payload
                    ) as response:
                        result = await response.json()
                        return result.get("result", str(result))
        
        return CustomMCPTool(tool_data, server_url)

# Export classes for easy importing
__all__ = [
    'LlamaIndexMCPConfig',
    'MCPLlamaIndexAgent', 
    'LlamaIndexMCPBridge'
]