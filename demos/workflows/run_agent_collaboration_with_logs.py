"""
Agent Collaboration with Detailed Interaction Logs

This script demonstrates agents collaborating and shows the detailed logs
of how they communicate with each other via the MCP protocol.
"""

import os
import json
import time
from typing import Dict, List, Any
import pprint

# Import the agent network implementation
from demos.network.agent_network_example import AgentNetwork
from agent_mcp.mcp_agent import MCPAgent  # Import the MCPAgent directly to access logs

# Enable verbose logging for all tool calls
os.environ["AUTOGEN_VERBOSE"] = "1"

def run_agent_collaboration_with_logs(topic: str):
    """
    Run a collaborative research process with detailed logs of agent interactions.
    
    This function will:
    1. Initialize the agent network
    2. Set the topic
    3. Show every interaction between agents
    4. Display tool calls between agents
    
    Args:
        topic: The topic for agents to collaborate on
    """
    print(f"\n{'='*80}")
    print(f"AGENT COLLABORATION WITH DETAILED LOGS: {topic}")
    print(f"{'='*80}\n")
    
    # Create the agent network
    print("Initializing agent network...")
    network = AgentNetwork()
    network.create_network()
    
    # Enable more verbose logging on all agents to see interactions
    for agent_id, agent in network.agents.items():
        # Enable tool call logging
        agent.init_log_file = f"{agent_id}_interactions.log"
        agent.verbose = True
    
    # Set the collaboration topic
    print(f"\nSetting collaboration topic: {topic}")
    network.set_topic(topic)
    time.sleep(1)
    
    # Store full logs of interactions
    interactions = []
    
    # Step 1: Researcher investigates the topic
    researcher_id = "researcher"
    print(f"\n[STEP 1] RESEARCHER INVESTIGATION")
    print(f"{'-'*60}")
    
    # Record pre-interaction state
    print(f"Researcher context before interaction:")
    researcher_context = network.agents[researcher_id].shared_context.get_all_context() if hasattr(network.agents[researcher_id], 'shared_context') else {}
    pprint.pprint(researcher_context)
    
    # Ask researcher about the topic
    research_question = f"What is {topic} and why is it important? Provide key concepts and components."
    print(f"\nQuestion to researcher: {research_question}\n")
    
    # Make the call and capture the response
    research_findings = network.interact_with_agent_programmatically(researcher_id, research_question)
    
    # Record the interaction
    interactions.append({
        "step": 1,
        "from": "user",
        "to": researcher_id,
        "message": research_question,
        "response": research_findings
    })
    
    print(f"\nResearcher's response:")
    print(f"{'-'*40}")
    print(research_findings)
    print(f"{'-'*40}")
    
    # Share knowledge with the analyst via tool call
    print(f"\nSharing research findings with the analyst...")
    knowledge_key = "key_concepts"
    
    # Show the tool call details
    print(f"Tool call details:")
    print(f"- Tool: share_knowledge")
    print(f"- From: {researcher_id}")
    print(f"- To: analyst")
    print(f"- Key: {knowledge_key}")
    print(f"- Value: [Research findings]")
    
    # Make the actual tool call
    network.share_knowledge(
        from_agent_id=researcher_id,
        to_agent_id="analyst",
        knowledge_key=knowledge_key,
        knowledge_value=research_findings
    )
    
    # Record the interaction
    interactions.append({
        "step": "1a",
        "from": researcher_id,
        "to": "analyst",
        "tool": "share_knowledge",
        "key": knowledge_key,
        "value_summary": "Research findings on " + topic
    })
    
    # Show the analyst's context after receiving the knowledge
    print(f"\nAnalyst context after receiving research:")
    analyst_context = network.agents["analyst"].shared_context.get_all_context() if hasattr(network.agents["analyst"], 'shared_context') else {}
    if knowledge_key in analyst_context:
        print(f"- Successfully received '{knowledge_key}' from researcher")
    else:
        print(f"- Failed to receive '{knowledge_key}' from researcher")
    
    # Step 2: Analyst evaluates the research findings
    analyst_id = "analyst"
    print(f"\n[STEP 2] ANALYST EVALUATION")
    print(f"{'-'*60}")
    
    # Ask analyst to analyze the research
    analysis_question = f"Based on the research about {topic}, what are the key benefits, challenges, and potential applications?"
    print(f"\nQuestion to analyst: {analysis_question}\n")
    
    # Make the call and capture the response
    analysis = network.interact_with_agent_programmatically(analyst_id, analysis_question)
    
    # Record the interaction
    interactions.append({
        "step": 2,
        "from": "user",
        "to": analyst_id,
        "message": analysis_question,
        "response": analysis
    })
    
    print(f"\nAnalyst's response:")
    print(f"{'-'*40}")
    print(analysis)
    print(f"{'-'*40}")
    
    # Share this knowledge with the planner via tool call
    print(f"\nSharing analysis with the planner...")
    knowledge_key = "analysis"
    
    # Show the tool call details
    print(f"Tool call details:")
    print(f"- Tool: share_knowledge")
    print(f"- From: {analyst_id}")
    print(f"- To: planner")
    print(f"- Key: {knowledge_key}")
    print(f"- Value: [Analysis content]")
    
    # Make the actual tool call
    network.share_knowledge(
        from_agent_id=analyst_id,
        to_agent_id="planner",
        knowledge_key=knowledge_key,
        knowledge_value=analysis
    )
    
    # Record the interaction
    interactions.append({
        "step": "2a",
        "from": analyst_id,
        "to": "planner",
        "tool": "share_knowledge",
        "key": knowledge_key,
        "value_summary": "Analysis of benefits, challenges, and applications"
    })
    
    # Show the planner's context after receiving the knowledge
    print(f"\nPlanner context after receiving analysis:")
    planner_context = network.agents["planner"].shared_context.get_all_context() if hasattr(network.agents["planner"], 'shared_context') else {}
    if knowledge_key in planner_context:
        print(f"- Successfully received '{knowledge_key}' from analyst")
    else:
        print(f"- Failed to receive '{knowledge_key}' from analyst")
    
    # Step 3: Planner develops an implementation approach
    planner_id = "planner"
    print(f"\n[STEP 3] PLANNER IMPLEMENTATION STRATEGY")
    print(f"{'-'*60}")
    
    # Ask planner to create an implementation plan
    planning_question = f"Based on the research and analysis about {topic}, create a step-by-step implementation plan."
    print(f"\nQuestion to planner: {planning_question}\n")
    
    # Make the call and capture the response
    plan = network.interact_with_agent_programmatically(planner_id, planning_question)
    
    # Record the interaction
    interactions.append({
        "step": 3,
        "from": "user",
        "to": planner_id,
        "message": planning_question,
        "response": plan
    })
    
    print(f"\nPlanner's response:")
    print(f"{'-'*40}")
    print(plan)
    print(f"{'-'*40}")
    
    # Share this knowledge with the creative agent via tool call
    print(f"\nSharing implementation plan with the creative agent...")
    knowledge_key = "implementation_plan"
    
    # Show the tool call details
    print(f"Tool call details:")
    print(f"- Tool: share_knowledge")
    print(f"- From: {planner_id}")
    print(f"- To: creative")
    print(f"- Key: {knowledge_key}")
    print(f"- Value: [Implementation plan content]")
    
    # Make the actual tool call
    network.share_knowledge(
        from_agent_id=planner_id,
        to_agent_id="creative",
        knowledge_key=knowledge_key,
        knowledge_value=plan
    )
    
    # Record the interaction
    interactions.append({
        "step": "3a",
        "from": planner_id,
        "to": "creative",
        "tool": "share_knowledge",
        "key": knowledge_key,
        "value_summary": "Step-by-step implementation plan"
    })
    
    # Show the creative's context after receiving the knowledge
    print(f"\nCreative context after receiving implementation plan:")
    creative_context = network.agents["creative"].shared_context.get_all_context() if hasattr(network.agents["creative"], 'shared_context') else {}
    if knowledge_key in creative_context:
        print(f"- Successfully received '{knowledge_key}' from planner")
    else:
        print(f"- Failed to receive '{knowledge_key}' from planner")
    
    # Step 4: Creative comes up with innovative ideas
    creative_id = "creative"
    print(f"\n[STEP 4] CREATIVE INNOVATION")
    print(f"{'-'*60}")
    
    # Ask creative to generate innovative ideas
    creative_question = f"Based on the implementation plan for {topic}, what are some creative and innovative approaches or extensions we could consider?"
    print(f"\nQuestion to creative: {creative_question}\n")
    
    # Make the call and capture the response
    creative_ideas = network.interact_with_agent_programmatically(creative_id, creative_question)
    
    # Record the interaction
    interactions.append({
        "step": 4,
        "from": "user",
        "to": creative_id,
        "message": creative_question,
        "response": creative_ideas
    })
    
    print(f"\nCreative's response:")
    print(f"{'-'*40}")
    print(creative_ideas)
    print(f"{'-'*40}")
    
    # Share these ideas with the coordinator via tool call
    print(f"\nSharing creative ideas with the coordinator...")
    knowledge_key = "creative_extensions"
    
    # Show the tool call details
    print(f"Tool call details:")
    print(f"- Tool: share_knowledge")
    print(f"- From: {creative_id}")
    print(f"- To: coordinator")
    print(f"- Key: {knowledge_key}")
    print(f"- Value: [Creative ideas content]")
    
    # Make the actual tool call
    network.share_knowledge(
        from_agent_id=creative_id,
        to_agent_id="coordinator",
        knowledge_key=knowledge_key,
        knowledge_value=creative_ideas
    )
    
    # Record the interaction
    interactions.append({
        "step": "4a",
        "from": creative_id,
        "to": "coordinator",
        "tool": "share_knowledge",
        "key": knowledge_key,
        "value_summary": "Creative and innovative approaches"
    })
    
    # Show the coordinator's context after receiving the knowledge
    print(f"\nCoordinator context after receiving creative ideas:")
    coordinator_context = network.agents["coordinator"].shared_context.get_all_context() if hasattr(network.agents["coordinator"], 'shared_context') else {}
    if knowledge_key in coordinator_context:
        print(f"- Successfully received '{knowledge_key}' from creative")
    else:
        print(f"- Failed to receive '{knowledge_key}' from creative")
    
    # Step 5: Coordinator synthesizes everything
    coordinator_id = "coordinator"
    print(f"\n[STEP 5] COORDINATOR SYNTHESIS")
    print(f"{'-'*60}")
    
    # Verify coordinator has access to all knowledge
    print(f"Checking coordinator's accumulated knowledge:")
    coordinator_keys = list(network.agents[coordinator_id].shared_context.get_all_context().keys()) if hasattr(network.agents[coordinator_id], 'shared_context') else []
    print(f"Available knowledge keys: {coordinator_keys}")
    
    # Ask coordinator to synthesize all information
    synthesis_question = f"Synthesize all the information shared about {topic} into a comprehensive summary including key concepts, analysis, implementation plan, and creative extensions."
    print(f"\nQuestion to coordinator: {synthesis_question}\n")
    
    # Make the call and capture the response
    final_synthesis = network.interact_with_agent_programmatically(coordinator_id, synthesis_question)
    
    # Record the interaction
    interactions.append({
        "step": 5,
        "from": "user",
        "to": coordinator_id,
        "message": synthesis_question,
        "response": final_synthesis
    })
    
    print(f"\nCoordinator's response (final synthesis):")
    print(f"{'-'*40}")
    print(final_synthesis)
    print(f"{'-'*40}")
    
    # Broadcast final synthesis to all agents
    print(f"\nBroadcasting final synthesis to all agents...")
    broadcast_message = f"Final synthesis on {topic} is complete. Thank you all for your contributions!"
    
    # Show the tool call details
    print(f"Tool call details:")
    print(f"- Tool: broadcast_message")
    print(f"- From: {coordinator_id}")
    print(f"- Message: '{broadcast_message}'")
    
    # Make the actual tool call
    network.broadcast_message(coordinator_id, broadcast_message)
    
    # Record the interaction
    interactions.append({
        "step": "5a",
        "from": coordinator_id,
        "to": "all agents",
        "tool": "broadcast_message",
        "message": broadcast_message
    })
    
    # Present the final collaborative output
    print(f"\n{'='*80}")
    print(f"FINAL COLLABORATIVE OUTPUT ON: {topic}")
    print(f"{'='*80}\n")
    print(final_synthesis)
    print(f"\n{'='*80}")
    
    # Show the full interaction graph
    print(f"\n{'='*80}")
    print(f"AGENT INTERACTION SUMMARY")
    print(f"{'='*80}")
    for interaction in interactions:
        if "tool" in interaction:
            print(f"[Step {interaction['step']}] {interaction['from']} → {interaction['to']} "
                  f"(via {interaction['tool']}): {interaction.get('key', interaction.get('message', ''))}")
        else:
            print(f"[Step {interaction['step']}] {interaction['from']} → {interaction['to']}: "
                  f"{interaction['message'][:50]}..." if len(interaction['message']) > 50 else interaction['message'])
    
    print(f"\nCollaboration demo with detailed logs complete!")
    return final_synthesis


if __name__ == "__main__":
    # Run the interaction with our specific topic
    run_agent_collaboration_with_logs("MCP and future of agentic work")