"""
Test script for heterogeneous agents working together through the deployed server.
"""

import os
import asyncio
from agent_mcp.enhanced_mcp_agent import EnhancedMCPAgent
from agent_mcp.langchain_mcp_adapter import LangchainMCPAdapter
from agent_mcp.heterogeneous_group_chat import HeterogeneousGroupChat
import json

# Langchain imports
from langchain_openai import ChatOpenAI
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import Tool
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.schema.messages import SystemMessage
from aztp_client import Aztp
from langchain_community.tools import DuckDuckGoSearchRun

class RateLimitedDuckDuckGoSearch:
    def __init__(self, min_delay=5.0, max_retries=5):
        """Initialize with rate limiting and retry logic
        
        Args:
            min_delay: Minimum delay between requests in seconds (default: 5.0)
            max_retries: Maximum number of retry attempts (default: 5)
        """
        self.searcher = DuckDuckGoSearchRun()
        self.min_delay = max(min_delay, 5.0)  # Enforce minimum delay of 5.0 seconds
        self.max_retries = max_retries
        self.last_request_time = 0
        self.session = None
        self.base_delay = 3.0  # Increased base delay for exponential backoff

    async def search_with_retry(self, query: str) -> str:
        """Perform search with rate limiting, retries, and exponential backoff
        
        Args:
            query: Search query string
            
        Returns:
            str: Search results
            
        Raises:
            Exception: If max retries are exceeded or other errors occur
        """
        import time
        import random
        import asyncio
        from duckduckgo_search.exceptions import DuckDuckGoSearchException
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Enforce rate limiting with jitter
                now = time.time()
                time_since_last = now - self.last_request_time
                if time_since_last < self.min_delay:
                    jitter = random.uniform(0.8, 1.2)  # Increased jitter range
                    wait_time = max(0, self.min_delay - time_since_last + jitter)
                    print(f"Rate limit: Waiting {wait_time:.2f}s before search")
                    await asyncio.sleep(wait_time)
                
                # Update last request time before making the request
                self.last_request_time = time.time()
                
                # Perform the search
                result = self.searcher.run(query)
                
                # If we got here, the search was successful
                return result
                
            except Exception as e:
                last_error = e
                # Check for various rate limit indicators
                rate_limit_indicators = ["ratelimit", "429", "too many", "rate limit", "timeout"]
                if any(indicator in str(e).lower() for indicator in rate_limit_indicators):
                    backoff = min(self.base_delay * (2 ** attempt), 60)  # Increased cap to 60 seconds
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = backoff * jitter
                    
                    if attempt < self.max_retries - 1:
                        print(f"Rate limited. Retrying in {wait_time:.2f}s (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                
                # If we've reached max retries or it's not a rate limit error, raise
                if attempt == self.max_retries - 1:
                    error_msg = f"Search failed after {self.max_retries} attempts. Last error: {str(e)}"
                    print(error_msg)
                    raise Exception(error_msg)
                    
                # For other errors, use exponential backoff with jitter
                backoff = min(self.base_delay * (2 ** attempt), 60)
                jitter = random.uniform(0.8, 1.2)
                wait_time = backoff * jitter
                print(f"Error occurred. Retrying in {wait_time:.2f}s (attempt {attempt + 1}/{self.max_retries})")
                await asyncio.sleep(wait_time)

    def run(self, query: str) -> str:
        """Synchronous run method for compatibility with LangChain tools"""
        import asyncio
        return asyncio.run(self.search_with_retry(query))

async def setup_langchain_agent():
    """Setup a Langchain agent with rate-limited search capabilities"""
    # Create rate-limited search instance
    search = RateLimitedDuckDuckGoSearch(
        min_delay=3.0,  # At least 3 seconds between requests
        max_retries=3
    )
    
    search_tool = Tool(
        name="duckduckgo_search",
        description="Search the web using DuckDuckGo. Use this tool when you need to find up-to-date information. Input should be a search query.",
        func=search.run,
        coroutine=search.search_with_retry  # Enable async support
    )
    tools = [search_tool]
    
    # Create Langchain model and agent
    llm = ChatOpenAI(temperature=0)
    agent = OpenAIFunctionsAgent.from_llm_and_tools(
        llm=llm,
        tools=tools,
        system_message=SystemMessage(content=(
            "You are a research assistant that helps find and analyze information."
        ))
    )
    
    # Create the agent executor
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent, agent_executor

async def main():
    #the idea here is agent in a group working with each other regardless of the framework they were built on
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable")
    
    # Create a group chat
    group = HeterogeneousGroupChat(
        name="TechResearch",
        server_url="https://mcp-server-ixlfhxquwq-ew.a.run.app"
    )
    
    print("\n=== Creating Coordinator ===")
    # Create and initialize coordinator
    coordinator = group.create_coordinator(api_key=api_key)
    print(f"Coordinator created with name: {coordinator.name}")
    
    # Verify coordinator transport
    if not coordinator.transport:
        raise ValueError("Coordinator transport not initialized")
    print(f"Coordinator transport initialized with URL: {coordinator.transport.get_url()}")
    
    print("\n=== Creating Agents ===")
    # Create an Autogen-based researcher
    researcher = EnhancedMCPAgent(
        name="Researcher",
        system_message="""You are a technology researcher specializing in AI and quantum computing.
        Your role is to analyze topics and provide detailed, technical insights.""",
        llm_config={
            "config_list": [{
                "model": "gpt-3.5-turbo",
                "api_key": api_key
            }]
        }
    )
    
    # Create a Langchain-based analyst with search capabilities
    print("Setting up Langchain agent...")
    langchain_agent, agent_executor = await setup_langchain_agent()
    analyst = LangchainMCPAdapter(
        name="Analyst",
        langchain_agent=langchain_agent,
        agent_executor=agent_executor,
        system_message="""I am a market research analyst specializing in technology trends.
        I use web search to find current market data and analyze industry developments."""
    )
    
    # Add both agents to the group
    print("Adding agents to group...")
    group.add_agents([researcher, analyst])
    
    print("\n=== Creating Proxy Agent ===")
    
    # Create and add proxy for EmailAgent
    from agent_mcp.proxy_agent import ProxyAgent
    # Create and add proxy for Influencer
    influencer_proxy = ProxyAgent(name="Influenxers", client_mode=True)
    await influencer_proxy.connect_to_remote_agent("Influenxers", group.server_url) #Influenxers is the id to Amrit's inflencer agent  
    
    # Create a secure agent
    # TODO: come back to do secure connections
    #client = Aztp(api_key=os.getenv("AZTP_API_KEY"))
    #influencer_proxy = await client.secure_connect(influencer_proxy, name="Influencer", config={"isGlobalIdentity": True})

    # Verify identity
    #is_valid = await client.verify_identity(influencer_proxy)
    #print(f"Influencer identity is valid: {is_valid}")
    
    # Get identity details
    #identity = await client.get_identity(influencer_proxy)
    #print(f"Influencer identity: {identity}")
    
    group.add_agent(influencer_proxy)

    # Create and add proxy for EmailAgent
    email_proxy = ProxyAgent(name="EmailProxy", client_mode=True) 
    await email_proxy.connect_to_remote_agent("EmailAgent", group.server_url)
    group.add_agent(email_proxy)
    
    # Connect everyone to the deployed server
    print("\n=== Connecting to Deployed Server ===")
    try:
        await group.connect()
        print("Successfully connected to server")
        
        # Verify all agents are connected
        for agent in group.agents:
            if not agent.transport or not agent.transport.token:
                raise ValueError(f"Agent {agent.name} not properly connected")
            print(f"Agent {agent.name} connected with token: {agent.transport.token[:8]}...")
            
        # Verify coordinator connection
        if not group.coordinator or not group.coordinator.transport.token:
            raise ValueError("Coordinator not properly connected")
        print(f"Coordinator connected with token: {group.coordinator.transport.token[:8]}...")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        raise
    
    # Define a collaborative task
    task = {
        "task_id": "balm_pcos_cure_research",
        "steps": [
            {
                "task_id": "initial_research",
                "agent": "Researcher",
                "description": """Research the intersection of AI Agents and PCOS cure.
                Focus on: 
                1. Recent breakthroughs in using AI Agents and PCOS cure
                2. Potential applications in real-world scenarios
                3. Current limitations and challenges"""
            },
            {
                "task_id": "market_analysis",
                "agent": "Analyst",
                "description": """Using the research findings, analyze:
                1. Current market potential, size and potential adoption of cure for PCOS using AI Agents
                2. Major companies and research institutions involved
                3. Future market potential and timeline
                Use your search capabilities to find supporting data.""",
                "depends_on": ["initial_research"]
            },
             {
                "task_id": "social_influencer_campaign_strategy",
                "agent": "Influenxers", 
                "description": 
                    "Using the market analysis, assuming a business is interested in quantum ML, develop a social influencer campaign strategy:\n"
                    "- Identify the best channels (TikTok, Instagram, YouTube)\n"
                    "- Suggest 3 micro-influencer profiles\n"
                    "- Outline KPIs and targeting\n"
                    "- Provide a 4-week rollout plan"
                ,
                "depends_on": ["market_analysis"]
            },
            {
                "task_id": "send_report",
                "agent": "EmailAgent",
                "description": """
                Come up with a comprehensive report from the research and also the social influencer campaign strategy and key findings.
                Send an email to nonye@balm.ai with the subject "AI Agents and PCOS cure Research Report"
                with the report as the body of the email.
                
                The email should be professional and include:
                  1. A comprehensive and detailed outline, including all the points from the research from the previous steps
                  2. A brief introduction to the campaign
                  3. Key findings from the market analysis
                  4. The proposed influencer strategy
                  5. Expected outcomes and KPIs
                
                the signature should be:
                
                Best regards,
                Samuel Ekpe
                """,
                "content": {
                    "email_params": {
                        "to_address": "samuel@grupa.ai",
                        "subject": "AI Agents and PCOS cure Research Report"
                    }, 
                    "generate_content": True
                },
                "depends_on": ["social_influencer_campaign_strategy"]
            }
        ]
    }
    
    # Submit the task and wait for completion
    print("\n=== Submitting Task ===")
    print("***** REACHED POINT BEFORE group.submit_task *****", flush=True)
    
    # Verify task structure before submission
    print(f"Task structure: {json.dumps(task, indent=2)}")
    print(f"Active agents: {[agent.name for agent in group.agents]}")

    # Submit all steps at once and let the group chat handle dependency injection at the right time
    await group.submit_task(task)
    await group.wait_for_completion()
    
    print("\n=== Task Complete ===\n")

    print("Shutting down agents...")
    await group.shutdown()
    print("All agents shut down successfully")

if __name__ == "__main__":
    asyncio.run(main())
