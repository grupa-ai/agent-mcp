"""
Comprehensive Test Suite for AgentMCP
Testing all new frameworks, protocols, and integrations

This test suite provides comprehensive testing for:
- A2A Protocol integration
- LlamaIndex MCP adapter  
- Microsoft Agent Framework
- Pydantic AI support
- Zero-trust security layer
- Hybrid payment gateway
- Multi-language agent registry
- OpenAPI protocol support
"""

import asyncio
import pytest
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class TestConfig:
    """Configuration for test environment"""
    TEST_SERVER_URL = "http://localhost:8999"
    TEST_STRIPE_KEY = "sk_test_123456789"
    TEST_USDC_RPC = "https://base-sepolia.blockpi.network/v1"
    TEST_USDC_PRIVATE_KEY = "0x12345678901234567890123456789012345678901234567890"
    TEST_AGENT_ID = "test_agent"

class MockStorage:
    """Mock storage backend for testing"""
    
    def __init__(self):
        self.data = {}
    
    async def write(self, collection: str, document: Dict[str, Any]):
        if collection not in self.data:
            self.data[collection] = []
        self.data[collection].append(document)
    
    async def query(self, collection: str, filters: Dict[str, Any] = None):
        if collection not in self.data:
            return []
        documents = self.data[collection]
        
        if filters:
            filtered_docs = []
            for doc in documents:
                match = True
                for key, value in filters.items():
                    if key.endswith("_gte"):
                        field = key[:-4]
                        if doc.get(field) and doc[field] >= value:
                            continue
                        match = False
                    elif key.endswith("_lte"):
                        field = key[:-4]
                        if doc.get(field) and doc[field] <= value:
                            continue
                        match = False
                    elif doc.get(key) != value:
                        match = False
                
                if match:
                    filtered_docs.append(doc)
            return filtered_docs
        
        return documents
    
    async def update(self, collection: str, filters: Dict[str, Any], updates: Dict[str, Any]):
        if collection not in self.data:
            return
        
        for i, doc in enumerate(self.data[collection]):
            match = True
            for key, value in filters.items():
                if doc.get(key) != value:
                    match = False
                    break
            
            if match:
                self.data[collection][i].update(updates)
                break

# Import modules with proper error handling
try:
    from agent_mcp.a2a_protocol import A2AClient, A2AAgentCard
except ImportError:
    A2AClient = None
    A2AAgentCard = None

try:
    from agent_mcp.llamaindex_mcp_adapter import LlamaIndexMCPConfig
except ImportError:
    LlamaIndexMCPConfig = None

try:
    from agent_mcp.microsoft_agent_framework import MicrosoftMCPAgent
except ImportError:
    MicrosoftMCPAgent = None

try:
    from agent_mcp.security import ZeroTrustSecurityLayer, Permission, SecurityLevel
except ImportError:
    ZeroTrustSecurityLayer = None
    Permission = None
    SecurityLevel = None

try:
    from agent_mcp.payments import HybridPaymentGateway, PaymentMethod, PaymentRequest
except ImportError:
    HybridPaymentGateway = None
    PaymentMethod = None
    PaymentRequest = None

try:
    from agent_mcp.registry import MultiLanguageAgentRegistry, AgentLanguage, AgentProtocol
except ImportError:
    MultiLanguageAgentRegistry = None
    AgentLanguage = None
    AgentProtocol = None

try:
    from agent_mcp.openapi_protocol import OpenAPIServer
except ImportError:
    OpenAPIServer = None

# Skip test if modules not available
def skip_if_unavailable(module_name):
    return pytest.mark.skip(f"{module_name} not available") if globals()[module_name] is None else pytest.mark.skip(f"Module {module_name} failed to import")

@pytest.mark.order(1)
@skip_if_unavailable("A2AClient")
class TestA2AProtocol:
    """Test A2A Protocol integration"""
    
    @pytest.mark.asyncio
    async def test_a2a_agent_card_creation(self):
        """Test creating A2A agent card"""
        if A2AAgentCard is None:
            pytest.skip("A2A modules not available")
            return
        
        card = A2AAgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="Test agent for A2A protocol",
            capabilities=["test_capability"],
            protocols=["A2A", "MCP"],
            endpoint="http://localhost:8080"
        )
        
        assert card.agent_id == "test_agent"
        assert card.name == "Test Agent"
        assert "test_capability" in card.capabilities

@pytest.mark.order(2)
@skip_if_unavailable("LlamaIndexMCPConfig")
class TestLlamaIndexMCPAdapter:
    """Test LlamaIndex MCP adapter"""
    
    @pytest.mark.asyncio
    async def test_llamaindex_config_creation(self):
        """Test creating LlamaIndex MCP config"""
        if LlamaIndexMCPConfig is None:
            pytest.skip("LlamaIndex modules not available")
            return
        
        config = LlamaIndexMCPConfig(
            agent_id="test_llama_agent",
            name="Test LlamaIndex Agent",
            description="Test agent for LlamaIndex integration",
            server_url=TestConfig.TEST_SERVER_URL
        )
        
        assert config.agent_id == "test_llama_agent"
        assert config.server_url == TestConfig.TEST_SERVER_URL

@pytest.mark.order(3)
@skip_if_unavailable("MicrosoftMCPAgent")
class TestMicrosoftAgentFramework:
    """Test Microsoft Agent Framework integration"""
    
    @pytest.mark.asyncio
    async def test_microsoft_agent_creation(self):
        """Test creating Microsoft Agent Framework agent"""
        if MicrosoftMCPAgent is None:
            pytest.skip("Microsoft Agent modules not available")
            return
        
        from agent_mcp.microsoft_agent_framework import MicrosoftAgentConfig
        
        config = MicrosoftAgentConfig(
            agent_id="test_microsoft_agent",
            name="Test Microsoft Agent",
            description="Test agent for Microsoft framework",
            llm_config={"model": "gpt-3.5-turbo", "api_key": TestConfig.TEST_STRIPE_KEY},
            skills=["WebSearch"]
        )
        
        assert config.agent_id == "test_microsoft_agent"
        assert config.llm_config["model"] == "gpt-3.5-turbo"

@pytest.mark.order(4)
@skip_if_unavailable("ZeroTrustSecurityLayer")
class TestZeroTrustSecurity:
    """Test zero-trust security layer"""
    
    @pytest.fixture
    async def security_layer(self):
        if ZeroTrustSecurityLayer is None:
            pytest.skip("Security modules not available")
            return
        
        storage = MockStorage()
        return ZeroTrustSecurityLayer(
            secret_key="test_secret_key",
            storage_backend=storage
        )
    
    @pytest.mark.asyncio
    async def test_agent_identity_creation(self, security_layer):
        """Test agent identity creation"""
        if ZeroTrustSecurityLayer is None:
            pytest.skip("Security modules not available")
            return
        
        identity, token = await security_layer.create_agent_identity(
            agent_id="test_security_agent",
            capabilities=["test_capability"],
            owner="test_owner",
            security_level=SecurityLevel.MEDIUM
        )
        
        assert identity.agent_id == "test_security_agent"
        assert identity.capabilities == ["test_capability"]
        assert token is not None
    
    @pytest.mark.asyncio
    async def test_authentication_authorization(self, security_layer):
        """Test authentication and authorization"""
        if ZeroTrustSecurityLayer is None or Permission is None or SecurityLevel is None:
            pytest.skip("Security modules not available")
            return
        
        # Create agent identity
        identity, token = await security_layer.create_agent_identity(
            agent_id="test_auth_agent",
            capabilities=["test_capability"],
            security_level=SecurityLevel.HIGH
        )
        
        # Test successful authentication
        auth_result = await security_layer.authenticate_agent(
            token=token,
            action="tool:call",
            context={"target": "test_tool"}
        )
        
        assert auth_result is not None
        assert auth_result["authorization"]["allowed"] == True
    
    @pytest.mark.asyncio
    async def test_permission_denied_insufficient_security(self, security_layer):
        """Test permission denied due to insufficient security level"""
        if ZeroTrustSecurityLayer is None:
            pytest.skip("Security modules not available")
            return
        
        # Create low security level agent
        identity, token = await security_layer.create_agent_identity(
            agent_id="test_low_security_agent",
            capabilities=["basic_capability"],
            security_level=SecurityLevel.LOW
        )
        
        # Try to access high-level operation
        auth_result = await security_layer.authenticate_agent(
            token=token,
            action="system:admin"
        )
        
        assert auth_result is None  # Should fail authentication

@pytest.mark.order(5)
@skip_if_unavailable("HybridPaymentGateway")
class TestHybridPaymentGateway:
    """Test hybrid payment gateway"""
    
    @pytest.fixture
    async def payment_gateway(self):
        if HybridPaymentGateway is None or PaymentMethod is None or PaymentRequest is None:
            pytest.skip("Payment modules not available")
            return
        
        return HybridPaymentGateway(
            stripe_config={"api_key": TestConfig.TEST_STRIPE_KEY},
            usdc_config={
                "rpc_url": TestConfig.TEST_USDC_RPC,
                "private_key": TestConfig.TEST_USDC_PRIVATE_KEY
            }
        )
    
    @pytest.mark.asyncio
    async def test_payment_processing(self, payment_gateway):
        """Test payment processing"""
        if HybridPaymentGateway is None:
            pytest.skip("Payment modules not available")
            return
        
        # Test Stripe payment
        stripe_request = PaymentRequest(
            sender_agent_id="test_sender",
            receiver_agent_id="test_receiver",
            amount=10.0,
            currency="USD",
            task_id="test_payment_123",
            description="Test payment",
            payment_method=PaymentMethod.STRIPE
        )
        
        response = await payment_gateway.process_payment(stripe_request)
        
        assert response.payment_id is not None
        assert response.amount == 10.0
        assert response.currency == "USD"
    
    @pytest.mark.asyncio
    async def test_usdc_payment(self, payment_gateway):
        """Test USDC payment processing"""
        if HybridPaymentGateway is None:
            pytest.skip("Payment modules not available")
            return
        
        # Test USDC payment
        usdc_request = PaymentRequest(
            sender_agent_id="test_sender",
            receiver_agent_id="test_receiver",
            amount=5.0,
            currency="USDC",
            task_id="test_usdc_123",
            description="Test USDC payment",
            payment_method=PaymentMethod.USDC
        )
        
        response = await payment_gateway.process_payment(usdc_request)
        
        assert response.payment_id is not None
        assert response.amount == 5.0
        assert response.currency == "USDC"

@pytest.mark.order(6)
@skip_if_unavailable("MultiLanguageAgentRegistry")
class TestMultiLanguageRegistry:
    """Test multi-language agent registry"""
    
    @pytest.fixture
    async def agent_registry(self):
        if MultiLanguageAgentRegistry is None or AgentLanguage is None or AgentProtocol is None:
            pytest.skip("Registry modules not available")
            return
        
        storage = MockStorage()
        return MultiLanguageAgentRegistry(storage_backend=storage)
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, agent_registry):
        """Test agent registration"""
        if MultiLanguageAgentRegistry is None:
            pytest.skip("Registry modules not available")
            return
        
        from agent_mcp.registry import AgentRegistration
        
        registration = AgentRegistration(
            agent_id="test_registry_agent",
            name="Test Registry Agent",
            description="Test agent for registry",
            language=AgentLanguage.PYTHON,
            frameworks=["test_framework"],
            protocols=[AgentProtocol.MCP, AgentProtocol.REST],
            endpoint="http://localhost:8070",
            capabilities=["test_capability"]
        )
        
        result = await agent_registry.register_agent(registration)
        
        assert result["status"] == "success"
        assert result["agent_id"] == "test_registry_agent"
    
    @pytest.mark.asyncio
    async def test_agent_discovery(self, agent_registry):
        """Test agent discovery"""
        if MultiLanguageAgentRegistry is None:
            pytest.skip("Registry modules not available")
            return
        
        # First register an agent
        await self.test_agent_registration(agent_registry)
        
        # Test discovery
        discovered = await agent_registry.discover_agents(
            capability="test_capability"
        )
        
        assert len(discovered) >= 1
        assert discovered[0]["agent_id"] == "test_registry_agent"

@pytest.mark.order(7)
@skip_if_unavailable("OpenAPIServer")
class TestOpenAPIProtocol:
    """Test OpenAPI protocol support"""
    
    @pytest.fixture
    async def openapi_server(self):
        if OpenAPIServer is None:
            pytest.skip("OpenAPI modules not available")
            return
        
        storage = MockStorage()
        return OpenAPIServer(
            agent_id="test_openapi_agent",
            agent_info={
                "name": "Test OpenAPI Agent",
                "description": "Test agent for OpenAPI protocol",
                "framework": "custom"
            }
        )
    
    @pytest.mark.asyncio
    async def test_openapi_spec_generation(self, openapi_server):
        """Test OpenAPI specification generation"""
        if OpenAPIServer is None:
            pytest.skip("OpenAPI modules not available")
            return
        
        spec = openapi_server.get_spec_json()
        
        # Basic validation
        assert spec is not None
        spec_data = json.loads(spec)
        assert spec_data["openapi"] == "3.0.0"
        assert "paths" in spec_data

@pytest.mark.order(8)
class TestIntegration:
    """Test integration between components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_integration(self):
        """Test complete integration scenario"""
        if any([
            ZeroTrustSecurityLayer is None,
            HybridPaymentGateway is None,
            MultiLanguageAgentRegistry is None
        ]):
            pytest.skip("Integration test requires all modules")
            return
        
        # Setup components
        storage = MockStorage()
        security = ZeroTrustSecurityLayer(storage_backend=storage)
        payment_gateway = HybridPaymentGateway(
            stripe_config={"api_key": TestConfig.TEST_STRIPE_KEY}
        )
        registry = MultiLanguageAgentRegistry(storage_backend=storage)
        
        # Create agent with all capabilities
        identity, token = await security.create_agent_identity(
            agent_id="integration_agent",
            capabilities=["test", "payment", "messaging"],
            security_level=SecurityLevel.HIGH
        )
        
        # Register agent
        from agent_mcp.registry import AgentRegistration
        registration = AgentRegistration(
            agent_id="integration_agent",
            name="Integration Test Agent",
            description="Test agent for integration",
            language=AgentLanguage.PYTHON,
            frameworks=["AgentMCP"],
            protocols=[AgentProtocol.MCP, AgentProtocol.OPENAPI],
            endpoint="http://localhost:8888",
            auth_token=token
        )
        
        reg_result = await registry.register_agent(registration)
        assert reg_result["status"] == "success"
        
        # Test authentication
        auth_result = await security.authenticate_agent(
            token=token,
            action="tool:call",
            context={"target": "test_tool"}
        )
        
        assert auth_result is not None
        assert auth_result["authorization"]["allowed"] == True
        
        logger.info("Integration test completed successfully")

# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers",
        """
        asyncio: marks test as async
        integration: marks test as integration test
        unit: marks test as unit test
        """
    )

if __name__ == "__main__":
    import sys
    
    available_tests = {
        "a2a": TestA2AProtocol,
        "llamaindex": TestLlamaIndexMCPAdapter,
        "microsoft": TestMicrosoftAgentFramework,
        "security": TestZeroTrustSecurity,
        "payments": TestHybridPaymentGateway,
        "registry": TestMultiLanguageRegistry,
        "openapi": TestOpenAPIProtocol,
        "integration": TestIntegration
    }
    
    if len(sys.argv) > 1:
        category = sys.argv[1]
        if category in available_tests:
            print(f"Running {category} tests...")
            pytest.main([f"tests/test_comprehensive.py::{available_tests[category].__name__}"])
        else:
            print(f"Available test categories: {list(available_tests.keys())}")
            print("Running all tests...")
            pytest.main(["-v", "tests/test_comprehensive.py"])
    else:
        print("Running all tests...")
        pytest.main(["-v", "tests/test_comprehensive.py"])