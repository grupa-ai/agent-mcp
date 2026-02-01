"""
Simple functionality test for AgentMCP
Basic test to ensure core features work
"""

import asyncio
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

async def test_basic_functionality():
    """Test basic functionality works"""
    print("Testing AgentMCP basic functionality...")
    
    # Test 1: Import core modules
    try:
        from agent_mcp.mcp_decorator import mcp_agent
        from agent_mcp.mcp_transport import HTTPTransport
        print("✓ Core imports successful")
    except ImportError as e:
        print(f"✗ Core import failed: {e}")
        return False
    
    # Test 2: Create basic agent
    try:
        @mcp_agent(mcp_id="test_basic")
        class BasicAgent:
            async def process_message(self, message: str) -> str:
                return f"Processed: {message}"
        
        agent = BasicAgent()
        print("✓ Basic agent creation successful")
    except Exception as e:
        print(f"✗ Basic agent creation failed: {e}")
        return False
    
    # Test 3: Create transport
    try:
        transport = HTTPTransport(port=8090)
        print("✓ Transport creation successful")
    except Exception as e:
        print(f"✗ Transport creation failed: {e}")
        return False
    
    # Test 4: Connect agent to transport
    try:
        agent.transport = transport
        print("✓ Agent transport assignment successful")
    except Exception as e:
        print(f"✗ Agent transport assignment failed: {e}")
        return False
    
    # Test 5: Register agent with transport
    try:
        # Mock server URL for testing
        transport.remote_url = "http://localhost:8090"
        agent.is_remote = True
        transport.agent_name = "test_basic"
        transport.token = "test_token"
        
        print("✓ Agent transport configuration successful")
    except Exception as e:
        print(f"✗ Agent transport configuration failed: {e}")
        return False
    
    print("✓ All basic functionality tests passed!")
    return True

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())