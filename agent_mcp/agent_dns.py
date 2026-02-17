"""
Agent DNS - Scalable Agent Discovery System

Inspired by:
- DNS (hierarchical, distributed, caching)
- Kubernetes service discovery (labels, selectors)
- Social handles (@username)
- Phone numbers (E.164 global standard)

Goal: 1-line discovery for 1B+ agents
"""

import hashlib
import asyncio
import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AgentScope(Enum):
    """Agent scope/namespace - like domain TLDs"""
    GLOBAL = "global"           # @ai-researcher.agent
    PUBLIC = "public"           # @myagent.mcp
    PRIVATE = "private"         # @myagent.corp (internal network)
    PERSONAL = "personal"       # @myagent.local


@dataclass
class AgentHandle:
    """
    Agent handle - like an email address or social handle
    
    Examples:
        @claude.code-assistant.agent    (global, AI-friendly)
        @researcher@bio-ai.mcp         (public with org)
        @jane@corp                     (private/corporate)
        @gpt4@local                    (personal/local)
    """
    name: str
    scope: AgentScope = AgentScope.GLOBAL
    org: Optional[str] = None
    service: Optional[str] = None  # e.g., "claude", "gpt", "gemini"
    
    def __str__(self):
        if self.org:
            return f"@{self.name}@{self.org}.{self.service or self.scope.value}"
        return f"@{self.name}.{self.service or self.scope.value}"
    
    @classmethod
    def parse(cls, handle: str) -> "AgentHandle":
        """Parse a handle string into components"""
        # Remove @ prefix
        handle = handle.lstrip("@")
        
        parts = handle.split("@")
        if len(parts) == 2:
            name, rest = parts
            org_parts = rest.rsplit(".", 1)
            org = org_parts[0] if len(org_parts) > 1 else None
            service = org_parts[-1] if org_parts else None
            scope = AgentScope(service) if service in [s.value for s in AgentScope] else AgentScope.PUBLIC
        else:
            name = parts[0]
            org = None
            service = None
            scope = AgentScope.GLOBAL
        
        return cls(name=name, scope=scope, org=org, service=service)
    
    @property
    def flat_id(self) -> str:
        """Unique flat ID for hashing/consistency"""
        return hashlib.sha256(str(self).encode()).hexdigest()[:16]


@dataclass
class AgentEndpoint:
    """Agent endpoint - how to connect to an agent"""
    transport: str  # "http", "websocket", "mcp", "a2a"
    host: str
    port: int = 443
    path: str = ""
    token: Optional[str] = None
    
    def to_url(self) -> str:
        """Convert to connectable URL"""
        if self.transport == "http":
            return f"http://{self.host}:{self.port}{self.path}"
        elif self.transport == "https":
            return f"https://{self.host}:{self.port}{self.path}"
        elif self.transport == "websocket":
            return f"ws://{self.host}:{self.port}{self.path}"
        elif self.transport == "wss":
            return f"wss://{self.host}:{self.port}{self.path}"
        return f"{self.transport}://{self.host}:{self.port}{self.path}"


@dataclass
class AgentCapabilities:
    """What an agent can do - for discovery"""
    tags: List[str] = field(default_factory=list)  # ["code-review", "text-gen", "vision"]
    languages: List[str] = field(default_factory=list)  # ["python", "javascript"]
    frameworks: List[str] = field(default_factory=list)  # ["langchain", "autogen"]
    max_concurrent: int = 1
    supports_streaming: bool = False
    supports_tools: bool = True
    
    def matches(self, query: str) -> bool:
        """Check if capabilities match a query"""
        query_lower = query.lower()
        all_items = self.tags + self.languages + self.frameworks
        return any(
            query_lower in item.lower()
            for item in all_items
        )


@dataclass
class AgentRecord:
    """Complete agent record - like a DNS record"""
    handle: AgentHandle
    endpoint: AgentEndpoint
    capabilities: AgentCapabilities
    description: str = ""
    version: str = "1.0"
    owner: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl: int = 3600  # Cache TTL in seconds
    
    def to_dns_like(self) -> Dict[str, Any]:
        """Convert to DNS-like record format"""
        return {
            "type": "AGENT",
            "name": str(self.handle),
            "target": self.endpoint.to_url(),
            "capabilities": self.capabilities.tags,
            "ttl": self.ttl,
            "data": {
                "description": self.description,
                "version": self.version,
                "owner": self.owner,
                "frameworks": self.capabilities.frameworks,
                "languages": self.capabilities.languages,
            }
        }


class AgentResolver:
    """
    1-line agent discovery - like DNS for AI agents
    
    Usage:
        resolver = AgentResolver()
        
        # 1-line discovery by handle
        agent = await resolver.resolve("@claude.code-assistant")
        
        # 1-line search by capability
        agents = await resolver.find("code-review")
        
        # 1-line connect
        await resolver.connect("@researcher@bio-ai")
    """
    
    def __init__(
        self,
        registry_url: str = "https://registry.agentmcp.com",
        cache_ttl: int = 300,
        local_cache: bool = True
    ):
        self.registry_url = registry_url
        self.cache_ttl = cache_ttl
        self.local_cache = local_cache
        
        # Local cache (L1) - like DNS resolver cache
        self._cache: Dict[str, AgentRecord] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Handle -> Canonical URL mapping
        self._handle_to_url: Dict[str, str] = {}
        
        # For testing: mock registry
        self._mock_mode = False
        self._mock_agents: Dict[str, AgentRecord] = {}
    
    def enable_mock(self):
        """Enable mock mode for testing"""
        self._mock_mode = True
    
    def register_mock(self, record: AgentRecord):
        """Register a mock agent"""
        self._mock_agents[str(record.handle)] = record
        self._handle_to_url[str(record.handle)] = record.endpoint.to_url()
    
    async def resolve(self, handle: str) -> Optional[AgentRecord]:
        """
        Resolve an agent by handle - THE 1-LINE DISCOVERY
        
        Usage:
            agent = await resolver.resolve("@claude.code-assistant")
            agent = await resolver.resolve("@researcher@bio-ai.mcp")
        
        Args:
            handle: Agent handle (e.g., "@claude.code-assistant.agent")
        
        Returns:
            AgentRecord or None if not found
        """
        # Normalize handle
        handle = handle.lstrip("@")
        
        # Check cache first (L1 cache - like DNS resolver)
        if handle in self._cache:
            if self._is_cache_valid(handle):
                logger.debug(f"Cache hit for {handle}")
                return self._cache[handle]
            else:
                # Cache expired
                del self._cache[handle]
        
        # Check local registry - try multiple formats
        full_handle = f"@{handle}" if not handle.startswith("@") else handle
        for key in [full_handle, handle, handle.replace(".agent", ""), handle.replace(".global", "")]:
            if key in self._mock_agents:
                return self._mock_agents[key]
            # Also try without @
            for k, v in self._mock_agents.items():
                if handle in k or k in handle:
                    return v
        
        # Query registry (L2 - like DNS root server)
        try:
            record = await self._query_registry(handle)
            if record:
                self._cache[handle] = record
                self._cache_timestamps[handle] = asyncio.get_event_loop().time()
            return record
        except Exception as e:
            logger.error(f"Failed to resolve {handle}: {e}")
            return None
    
    async def find(
        self,
        query: str,
        limit: int = 10,
        scope: AgentScope = AgentScope.GLOBAL
    ) -> List[AgentRecord]:
        """
        Find agents by capability/query - SEARCH DISCOVERY
        
        Usage:
            agents = await resolver.find("code-review")
            agents = await resolver.find("python langchain")
            agents = await resolver.find("image generation")
        
        Like a search engine but for agents!
        
        Args:
            query: Search query (capability, tag, or description)
            limit: Maximum results to return
            scope: Scope to search in
        
        Returns:
            List of matching AgentRecords
        """
        results = []
        
        # Search local cache/registry
        all_agents = list(self._mock_agents.values()) if self._mock_mode else []
        
        # Score and filter
        for agent in all_agents:
            if agent.capabilities.matches(query):
                results.append(agent)
        
        # Sort by relevance (simple keyword matching for now)
        results.sort(
            key=lambda a: self._score_match(a, query),
            reverse=True
        )
        
        return results[:limit]
    
    async def connect(self, handle: str) -> str:
        """
        Connect to an agent - returns connection URL
        
        Usage:
            url = await resolver.connect("@claude.code-assistant")
            # Returns: "https://claude.agentmcp.com/mcp"
        
        Args:
            handle: Agent handle
        
        Returns:
            Connection URL
        """
        agent = await self.resolve(handle)
        if not agent:
            raise ValueError(f"Agent not found: {handle}")
        
        return agent.endpoint.to_url()
    
    async def discover_neighbors(
        self,
        handle: str,
        same_org: bool = True,
        same_capability: bool = True,
        limit: int = 5
    ) -> List[AgentRecord]:
        """
        Discover related agents - like "nearby" in a network
        
        Usage:
            neighbors = await resolver.discover_neighbors("@claude.code-assistant")
            # Returns agents from same org, with similar capabilities
        """
        agent = await self.resolve(handle)
        if not agent:
            return []
        
        results = []
        
        for other in self._mock_agents.values():
            if other.handle.name == agent.handle.name:
                continue
            
            # Same org?
            if same_org and agent.handle.org == other.handle.org:
                results.append(other)
                continue
            
            # Similar capabilities?
            if same_capability:
                common_tags = set(agent.capabilities.tags) & set(other.capabilities.tags)
                if common_tags:
                    results.append(other)
        
        return results[:limit]
    
    async def broadcast_discover(
        self,
        capabilities: List[str],
        timeout: float = 5.0
    ) -> List[AgentRecord]:
        """
        Broadcast discovery - like mDNS/Bonjour for local networks
        
        Usage:
            agents = await resolver.broadcast_discover(
                ["code-review", "python"],
                timeout=3.0
            )
        """
        # In real implementation, this would broadcast to local network
        # For now, search registry
        results = []
        
        for cap in capabilities:
            matches = await self.find(cap, limit=10)
            results.extend(matches)
        
        # Deduplicate
        seen = set()
        unique = []
        for a in results:
            if a.handle.flat_id not in seen:
                seen.add(a.handle.flat_id)
                unique.append(a)
        
        return unique[:10]
    
    # --- Internal methods ---
    
    def _is_cache_valid(self, handle: str) -> bool:
        """Check if cache entry is still valid"""
        if handle not in self._cache_timestamps:
            return False
        age = asyncio.get_event_loop().time() - self._cache_timestamps[handle]
        return age < self.cache_ttl
    
    async def _query_registry(self, handle: str) -> Optional[AgentRecord]:
        """Query the registry for an agent"""
        # Parse handle
        parsed = AgentHandle.parse(handle)
        
        # Build query URL
        url = f"{self.registry_url}/resolve/{parsed.flat_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._parse_record(data)
            except Exception as e:
                logger.debug(f"Registry query failed: {e}")
        
        return None
    
    def _parse_record(self, data: Dict[str, Any]) -> AgentRecord:
        """Parse registry response into AgentRecord"""
        return AgentRecord(
            handle=AgentHandle.parse(data.get("name", "")),
            endpoint=AgentEndpoint(
                transport=data.get("transport", "https"),
                host=data.get("host", ""),
                port=data.get("port", 443),
                path=data.get("path", "")
            ),
            capabilities=AgentCapabilities(
                tags=data.get("capabilities", []),
                languages=data.get("languages", []),
                frameworks=data.get("frameworks", [])
            ),
            description=data.get("description", ""),
            version=data.get("version", "1.0")
        )
    
    def _score_match(self, agent: AgentRecord, query: str) -> float:
        """Score how well an agent matches a query"""
        query_parts = query.lower().split()
        score = 0.0
        
        for part in query_parts:
            # Tags match (highest weight)
            if any(part in tag.lower() for tag in agent.capabilities.tags):
                score += 10.0
            # Languages match
            if any(part in lang.lower() for lang in agent.capabilities.languages):
                score += 5.0
            # Frameworks match
            if any(part in fw.lower() for fw in agent.capabilities.frameworks):
                score += 3.0
            # Description match
            if part in agent.description.lower():
                score += 1.0
        
        return score


# --- Convenience functions for 1-line usage ---

_global_resolver: Optional[AgentResolver] = None

def get_resolver() -> AgentResolver:
    """Get global resolver instance"""
    global _global_resolver
    if _global_resolver is None:
        _global_resolver = AgentResolver()
    return _global_resolver

async def resolve_agent(handle: str) -> Optional[AgentRecord]:
    """1-line agent resolution"""
    return await get_resolver().resolve(handle)

async def find_agents(query: str, limit: int = 10) -> List[AgentRecord]:
    """1-line agent search"""
    return await get_resolver().find(query, limit=limit)

async def connect_to_agent(handle: str) -> str:
    """1-line agent connection"""
    return await get_resolver().connect(handle)


# --- Demo/Testing ---

async def demo():
    """Demo the agent discovery system"""
    resolver = AgentResolver()
    resolver.enable_mock()
    
    # Register some mock agents
    resolver.register_mock(AgentRecord(
        handle=AgentHandle.parse("@claude.code-assistant.agent"),
        endpoint=AgentEndpoint(transport="https", host="claude.agentmcp.com", port=443, path="/mcp"),
        capabilities=AgentCapabilities(
            tags=["code-review", "programming", "analysis"],
            languages=["python", "javascript", "go"],
            frameworks=["claude", "anthropic"],
            supports_tools=True
        ),
        description="AI coding assistant",
        owner="Anthropic"
    ))
    
    resolver.register_mock(AgentRecord(
        handle=AgentHandle.parse("@gpt4.developer.mcp"),
        endpoint=AgentEndpoint(transport="https", host="openai.agentmcp.com", port=443, path="/v1"),
        capabilities=AgentCapabilities(
            tags=["text-generation", "conversation", "reasoning"],
            languages=["python"],
            frameworks=["openai"],
            supports_tools=True
        ),
        description="OpenAI GPT-4 assistant"
    ))
    
    resolver.register_mock(AgentRecord(
        handle=AgentHandle.parse("@researcher@bio-ai.mcp"),
        endpoint=AgentEndpoint(transport="https", host="bio-ai.research.org", port=443, path="/agent"),
        capabilities=AgentCapabilities(
            tags=["research", "bioinformatics", "analysis"],
            languages=["python", "r"],
            frameworks=["langchain", "autogen"],
            supports_tools=True
        ),
        description="Bioinformatics research agent"
    ))
    
    print("=" * 60)
    print("AGENT DNS - 1-LINE DISCOVERY DEMO")
    print("=" * 60)
    
    # 1-line resolve
    print("\n1. RESOLVE by handle:")
    agent = await resolver.resolve("@claude.code-assistant.agent")
    if agent:
        print(f"   @{agent.handle.name} -> {agent.endpoint.to_url()}")
        print(f"   Capabilities: {agent.capabilities.tags}")
    
    # 1-line find
    print("\n2. FIND by capability:")
    agents = await resolver.find("code-review", limit=5)
    for a in agents:
        print(f"   - {a.handle}: {a.description}")
    
    # 1-line find more
    print("\n3. FIND research agents:")
    agents = await resolver.find("research bio", limit=5)
    for a in agents:
        print(f"   - {a.handle}: {a.description}")
    
    # 1-line connect
    print("\n4. CONNECT to agent:")
    url = await resolver.connect("@claude.code-assistant.agent")
    print(f"   Connection URL: {url}")
    
    # Discovery
    print("\n5. DISCOVER neighbors:")
    neighbors = await resolver.discover_neighbors("@researcher@bio-ai.mcp")
    for n in neighbors:
        print(f"   - {n.handle}: {n.description}")
    
    print("\n" + "=" * 60)
    print("All in 1 line! 🎉")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
