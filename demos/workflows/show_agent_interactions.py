"""
Show Agent Interactions

This script demonstrates a simplified version of agent interactions,
making it clear how agents communicate with each other using MCP protocol
"""

import os
import time
from demos.network.agent_network_example import AgentNetwork

# Enable verbose logging for all agent interactions
os.environ["AUTOGEN_VERBOSE"] = "1"

def main():
    """Run a simplified agent interaction demo with clear visualization of messages."""
    print("\n=== AGENT INTERACTIONS DEMONSTRATION ===\n")
    
    # Create the agent network
    print("1. Creating agent network with specialized agents...")
    network = AgentNetwork()
    network.create_network()
    print(f"   Network created with {len(network.agents)} agents:")
    for agent_id, agent in network.agents.items():
        print(f"   - {agent.name} ({agent_id})")
    
    # Set a topic for discussion
    topic = "MCP and future of agentic work"
    print(f"\n2. Setting collaboration topic: {topic}")
    network.set_topic(topic)
    
    # STEP 1: Direct agent-to-agent communication
    print("\n3. DEMONSTRATING DIRECT AGENT COMMUNICATION")
    print("   Researcher -> Analyst")
    print("   ----------------------------------------")
    
    # Researcher discovers information
    research_question = f"What is {topic} and why is it important? Provide key concepts."
    print(f"   Question to researcher: {research_question}")
    research_findings = network.interact_with_agent_programmatically("researcher", research_question)
    print(f"   Researcher's response: '{research_findings[:100]}...'")
    
    # Researcher shares with analyst
    print(f"\n   Sharing knowledge from Researcher to Analyst...")
    network.share_knowledge(
        from_agent_id="researcher",
        to_agent_id="analyst",
        knowledge_key="research_findings",
        knowledge_value=research_findings
    )
    print(f"   ✓ Knowledge shared successfully")
    
    # STEP 2: Tool-based communication
    print("\n4. DEMONSTRATING TOOL-BASED COMMUNICATION")
    print("   Analyst calls Planner as a tool")
    print("   ----------------------------------------")
    
    # Analyst uses the planner as a tool
    analysis_request = f"Based on this research, create a short analysis of {topic} highlighting benefits and challenges."
    print(f"   Request to analyst: {analysis_request}")
    analyst_response = network.interact_with_agent_programmatically("analyst", analysis_request)
    print(f"   Analyst's response (which includes calling the planner as a tool): '{analyst_response[:100]}...'")
    
    # STEP 3: Multi-agent coordination
    print("\n5. DEMONSTRATING MULTI-AGENT COORDINATION")
    print("   Coordinator broadcasts to all agents")
    print("   ----------------------------------------")
    
    # Coordinator broadcasts to all agents
    coordinator_message = f"Team, I need everyone's input on {topic}. Please share your specialized perspectives."
    print(f"   Broadcast message: {coordinator_message}")
    network.broadcast_message("coordinator", coordinator_message)
    print(f"   ✓ Message broadcast to all agents in the network")
    
    # STEP 4: Context sharing
    print("\n6. DEMONSTRATING CONTEXT SHARING")
    print("   Agents update and access shared context")
    print("   ----------------------------------------")
    
    # Planner updates the shared workspace with a plan
    planning_request = f"Create a simple implementation plan for {topic}"
    print(f"   Request to planner: {planning_request}")
    plan = network.interact_with_agent_programmatically("planner", planning_request)
    print(f"   Planner's response: '{plan[:100]}...'")
    
    # Creative accesses the plan and builds upon it
    creative_request = f"Based on the existing plan, suggest innovative extensions for {topic}"
    print(f"   Request to creative: {creative_request}")
    creative_response = network.interact_with_agent_programmatically("creative", creative_request)
    print(f"   Creative's response (building on shared context): '{creative_response[:100]}...'")
    
    # Show network context
    print("\n=== AGENT NETWORK COLLABORATION SUMMARY ===")
    print("During this demonstration:")
    print("1. The Researcher investigated the topic and shared findings with the Analyst")
    print("2. The Analyst evaluated the research, calling the Planner as a tool for help")
    print("3. The Coordinator broadcast a message to all agents in the network")
    print("4. The Planner created an implementation plan stored in shared context")
    print("5. The Creative accessed the shared context to build upon the plan")
    print("\nThis demonstrates how agents collaborate through:")
    print("- Direct knowledge sharing (agent to agent)")
    print("- Tool-based communication (using other agents as tools)")
    print("- Broadcasting (one to many communication)")
    print("- Context sharing (maintaining shared knowledge state)")

if __name__ == "__main__":
    main()