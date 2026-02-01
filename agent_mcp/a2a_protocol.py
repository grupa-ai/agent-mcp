"""
A2A Protocol Integration for AgentMCP
Google's Agent-to-Agent protocol implementation

This module implements Google's A2A protocol for agent interoperability.
A2A complements MCP by focusing on agent-to-agent communication
while MCP handles agent-to-tool communication.
"""

import json
import uuid
import hashlib
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

@dataclass
class A2AAgentCard:
    """Agent Card - A2A standard for agent discovery"""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    protocols: List[str]  # ["A2A", "MCP", "REST"]
    endpoint: str
    version: str = "1.0"
    owner_did: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class A2AMessage:
    """A2A Message format"""
    id: str
    sender_id: str
    receiver_id: str
    message_type: str  # "request", "response", "event", "handshake"
    content: Dict[str, Any]
    timestamp: str
    correlation_id: Optional[str] = None
    priority: int = 5  # 1-10, lower = higher priority
    expires_at: Optional[str] = None
    signature: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

class A2AClient:
    """A2A Protocol Client for communicating with other A2A-enabled agents"""
    
    def __init__(self, agent_id: str, private_key: str = None):
        self.agent_id = agent_id
        self.private_key = private_key
        self.session = None
        self.known_agents = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def discover_agent(self, endpoint: str) -> Optional[A2AAgentCard]:
        """Discover an agent's capabilities using A2A protocol"""
        try:
            async with self.session.get(f"{endpoint}/.well-known/agent.json") as response:
                if response.status == 200:
                    data = await response.json()
                    return A2AAgentCard(**data)
        except Exception as e:
            logger.error(f"Failed to discover agent at {endpoint}: {e}")
        return None
    
    async def register_with_agent(self, agent_card: A2AAgentCard, target_endpoint: str) -> Dict[str, Any]:
        """Register this agent with another A2A agent"""
        handshake_msg = A2AMessage(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            receiver_id=agent_card.agent_id,
            message_type="handshake",
            content={
                "agent_card": asdict(agent_card),
                "intention": "register"
            }
        )
        
        return await self._send_message(target_endpoint, handshake_msg)
    
    async def send_message(self, receiver_id: str, endpoint: str, content: Dict[str, Any], 
                        message_type: str = "request", correlation_id: str = None) -> Dict[str, Any]:
        """Send a message to another A2A agent"""
        message = A2AMessage(
            id=str(uuid.uuid4()),
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            correlation_id=correlation_id
        )
        
        return await self._send_message(endpoint, message)
    
    async def _send_message(self, endpoint: str, message: A2AMessage) -> Dict[str, Any]:
        """Send message via HTTP POST"""
        try:
            payload = asdict(message)
            
            # Sign message if private key available
            if self.private_key:
                payload["signature"] = self._sign_message(payload)
            
            async with self.session.post(
                f"{endpoint}/a2a/message",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to send A2A message: {e}")
            return {"status": "error", "message": str(e)}
    
    def _sign_message(self, message_data: Dict[str, Any]) -> str:
        """Sign message with private key (simplified)"""
        # In production, use proper cryptographic signing
        message_str = json.dumps(message_data, sort_keys=True)
        return hashlib.sha256((message_str + self.private_key).encode()).hexdigest()

class A2AServer:
    """A2A Protocol Server integration for AgentMCP"""
    
    def __init__(self, mcp_agent, host: str = "0.0.0.0", port: int = 8081):
        self.mcp_agent = mcp_agent
        self.host = host
        self.port = port
        self.registered_agents = {}
        self.app = None
        
    def create_agent_card(self) -> A2AAgentCard:
        """Create Agent Card for this agent"""
        return A2AAgentCard(
            agent_id=self.mcp_agent.name,
            name=self.mcp_agent.name,
            description=f"MCP Agent: {getattr(self.mcp_agent, 'system_message', 'No description')}",
            capabilities=getattr(self.mcp_agent, 'capabilities', []),
            protocols=["MCP", "A2A"],
            endpoint=f"http://{self.host}:{self.port}",
            metadata={"mcp_version": getattr(self.mcp_agent, 'mcp_version', '0.1.0')}
        )
    
    def setup_fastapi_routes(self, app):
        """Setup A2A routes on existing FastAPI app"""
        self.app = app
        
        @app.get("/.well-known/agent.json")
        async def get_agent_card():
            return asdict(self.create_agent_card())
        
        @app.post("/a2a/message")
        async def handle_a2a_message(message: dict):
            return await self._handle_incoming_message(message)
        
        @app.get("/a2a/agents")
        async def list_agents():
            return {
                "agents": list(self.registered_agents.values()),
                "total": len(self.registered_agents)
            }
        
        @app.post("/a2a/register")
        async def register_agent(agent_info: dict):
            """Register another agent"""
            agent_card = A2AAgentCard(**agent_info)
            self.registered_agents[agent_card.agent_id] = asdict(agent_card)
            
            # Auto-register the agent as a tool in MCP
            if hasattr(self.mcp_agent, 'register_agent_as_tool'):
                await self._register_as_mcp_tool(agent_card)
            
            return {"status": "registered", "agent_id": agent_card.agent_id}
    
    async def _handle_incoming_message(self, message_data: dict) -> dict:
        """Handle incoming A2A message"""
        try:
            message = A2AMessage(**message_data)
            
            if message.message_type == "handshake":
                return await self._handle_handshake(message)
            elif message.message_type == "request":
                return await self._handle_request(message)
            else:
                return {"status": "error", "message": f"Unknown message type: {message.message_type}"}
                
        except Exception as e:
            logger.error(f"Error handling A2A message: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _handle_handshake(self, message: A2AMessage) -> dict:
        """Handle A2A handshake"""
        agent_info = message.content.get("agent_card")
        if agent_info:
            self.registered_agents[agent_info["agent_id"]] = agent_info
            logger.info(f"Registered A2A agent: {agent_info['agent_id']}")
            
            return {
                "status": "handshake_complete",
                "agent_id": self.mcp_agent.name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return {"status": "error", "message": "No agent card in handshake"}
    
    async def _handle_request(self, message: A2AMessage) -> dict:
        """Handle A2A request by routing through MCP"""
        try:
            # Convert A2A message to MCP format and handle
            content = message.content
            
            # Check if this is a tool call
            if "tool_name" in content:
                tool_name = content["tool_name"]
                tool_args = content.get("arguments", {})
                
                # Execute through MCP agent
                if hasattr(self.mcp_agent, 'execute_tool'):
                    result = await self.mcp_agent.execute_tool(tool_name, **tool_args)
                    return {
                        "status": "success",
                        "result": result,
                        "message_id": message.id,
                        "correlation_id": message.correlation_id
                    }
            
            # Handle as general message
            elif hasattr(self.mcp_agent, 'message_handler'):
                result = await self.mcp_agent.message_handler(content)
                return {
                    "status": "success", 
                    "result": result,
                    "message_id": message.id,
                    "correlation_id": message.correlation_id
                }
            
            else:
                return {"status": "error", "message": "No message handler available"}
                
        except Exception as e:
            logger.error(f"Error handling A2A request: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _register_as_mcp_tool(self, agent_card: A2AAgentCard):
        """Register A2A agent as MCP tool"""
        tool_name = f"a2a_{agent_card.agent_id}"
        tool_description = f"Communicate with A2A agent {agent_card.name}"
        
        async def a2a_tool_wrapper(**kwargs):
            """Wrapper to call A2A agent from MCP"""
            async with A2AClient(self.mcp_agent.name) as client:
                return await client.send_message(
                    receiver_id=agent_card.agent_id,
                    endpoint=agent_card.endpoint,
                    content=kwargs
                )
        
        # Register with MCP agent if available
        if hasattr(self.mcp_agent, 'register_mcp_tool'):
            self.mcp_agent.register_mcp_tool(
                lambda **kwargs: a2a_tool_wrapper(**kwargs)
            )

class A2AMCPBridge:
    """Bridge between A2A and MCP protocols"""
    
    def __init__(self, mcp_agent, private_key: str = None):
        self.mcp_agent = mcp_agent
        self.a2a_client = A2AClient(mcp_agent.name, private_key)
        self.a2a_server = A2AServer(mcp_agent)
    
    async def start_bridge(self, app):
        """Start the bridge with existing FastAPI app"""
        # Setup A2A server routes
        self.a2a_server.setup_fastapi_routes(app)
        
        # Discover and register with known A2A agents
        await self._discover_and_register_agents()
    
    async def _discover_and_register_agents(self):
        """Discover and auto-register with other A2A agents"""
        # This could read from a config file or environment variable
        known_endpoints = [
            "http://localhost:8082",  # Example other agent
            # Add more agent endpoints here
        ]
        
        async with self.a2a_client as client:
            for endpoint in known_endpoints:
                agent_card = await client.discover_agent(endpoint)
                if agent_card:
                    await client.register_with_agent(agent_card, endpoint)
                    logger.info(f"Registered with A2A agent: {agent_card.name}")

# Export for easy importing
__all__ = ['A2AAgentCard', 'A2AMessage', 'A2AClient', 'A2AServer', 'A2AMCPBridge']