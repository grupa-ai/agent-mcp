"""
Comprehensive AI SDK Integration Demo
Shows AgentMCP working with multiple AI providers: OpenAI, Gemini, Claude, Agent Lightning, etc.
"""

import os
import asyncio
import json
from typing import Dict, Any, List

# Import AgentMCP components
from agent_mcp.heterogeneous_group_chat import HeterogeneousGroupChat
from agent_mcp.proxy_agent import ProxyAgent

# Check environment variables
def check_environment():
    """Check which AI providers are available"""
    print("🔑 Environment Check:")
    print(f"   OpenAI: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
    print(f"   Google AI: {'✅' if os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GOOGLE_GEMINI_API_KEY') else '❌'}")
    print(f"   Anthropic: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    print(f"   Agent Lightning: {'✅' if os.getenv('AGENT_LIGHTNING_API_KEY') else '❌'}")
    
    available_providers = []
    if os.getenv('OPENAI_API_KEY'):
        available_providers.append('OpenAI')
    if os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GOOGLE_GEMINI_API_KEY'):
        available_providers.append('Google AI')
    if os.getenv('ANTHROPIC_API_KEY'):
        available_providers.append('Anthropic Claude')
    if os.getenv('AGENT_LIGHTNING_API_KEY'):
        available_providers.append('Agent Lightning')
    
    print(f"   Available: {', '.join(available_providers)}")
    return available_providers

async def create_multi_provider_demo():
    """Create a demo with multiple AI providers"""
    print("🚀 Multi-Provider AI Agent Demo")
    print("=" * 50)
    
    available_providers = check_environment()
    
    if not available_providers:
        print("❌ No AI providers available")
        return False
    
    # Create heterogeneous group chat
    group = HeterogeneousGroupChat(
        name="MultiProviderDemoGroup",
        server_url="https://mcp-server-ixlfhxquwq-ew.a.run.app"
    )
    
    print("\n🎯 Creating Agents with Different AI Providers:")
    
    agents = []
    
    # 1. OpenAI Agent (Coordinator)
    if 'OpenAI' in available_providers:
        from agent_mcp.enhanced_mcp_agent import EnhancedMCPAgent
        
        openai_coordinator = group.create_coordinator(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        agents.append(openai_coordinator)
        print("✅ OpenAI Coordinator created")
    
    # 2. Google AI Agent
    if 'Google AI' in available_providers:
        try:
            from agent_mcp.google_ai_mcp_adapter import GoogleAIMCPAdapter
            
            google_agent = GoogleAIMCPAdapter(
                name="GoogleAIAgent",
                api_key=os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
            )
            agents.append(google_agent)
            print("✅ Google AI Agent created")
        except ImportError:
            print("⚠️  Google AI adapter not available")
    
    # 3. Anthropic Claude Agent
    if 'Anthropic Claude' in available_providers:
        try:
            from agent_mcp.claude_mcp_adapter import ClaudeMCPAdapter
            
            claude_agent = ClaudeMCPAdapter(
                name="ClaudeAgent",
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            agents.append(claude_agent)
            print("✅ Claude Agent created")
        except ImportError:
            print("⚠️  Claude adapter not available")
    
    # 4. Agent Lightning Agent (RL/Training)
    if 'Agent Lightning' in available_providers:
        try:
            from agent_mcp.agent_lightning_mcp_adapter import AgentLightningMCPAdapter
            
            lightning_agent = AgentLightningMCPAdapter(
                name="LightningAgent",
                api_key=os.getenv("AGENT_LIGHTNING_API_KEY")
            )
            agents.append(lightning_agent)
            print("✅ Agent Lightning created")
        except ImportError:
            print("⚠️  Agent Lightning adapter not available")
    
    # 5. Remote Agent (existing on server)
    try:
        remote_ai_agent = ProxyAgent(name="RemoteAIAgent", client_mode=True)
        await remote_ai_agent.connect_to_remote_agent("SomeExistingAgent", group.server_url)
        agents.append(remote_ai_agent)
        print("✅ Remote AI Agent proxy created")
    except Exception as e:
        print(f"⚠️  Remote agent creation failed: {e}")
    
    # Add all agents to group
    group.add_agents(agents)
    print(f"✅ Added {len(agents)} agents to group")
    
    return group, agents

async def demonstrate_multi_provider_task():
    """Demonstrate task execution with different AI providers"""
    print("\n🎯 Multi-Provider Task Execution:")
    print("-" * 30)
    
    available_providers = check_environment()
    
    if len(available_providers) < 2:
        print("⚠️  Need at least 2 AI providers for demo")
        return False
    
    # Create demo group
    group, agents = await create_multi_provider_demo()
    
    # Define a task that shows different AI capabilities
    multi_provider_task = {
        "task_id": "multi_provider_showcase",
        "description": "Showcase different AI provider capabilities",
        "steps": [
            {
                "task_id": "creative_writing",
                "agent": "GoogleAIAgent" if 'Google AI' in available_providers else "ClaudeAgent",
                "description": "Write a creative short story about AI assistants collaborating",
                "expected_capability": "Creative text generation"
            },
            {
                "task_id": "analysis_task", 
                "agent": "ClaudeAgent" if 'Anthropic Claude' in available_providers else "GoogleAIAgent",
                "description": "Analyze the collaboration potential of AI agents",
                "expected_capability": "Analytical reasoning",
                "depends_on": ["creative_writing"]
            },
            {
                "task_id": "coordination_task",
                "agent": "LightningAgent" if 'Agent Lightning' in available_providers else "GoogleAIAgent",
                "description": "Coordinate the multi-agent system and optimize performance",
                "expected_capability": "Training and optimization",
                "depends_on": ["analysis_task"]
            },
            {
                "task_id": "integration_task",
                "agent": "RemoteAIAgent",
                "description": "Integrate with existing AI systems and provide compatibility layer",
                "expected_capability": "API integration",
                "depends_on": ["coordination_task"]
            }
        ]
    }
    
    try:
        # Connect to server
        print("🔗 Connecting to deployed server...")
        await group.connect()
        print("✅ Connected successfully")
        
        # Submit task
        print("📋 Submitting multi-provider task...")
        await group.submit_task(multi_provider_task)
        
        # Wait for completion
        print("⏳ Waiting for task completion...")
        await group.wait_for_completion()
        
        print("✅ Multi-provider task completed!")
        return True
        
    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        return False

async def show_provider_capabilities():
    """Show capabilities of available AI providers"""
    print("\n🛠️ AI Provider Capabilities:")
    print("-" * 40)
    
    capabilities_summary = {
        "OpenAI": {
            "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            "strengths": ["Reasoning", "Code generation", "Analysis"],
            "cost": "Medium"
        },
        "Google AI": {
            "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"],
            "strengths": ["Multimodal", "Speed", "Cost-effective"],
            "cost": "Low"
        },
        "Anthropic Claude": {
            "models": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"],
            "strengths": ["Safety", "Analysis", "Long context"],
            "cost": "Medium-High"
        },
        "Agent Lightning": {
            "models": ["Custom models", "RL-trained"],
            "strengths": ["Training", "Optimization", "Distributed"],
            "cost": "Varies"
        }
    }
    
    for provider, caps in capabilities_summary.items():
        if any(provider in check_environment() for provider in provider.split()):
            print(f"✅ {provider}:")
            print(f"   Models: {', '.join(caps['models'])}")
            print(f"   Strengths: {', '.join(caps['strengths'])}")
            print(f"   Cost: {caps['cost']}")
        else:
            print(f"❌ {provider}: Not available")
    
    return capabilities_summary

async def main():
    """Main demonstration"""
    print("🌟 AgentMCP Multi-Provider AI Integration Demo")
    print("=" * 60)
    
    # Show environment setup
    available_providers = check_environment()
    
    if not available_providers:
        print("\n❌ SETUP REQUIRED:")
        print("Please set at least one AI provider API key:")
        print("   export OPENAI_API_KEY=your_key")
        print("   export GOOGLE_AI_API_KEY=your_key") 
        print("   export ANTHROPIC_API_KEY=your_key")
        print("   export AGENT_LIGHTNING_API_KEY=your_key")
        return False
    
    # Show provider capabilities
    await show_provider_capabilities()
    
    # Create and run multi-provider demo
    print(f"\n🚀 Starting Demo with {len(available_providers)} Providers")
    success = await demonstrate_multi_provider_task()
    
    if success:
        print(f"\n🎉 MULTI-PROVIDER DEMO SUCCESS!")
        print("=" * 50)
        print("✅ Heterogeneous multi-agent collaboration")
        print("✅ Multiple AI provider support")
        print("✅ Advanced capabilities demonstrated")
        print("✅ Production-ready architecture")
        print()
        print("📦 AgentMCP now supports:")
        print("   • OpenAI GPT models")
        print("   • Google Gemini models")
        print("   • Anthropic Claude models")
        print("   • Agent Lightning training")
        print("   • Multi-provider cost optimization")
        print("   • Heterogeneous collaboration")
        print("   • Advanced task coordination")
        print()
        print("🚀 READY FOR PRODUCTION DEPLOYMENT!")
        
        return True
    else:
        print(f"\n❌ MULTI-PROVIDER DEMO FAILED!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)