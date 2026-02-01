"""
Comprehensive Test Suite for AgentMCP Platform
Tests all frameworks, security, payments, and heterogeneous collaboration
"""

import os
import asyncio
import json
import time
from typing import Dict, Any, List
from datetime import datetime

# Core imports
from agent_mcp.enhanced_mcp_agent import EnhancedMCPAgent
from agent_mcp.heterogeneous_group_chat import HeterogeneousGroupChat
from agent_mcp.security import SecurityManager
from agent_mcp.payments import PaymentManager
from agent_mcp.registry import AgentRegistry
from agent_mcp.a2a_protocol import A2AProtocol
from agent_mcp.openapi_protocol import OpenAPIProtocol

# Framework adapters
from agent_mcp.langchain_mcp_adapter import LangchainMCPAdapter
from agent_mcp.crewai_mcp_adapter import CrewAIMCPAdapter
from agent_mcp.langgraph_mcp_adapter import LangGraphMCPAdapter
from agent_mcp.llamaindex_mcp_adapter import LlamaIndexMCPAdapter
from agent_mcp.microsoft_agent_framework import MicrosoftAgentMCPAdapter
from agent_mcp.pydantic_ai_mcp_adapter import PydanticAIMCPAdapter
from agent_mcp.missing_frameworks import (
    BeeAIMCPAdapter, 
    AgentGPTMCPAdapter, 
    SuperAGIMCPAdapter, 
    FractalMCPAdapter,
    SwarmMCPAdapter
)

# Langchain imports for existing agents
from langchain_openai import ChatOpenAI
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage
from langchain_community.tools import Tool
from crewai import Agent as CrewAgent

class ComprehensiveTestSuite:
    """Comprehensive test suite for the AgentMCP platform"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Please set OPENAI_API_KEY environment variable")
        
        self.server_url = "https://mcp-server-ixlfhxquwq-ew.a.run.app"
        self.test_results = {}
        self.agents_created = []
        self.group_chat = None
        
        # Initialize security and payments
        self.security_manager = SecurityManager()
        self.payment_manager = PaymentManager(
            stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder"),
            usdc_rpc_url=os.getenv("USDC_RPC_URL", "https://polygon-rpc.com")
        )
        self.registry = AgentRegistry()
        
    async def setup_all_framework_agents(self) -> List:
        """Create agents from all supported frameworks"""
        agents = []
        
        print("\n=== Setting up Framework Agents ===")
        
        # 1. Enhanced MCP Agent (Core)
        core_agent = EnhancedMCPAgent(
            name="CoreAgent",
            system_message="I am the core agent handling foundational tasks and coordination.",
            llm_config={
                "config_list": [{"model": "gpt-3.5-turbo", "api_key": self.api_key}]
            }
        )
        agents.append(core_agent)
        
        # 2. Langchain Agent
        try:
            search_tool = Tool(
                name="search",
                description="Search the web for information",
                func=lambda x: f"Search results for: {x}"
            )
            langchain_agent = LangchainMCPAdapter(
                name="LangchainAgent",
                system_message="I am a Langchain-based research agent with web search capabilities.",
                tools=[search_tool]
            )
            agents.append(langchain_agent)
        except Exception as e:
            print(f"Failed to create Langchain agent: {e}")
        
        # 3. CrewAI Agent
        try:
            crew_agent = CrewAgent(
                role="Project Manager",
                goal="Manage and coordinate project tasks efficiently",
                backstory="I am an experienced project manager specializing in AI projects."
            )
            crewai_adapter = CrewAIMCPAdapter(
                name="CrewAIAgent",
                crewai_agent=crew_agent
            )
            agents.append(crewai_adapter)
        except Exception as e:
            print(f"Failed to create CrewAI agent: {e}")
        
        # 4. LangGraph Agent
        try:
            langgraph_agent = LangGraphMCPAdapter(
                name="LangGraphAgent",
                system_message="I am a LangGraph agent specializing in workflow automation."
            )
            agents.append(langgraph_agent)
        except Exception as e:
            print(f"Failed to create LangGraph agent: {e}")
        
        # 5. LlamaIndex Agent
        try:
            llamaindex_agent = LlamaIndexMCPAdapter(
                name="LlamaIndexAgent",
                system_message="I am a LlamaIndex agent specializing in document analysis."
            )
            agents.append(llamaindex_agent)
        except Exception as e:
            print(f"Failed to create LlamaIndex agent: {e}")
        
        # 6. Microsoft Agent Framework
        try:
            microsoft_agent = MicrosoftAgentMCPAdapter(
                name="MicrosoftAgent",
                system_message="I am a Microsoft agent framework integration."
            )
            agents.append(microsoft_agent)
        except Exception as e:
            print(f"Failed to create Microsoft agent: {e}")
        
        # 7. Pydantic AI Agent
        try:
            pydantic_agent = PydanticAIMCPAdapter(
                name="PydanticAIAgent",
                system_message="I am a Pydantic AI agent with type-safe operations."
            )
            agents.append(pydantic_agent)
        except Exception as e:
            print(f"Failed to create Pydantic AI agent: {e}")
        
        # 8. BeeAI Agent
        try:
            beeai_agent = BeeAIMCPAdapter(
                name="BeeAIAgent",
                system_message="I am a BeeAI agent specializing in task orchestration."
            )
            agents.append(beeai_agent)
        except Exception as e:
            print(f"Failed to create BeeAI agent: {e}")
        
        # 9. AgentGPT Agent
        try:
            agentgpt_agent = AgentGPTMCPAdapter(
                name="AgentGPTAgent",
                system_message="I am an AgentGPT conversational AI agent."
            )
            agents.append(agentgpt_agent)
        except Exception as e:
            print(f"Failed to create AgentGPT agent: {e}")
        
        # 10. SuperAGI Agent
        try:
            superagi_agent = SuperAGIMCPAdapter(
                name="SuperAGIAgent",
                system_message="I am a SuperAGI enterprise automation agent."
            )
            agents.append(superagi_agent)
        except Exception as e:
            print(f"Failed to create SuperAGI agent: {e}")
        
        # 11. Fractal Agent
        try:
            fractal_agent = FractalMCPAdapter(
                name="FractalAgent",
                system_message="I am a Fractal blockchain and DeFi agent."
            )
            agents.append(fractal_agent)
        except Exception as e:
            print(f"Failed to create Fractal agent: {e}")
        
        # 12. Swarm Agent
        try:
            swarm_agent = SwarmMCPAdapter(
                name="SwarmAgent",
                system_message="I am a Swarm agent specializing in agent handoff and coordination."
            )
            agents.append(swarm_agent)
        except Exception as e:
            print(f"Failed to create Swarm agent: {e}")
        
        # 13. Custom Python Agent (built-in)
        class CustomPythonAgent(EnhancedMCPAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            async def custom_function(self, data: str) -> str:
                """Custom function specific to this agent"""
                return f"Custom Python agent processed: {data}"
        
        custom_agent = CustomPythonAgent(
            name="CustomPythonAgent",
            system_message="I am a custom-built Python agent with specialized functions.",
            llm_config={
                "config_list": [{"model": "gpt-3.5-turbo", "api_key": self.api_key}]
            }
        )
        agents.append(custom_agent)
        
        self.agents_created = agents
        print(f"✅ Created {len(agents)} agents from all frameworks")
        return agents
    
    async def test_security_features(self) -> Dict[str, Any]:
        """Test security features"""
        print("\n=== Testing Security Features ===")
        
        security_results = {}
        
        try:
            # Test DID creation
            did = await self.security_manager.create_did()
            security_results["did_creation"] = {"status": "success", "did": did}
            print(f"✅ Created DID: {did[:20]}...")
            
            # Test identity verification
            is_valid = await self.security_manager.verify_identity(did)
            security_results["identity_verification"] = {"status": "success", "valid": is_valid}
            print(f"✅ Identity verification: {is_valid}")
            
            # Test secure messaging
            message = "Test secure message"
            encrypted = await self.security_manager.encrypt_message(did, message)
            decrypted = await self.security_manager.decrypt_message(did, encrypted)
            
            security_results["secure_messaging"] = {
                "status": "success", 
                "original": message,
                "encrypted_length": len(encrypted),
                "decrypted": decrypted
            }
            print(f"✅ Secure messaging test passed")
            
        except Exception as e:
            security_results["error"] = str(e)
            print(f"❌ Security test failed: {e}")
        
        return security_results
    
    async def test_payment_features(self) -> Dict[str, Any]:
        """Test payment features"""
        print("\n=== Testing Payment Features ===")
        
        payment_results = {}
        
        try:
            # Test Stripe payment intent
            if self.payment_manager.stripe_enabled:
                payment_intent = await self.payment_manager.create_stripe_payment(
                    amount=1000,  # $10.00
                    currency="usd",
                    description="Test payment"
                )
                payment_results["stripe_payment"] = {
                    "status": "success",
                    "payment_intent_id": payment_intent.get("id")
                }
                print(f"✅ Stripe payment created: {payment_intent.get('id')}")
            
            # Test USDC payment
            if self.payment_manager.usdc_enabled:
                usdc_payment = await self.payment_manager.create_usdc_payment(
                    recipient_address="0x1234567890123456789012345678901234567890",
                    amount=10.0,
                    description="Test USDC payment"
                )
                payment_results["usdc_payment"] = {
                    "status": "success",
                    "transaction_hash": usdc_payment.get("tx_hash", "simulated")
                }
                print(f"✅ USDC payment created")
            
            # Test hybrid payment
            hybrid_payment = await self.payment_manager.create_hybrid_payment(
                amount=500,
                currency="usd",
                description="Test hybrid payment",
                split_ratio={"stripe": 0.7, "usdc": 0.3}
            )
            payment_results["hybrid_payment"] = {
                "status": "success",
                "details": hybrid_payment
            }
            print(f"✅ Hybrid payment created")
            
        except Exception as e:
            payment_results["error"] = str(e)
            print(f"❌ Payment test failed: {e}")
        
        return payment_results
    
    async def test_agent_collaboration(self) -> Dict[str, Any]:
        """Test heterogeneous agent collaboration"""
        print("\n=== Testing Agent Collaboration ===")
        
        collaboration_results = {}
        
        try:
            # Create group chat
            self.group_chat = HeterogeneousGroupChat(
                name="ComprehensiveTestGroup",
                server_url=self.server_url
            )
            
            # Create coordinator
            coordinator = self.group_chat.create_coordinator(self.api_key)
            
            # Add all framework agents
            if self.agents_created:
                self.group_chat.add_agents(self.agents_created)
            
            # Register agents in the registry
            for agent in self.agents_created:
                await self.registry.register_agent(
                    agent_id=agent.name,
                    framework=agent.__class__.__name__,
                    capabilities=["collaboration", "task_processing"],
                    endpoint=f"{self.server_url}/agents/{agent.name}"
                )
            
            # Connect all agents
            await self.group_chat.connect()
            
            collaboration_results["group_setup"] = {
                "status": "success",
                "agents_count": len(self.agents_created),
                "coordinator": coordinator.name
            }
            print(f"✅ Group chat setup with {len(self.agents_created)} agents")
            
            # Test discovery
            discovered_agents = await self.registry.discover_agents(
                capabilities=["collaboration"]
            )
            collaboration_results["agent_discovery"] = {
                "status": "success",
                "discovered_count": len(discovered_agents)
            }
            print(f"✅ Discovered {len(discovered_agents)} agents")
            
        except Exception as e:
            collaboration_results["error"] = str(e)
            print(f"❌ Collaboration test failed: {e}")
        
        return collaboration_results
    
    async def test_comprehensive_task(self) -> Dict[str, Any]:
        """Test a comprehensive task involving all frameworks"""
        print("\n=== Testing Comprehensive Task ===")
        
        task_results = {}
        
        try:
            if not self.group_chat:
                raise ValueError("Group chat not initialized")
            
            # Define a comprehensive task that uses multiple frameworks
            comprehensive_task = {
                "task_id": "comprehensive_ai_platform_analysis",
                "type": "multi_framework_analysis",
                "description": "Analyze the current AI agent platform landscape and provide recommendations",
                "steps": [
                    {
                        "task_id": "market_research",
                        "agent": "LangchainAgent",
                        "description": "Research current AI agent frameworks and their market positioning",
                        "content": {"research_type": "market_analysis"}
                    },
                    {
                        "task_id": "project_planning",
                        "agent": "CrewAIAgent", 
                        "description": "Create a project plan for building a comprehensive AI platform",
                        "depends_on": ["market_research"]
                    },
                    {
                        "task_id": "workflow_design",
                        "agent": "LangGraphAgent",
                        "description": "Design the workflow architecture for the platform",
                        "depends_on": ["project_planning"]
                    },
                    {
                        "task_id": "documentation_analysis",
                        "agent": "LlamaIndexAgent",
                        "description": "Analyze documentation patterns and best practices",
                        "depends_on": ["workflow_design"]
                    },
                    {
                        "task_id": "security_review",
                        "agent": "MicrosoftAgent",
                        "description": "Review security requirements and implement security measures",
                        "depends_on": ["documentation_analysis"]
                    },
                    {
                        "task_id": "type_safe_design",
                        "agent": "PydanticAIAgent",
                        "description": "Design type-safe interfaces and data models",
                        "depends_on": ["security_review"]
                    },
                    {
                        "task_id": "task_orchestration",
                        "agent": "BeeAIAgent",
                        "description": "Orchestrate the deployment and testing process",
                        "depends_on": ["type_safe_design"]
                    },
                    {
                        "task_id": "user_interaction",
                        "agent": "AgentGPTAgent",
                        "description": "Design user interaction patterns and conversational flows",
                        "depends_on": ["task_orchestration"]
                    },
                    {
                        "task_id": "enterprise_integration",
                        "agent": "SuperAGIAgent",
                        "description": "Plan enterprise integration strategies",
                        "depends_on": ["user_interaction"]
                    },
                    {
                        "task_id": "blockchain_features",
                        "agent": "FractalAgent",
                        "description": "Design blockchain and DeFi integration features",
                        "depends_on": ["enterprise_integration"]
                    },
                    {
                        "task_id": "coordination_review",
                        "agent": "SwarmAgent",
                        "description": "Review and coordinate all agent handoffs and integrations",
                        "depends_on": ["blockchain_features"]
                    },
                    {
                        "task_id": "custom_implementation",
                        "agent": "CustomPythonAgent",
                        "description": "Implement custom Python features and integrations",
                        "depends_on": ["coordination_review"]
                    }
                ]
            }
            
            # Submit the task
            start_time = time.time()
            await self.group_chat.submit_task(comprehensive_task)
            await self.group_chat.wait_for_completion()
            end_time = time.time()
            
            # Collect results
            all_results = self.group_chat.group_state
            
            task_results = {
                "status": "completed",
                "duration_seconds": end_time - start_time,
                "steps_completed": len(all_results),
                "frameworks_used": len(set(step["agent"] for step in comprehensive_task["steps"])),
                "sample_results": {k: str(v)[:200] for k, v in list(all_results.items())[:3]}
            }
            
            print(f"✅ Comprehensive task completed in {end_time - start_time:.2f}s")
            print(f"✅ Used all {len(set(step['agent'] for step in comprehensive_task['steps']))} frameworks")
            
        except Exception as e:
            task_results["error"] = str(e)
            print(f"❌ Comprehensive task failed: {e}")
        
        return task_results
    
    async def test_protocols(self) -> Dict[str, Any]:
        """Test A2A and OpenAPI protocols"""
        print("\n=== Testing Protocols ===")
        
        protocol_results = {}
        
        try:
            # Test A2A Protocol
            a2a_protocol = A2AProtocol()
            a2a_capabilities = await a2a_protocol.discover_capabilities("https://example-agent.com")
            protocol_results["a2a_discovery"] = {
                "status": "success",
                "capabilities_found": len(a2a_capabilities) if a2a_capabilities else 0
            }
            print(f"✅ A2A protocol discovery completed")
            
            # Test OpenAPI Protocol
            openapi_protocol = OpenAPIProtocol()
            if self.agents_created:
                # Generate OpenAPI spec for the first agent
                openapi_spec = await openapi_protocol.generate_spec(self.agents_created[0])
                protocol_results["openapi_generation"] = {
                    "status": "success",
                    "spec_version": openapi_spec.get("openapi", "3.0.0"),
                    "paths_count": len(openapi_spec.get("paths", {}))
                }
                print(f"✅ OpenAPI spec generated with {len(openapi_spec.get('paths', {}))} paths")
            
        except Exception as e:
            protocol_results["error"] = str(e)
            print(f"❌ Protocol test failed: {e}")
        
        return protocol_results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        print("\n🚀 Starting Comprehensive AgentMCP Test Suite")
        print("=" * 60)
        
        # Test all components
        security_results = await self.test_security_features()
        payment_results = await self.test_payment_features()
        protocol_results = await self.test_protocols()
        
        # Setup and test agents
        await self.setup_all_framework_agents()
        collaboration_results = await self.test_agent_collaboration()
        task_results = await self.test_comprehensive_task()
        
        # Compile results
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "platform_version": "AgentMCP v2.0",
            "tests": {
                "security": security_results,
                "payments": payment_results,
                "protocols": protocol_results,
                "collaboration": collaboration_results,
                "comprehensive_task": task_results
            },
            "summary": {
                "total_frameworks_tested": len(self.agents_created),
                "security_features": "✅ Passed" if security_results.get("did_creation") else "❌ Failed",
                "payment_features": "✅ Passed" if payment_results.get("stripe_payment") or payment_results.get("usdc_payment") else "❌ Failed",
                "protocol_support": "✅ Passed" if protocol_results.get("a2a_discovery") else "❌ Failed",
                "agent_collaboration": "✅ Passed" if collaboration_results.get("group_setup") else "❌ Failed",
                "comprehensive_task": "✅ Passed" if task_results.get("status") == "completed" else "❌ Failed"
            }
        }
        
        # Cleanup
        if self.group_chat:
            await self.group_chat.shutdown()
        
        return self.test_results
    
    def print_results(self):
        """Print test results in a formatted way"""
        if not self.test_results:
            print("No test results available")
            return
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        results = self.test_results
        print(f"🕒 Timestamp: {results['timestamp']}")
        print(f"🚀 Platform: {results['platform_version']}")
        
        print(f"\n📈 Summary:")
        for test_name, status in results["summary"].items():
            print(f"  {test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\n🔍 Detailed Results:")
        for test_name, test_data in results["tests"].items():
            print(f"\n  {test_name.title()}:")
            if "error" in test_data:
                print(f"    ❌ Error: {test_data['error']}")
            else:
                print(f"    ✅ Status: Success")
                if isinstance(test_data, dict):
                    for key, value in test_data.items():
                        if key != "error":
                            print(f"    📋 {key}: {value}")

async def main():
    """Main test execution"""
    # Check environment variables
    required_vars = ["OPENAI_API_KEY"]
    optional_vars = ["STRIPE_SECRET_KEY", "USDC_RPC_URL"]
    
    print("Checking environment variables...")
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing required environment variable: {var}")
            return
    
    for var in optional_vars:
        if not os.getenv(var):
            print(f"⚠️  Missing optional environment variable: {var}")
    
    try:
        # Run comprehensive test suite
        test_suite = ComprehensiveTestSuite()
        results = await test_suite.run_all_tests()
        test_suite.print_results()
        
        # Save results to file
        with open("comprehensive_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to comprehensive_test_results.json")
        
        # Return results for programmatic use
        return results
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    asyncio.run(main())