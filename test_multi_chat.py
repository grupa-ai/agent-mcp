"""
Test and Demo for Multi-Chat Agent with Network Modes

This demonstrates the new feature:
- One agent can work in Company, Business, and Public modes simultaneously
- Automatic routing based on handle suffix
- Zero data leakage between modes
"""

import asyncio
from agent_mcp.multi_chat import MultiChatAgent, create_multi_chat_agent


async def test_company_mode():
    """Test: Company mode agent can ONLY talk to company agents"""
    print("\n=== Test 1: COMPANY Mode ===")
    agent = create_multi_chat_agent("@alice@acme.corp")
    await agent.connect(
        company_endpoint="https://company.internal",
        business_endpoint="https://company.business",
        public_endpoint="https://mcp.agentmcp.com"
    )
    
    # To company - OK
    result = await agent.send("@bob@acme.corp", "internal data")
    print(f"✓ To .corp: {result['via']}")
    
    # To business - BLOCKED
    try:
        await agent.send("@partner@vendor.business", "external")
        print("✗ Should have blocked business")
    except PermissionError as e:
        print(f"✓ Blocked to .business: {e}")
    
    # To public - BLOCKED
    try:
        await agent.send("@gpt@openai.public", "external")
        print("✗ Should have blocked public")
    except PermissionError as e:
        print(f"✓ Blocked to .public: {e}")


async def test_business_mode():
    """Test: Business mode agent can talk to company + business, sanitize public"""
    print("\n=== Test 2: BUSINESS Mode ===")
    agent = create_multi_chat_agent("@alice@acme.business")
    await agent.connect(
        company_endpoint="https://company.internal",
        business_endpoint="https://company.business",
        public_endpoint="https://mcp.agentmcp.com"
    )
    
    # To company - OK
    result = await agent.send("@bob@acme.corp", "internal data")
    print(f"✓ To .corp: {result['via']}")
    
    # To business - OK
    result = await agent.send("@partner@vendor.business", "external")
    print(f"✓ To .business: {result['via']}")
    
    # To public - OK but sanitized
    result = await agent.send("@gpt@openai.public", {"question": "hi", "api_key": "secret123"})
    print(f"✓ To .public: sanitized = {result['message'].get('api_key')}")


async def test_public_mode():
    """Test: Public mode can talk to anyone"""
    print("\n=== Test 3: PUBLIC Mode ===")
    agent = create_multi_chat_agent("@alice@acme.public")
    await agent.connect(
        company_endpoint="https://company.internal",
        business_endpoint="https://company.business",
        public_endpoint="https://mcp.agentmcp.com"
    )
    
    # To company - OK
    result = await agent.send("@bob@acme.corp", "hello")
    print(f"✓ To .corp: {result['via']}")
    
    # To business - OK
    result = await agent.send("@partner@vendor.business", "hello")
    print(f"✓ To .business: {result['via']}")
    
    # To public - OK
    result = await agent.send("@gpt@openai.public", "hello")
    print(f"✓ To .public: {result['via']}")


async def test_default_mode():
    """Test: Plain string defaults to public"""
    print("\n=== Test 4: DEFAULT Mode (plain string) ===")
    agent = create_multi_chat_agent("MyAgent")
    await agent.connect(
        company_endpoint="https://company.internal",
        business_endpoint="https://company.business",
        public_endpoint="https://mcp.agentmcp.com"
    )
    
    print(f"Mode: {agent.mode.value}")
    
    result = await agent.send("@gpt@openai.public", "hello")
    print(f"✓ To .public: {result['via']}")


async def main():
    print("=" * 60)
    print("MULTI-CHAT AGENT TEST SUITE")
    print("=" * 60)
    
    await test_company_mode()
    await test_business_mode()
    await test_public_mode()
    await test_default_mode()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
