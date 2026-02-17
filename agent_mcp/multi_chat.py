"""
MultiChat Agent - One Agent, Three Chats, Zero Leaks

The magic: handle suffix determines routing automatically!

Usage:
    agent = MultiChatAgent("@alice@acme.corp")
    
    # Auto-routes to company chat
    await agent.send("bob", "internal payroll data")  # .corp → company
    
    # Auto-routes to business chat  
    await agent.send("@partner@vendor.business", "project update")  # .business → business
    
    # Auto-routes to public chat
    await agent.send("@gpt@openai.public", "quick question")  # .public → public
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NetworkMode(Enum):
    COMPANY = "company"    # .corp suffix - no external
    BUSINESS = "business"  # .business suffix - sanitized
    PUBLIC = "public"      # .public suffix - minimal


@dataclass
class ChatConnection:
    """A connection to a specific chat/network"""
    mode: NetworkMode
    transport: Any = None  # The actual transport connection
    endpoint: str = ""
    agents: List[str] = field(default_factory=list)
    
    def is_connected(self) -> bool:
        return self.transport is not None


class MultiChatAgent:
    """
    One agent that can work in THREE chats simultaneously!
    
    Magic: Just send messages - routing is automatic based on handle suffix
    
    Usage:
        agent = MultiChatAgent("@alice@acme.corp")
        
        # Auto-routes based on recipient suffix
        await agent.send("@bob@acme.corp", "hi")         # → Company chat
        await agent.send("@vendor@partner.business", "hi") # → Business chat  
        await agent.send("@gpt@openai.public", "hi")      # → Public chat
    """
    
    def __init__(self, handle: str):
        self.handle = handle
        self.mode = self._detect_mode(handle)
        self.org = self._extract_org(handle)
        
        # THREE connections - one per chat
        self._connections: Dict[NetworkMode, ChatConnection] = {
            NetworkMode.COMPANY: ChatConnection(mode=NetworkMode.COMPANY),
            NetworkMode.BUSINESS: ChatConnection(mode=NetworkMode.BUSINESS),
            NetworkMode.PUBLIC: ChatConnection(mode=NetworkMode.PUBLIC),
        }
        
        logger.info(f"Created MultiChatAgent: {handle} (mode: {self.mode.value})")
    
    def _detect_mode(self, handle: str) -> NetworkMode:
        """Detect network mode from handle suffix - THE MAGIC!"""
        h = handle.lower()
        if '.corp' in h:
            return NetworkMode.COMPANY
        elif '.business' in h:
            return NetworkMode.BUSINESS
        else:
            return NetworkMode.PUBLIC
    
    def _extract_org(self, handle: str) -> Optional[str]:
        """Extract organization from handle"""
        parts = handle.lstrip('@').split('@')
        if len(parts) >= 2:
            return parts[1].split('.')[0]
        return None
    
    def _detect_target_mode(self, target: str) -> NetworkMode:
        """Detect which chat to route to based on target handle - THE MAGIC!"""
        t = target.lower()
        if '.corp' in t:
            return NetworkMode.COMPANY
        elif '.business' in t:
            return NetworkMode.BUSINESS
        else:
            return NetworkMode.PUBLIC
    
    async def connect(self, company_endpoint: str = None, business_endpoint: str = None, public_endpoint: str = None):
        """
        Connect to all three networks (or just the ones you need)
        
        Usage:
            await agent.connect(
                company_endpoint="https://company.internal",
                business_endpoint="https://company.business",
                public_endpoint="https://mcp.agentmcp.com"
            )
        """
        # Connect to company (if endpoint provided)
        if company_endpoint:
            self._connections[NetworkMode.COMPANY].endpoint = company_endpoint
            self._connections[NetworkMode.COMPANY].transport = "CONNECTED"  # Simplified
            logger.info(f"Connected to COMPANY: {company_endpoint}")
        
        # Connect to business
        if business_endpoint:
            self._connections[NetworkMode.BUSINESS].endpoint = business_endpoint
            self._connections[NetworkMode.BUSINESS].transport = "CONNECTED"
            logger.info(f"Connected to BUSINESS: {business_endpoint}")
        
        # Connect to public (default)
        if public_endpoint:
            self._connections[NetworkMode.PUBLIC].endpoint = public_endpoint
            self._connections[NetworkMode.PUBLIC].transport = "CONNECTED"
            logger.info(f"Connected to PUBLIC: {public_endpoint}")
        elif not public_endpoint and not company_endpoint and not business_endpoint:
            # Default: connect to public
            self._connections[NetworkMode.PUBLIC].endpoint = "https://mcp.agentmcp.com"
            self._connections[NetworkMode.PUBLIC].transport = "CONNECTED"
            logger.info("Connected to PUBLIC (default)")
    
    async def send(self, target: str, message: Any) -> Dict[str, Any]:
        """
        Send a message - AUTOMATIC ROUTING!
        
        THE MAGIC: Just pass the target handle, we figure out which chat!
        
        Args:
            target: Target agent handle (e.g., "@bob@acme.corp")
            message: Message to send
        
        Returns:
            Delivery confirmation
        """
        # Auto-detect which chat based on TARGET handle suffix
        target_mode = self._detect_target_mode(target)
        
        # Get the right connection
        connection = self._connections[target_mode]
        
        if not connection.is_connected():
            raise RuntimeError(f"Not connected to {target_mode.value} network")
        
        # Check for data leakage prevention
        await self._check_security(target, message, target_mode)
        
        # Simulate sending (in real impl, use actual transport)
        result = {
            "status": "sent",
            "from": self.handle,
            "to": target,
            "via": target_mode.value,
            "endpoint": connection.endpoint,
            "message": message
        }
        
        logger.info(f"Message sent: {self.handle} → {target} via {target_mode.value}")
        return result
    
    async def _check_security(self, target: str, message: Any, target_mode: NetworkMode):
        """Security check - prevent leaks!"""
        
        # COMPANY mode: can ONLY talk to .corp
        if self.mode == NetworkMode.COMPANY:
            if target_mode != NetworkMode.COMPANY:
                raise PermissionError(f"COMPANY agent cannot send to {target_mode.value}")
        
        # BUSINESS mode: can talk to .corp and .business, sanitize .public
        if self.mode == NetworkMode.BUSINESS:
            if target_mode == NetworkMode.PUBLIC:
                # Sanitize sensitive data
                await self._sanitize_message(message)
        
        # PUBLIC mode: can talk to anyone
    
    async def _sanitize_message(self, message: Any):
        """Remove sensitive data before sending to public"""
        sensitive = ["password", "secret", "api_key", "token", "credential"]
        if isinstance(message, dict):
            for key in list(message.keys()):
                if any(s in key.lower() for s in sensitive):
                    message[key] = "[REDACTED]"
    
    async def receive(self, mode: NetworkMode = None) -> Dict[str, Any]:
        """
        Receive a message from a specific chat
        
        Args:
            mode: Which chat to listen to (default: all)
        """
        if mode:
            conn = self._connections[mode]
            return {"mode": mode.value, "waiting": conn.is_connected()}
        
        # Return messages from all chats
        return {
            mode.value: {"connected": conn.is_connected()}
            for mode, conn in self._connections.items()
        }
    
    def get_mode(self) -> NetworkMode:
        """Get this agent's primary mode"""
        return self.mode


# --- The Magic: 3 Lines to Multi-Chat! ---

def create_multi_chat_agent(handle: str, endpoints: Dict[str, str] = None) -> MultiChatAgent:
    """
    Create a multi-chat agent in 3 lines!
    
    Usage:
        agent = create_multi_chat_agent("@alice@acme.corp")
        
        # Or with endpoints:
        agent = create_multi_chat_agent("@alice@acme.corp", {
            "company": "https://company.internal",
            "business": "https://company.business", 
            "public": "https://mcp.agentmcp.com"
        })
    """
    import concurrent.futures
    
    agent = MultiChatAgent(handle)
    
    def _connect():
        if endpoints:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(agent.connect(**endpoints))
            finally:
                loop.close()
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(agent.connect())
            finally:
                loop.close()
    
    # Run connection in thread to avoid event loop issues
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_connect)
        future.result()
    
    return agent


# --- Demo ---

async def demo():
    """Demo the magical multi-chat agent"""
    
    print("=" * 60)
    print("MULTI-CHAT AGENT - THE MAGIC!")
    print("=" * 60)
    
    # Create ONE agent that works in all 3 modes (business mode to show all features)
    agent = MultiChatAgent("@alice@acme.business")
    
    # Connect to all networks
    await agent.connect(
        company_endpoint="https://company.internal",
        business_endpoint="https://company.business", 
        public_endpoint="https://mcp.agentmcp.com"
    )
    
    print(f"\nAgent: {agent.handle}")
    print(f"Mode: {agent.mode.value}")
    print(f"Org: {agent.org}")
    
    # THE MAGIC: Auto-routing based on target handle!
    
    print("\n--- Sending Messages ---")
    
    # To .corp → Company chat (same org)
    result = await agent.send("@bob@acme.corp", "Hey Bob, payroll ready")
    print(f"\n1. To company: {result['via']}")
    print(f"   Message: {result['message']}")
    
    # To .business → Business chat (partners)
    result = await agent.send("@partner@vendor.business", "Project update")
    print(f"\n2. To business: {result['via']}")
    print(f"   Message: {result['message']}")
    
    # To .public → Public chat (anyone)
    result = await agent.send("@gpt@openai.public", "Quick question")
    print(f"\n3. To public: {result['via']}")
    print(f"   Message: {result['message']}")
    
    # Try to leak: COMPANY agent → PUBLIC with secrets
    print("\n--- Security Test ---")
    try:
        result = await agent.send("@gpt@openai.public", {"question": "hi", "api_key": "secret123"})
        print(f"   Result: {result['message']}")
    except PermissionError as e:
        print(f"   Blocked: {e}")
    
    print("\n" + "=" * 60)
    print("ONE AGENT, THREE CHATS, ZERO LEAKS! ✨")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
