"""
Show Detailed Agent Interactions.

This script demonstrates agent interactions using the AutoGen-based implementation,
showing all the detailed conversations between agents as they collaborate on a research topic.
"""

import os
import json
import time
from typing import Dict, List, Any
import random

# Import the agent network implementation
from agent_network_example import AgentNetwork

def show_agent_interactions(topic: str):
    """
    Run a detailed agent interaction demonstration on a specific topic.
    
    This function will:
    1. Initialize the agent network
    2. Set the topic
    3. Have each specialized agent contribute to the topic
    4. Show the full interactions between agents
    5. Produce a final output combining all contributions
    
    Args:
        topic: The topic for agents to collaborate on
    """
    print(f"\n{'='*80}")
    print(f"DETAILED AGENT INTERACTION DEMO: {topic}")
    print(f"{'='*80}\n")
    
    # Create the agent network
    print("Initializing agent network...")
    network = AgentNetwork()
    network.create_network()  # Important: create the actual agents in the network
    
    # Set the collaboration topic
    print(f"\nSetting collaboration topic: {topic}")
    network.set_topic(topic)
    time.sleep(1)
    
    # Phase 1: Initial Research
    print(f"\n{'='*50}")
    print(f"PHASE 1: INITIAL RESEARCH")
    print(f"{'='*50}")
    researcher_id = "researcher"
    
    # Get researcher to investigate the topic with verbose output
    research_question = f"What is {topic} and why is it important? Provide key concepts, definitions, and components. Please be thorough in your research."
    print(f"\nMessage to Researcher: {research_question}\n")
    research_findings = network.interact_with_agent_programmatically(researcher_id, research_question)
    
    print(f"\n[RESEARCHER RESPONSE]\n{'-'*30}")
    print(research_findings)
    print(f"{'-'*30}")
    
    # Share this knowledge with the analyst
    print(f"\nSharing research findings with the Analyst...")
    network.share_knowledge(
        from_agent_id=researcher_id,
        to_agent_id="analyst",
        knowledge_key="key_concepts",
        knowledge_value=research_findings
    )
    
    # Phase 2: Analysis
    print(f"\n{'='*50}")
    print(f"PHASE 2: ANALYSIS")
    print(f"{'='*50}")
    analyst_id = "analyst"
    
    # Get analyst to evaluate with verbose output
    analysis_question = f"Based on the research about {topic}, what are the key benefits, challenges, and potential applications? Provide a detailed analysis."
    print(f"\nMessage to Analyst: {analysis_question}\n")
    analysis = network.interact_with_agent_programmatically(analyst_id, analysis_question)
    
    print(f"\n[ANALYST RESPONSE]\n{'-'*30}")
    print(analysis)
    print(f"{'-'*30}")
    
    # Share this knowledge with the planner
    print(f"\nSharing analysis with the Planner...")
    network.share_knowledge(
        from_agent_id=analyst_id,
        to_agent_id="planner",
        knowledge_key="analysis",
        knowledge_value=analysis
    )
    
    # Phase 3: Planning
    print(f"\n{'='*50}")
    print(f"PHASE 3: PLANNING")
    print(f"{'='*50}")
    planner_id = "planner"
    
    # Get planner to develop approach with verbose output
    planning_question = f"Based on the research and analysis about {topic}, create a detailed step-by-step implementation plan. Consider practical considerations and timeline."
    print(f"\nMessage to Planner: {planning_question}\n")
    plan = network.interact_with_agent_programmatically(planner_id, planning_question)
    
    print(f"\n[PLANNER RESPONSE]\n{'-'*30}")
    print(plan)
    print(f"{'-'*30}")
    
    # Share this knowledge with the creative agent
    print(f"\nSharing implementation plan with the Creative agent...")
    network.share_knowledge(
        from_agent_id=planner_id,
        to_agent_id="creative",
        knowledge_key="implementation_plan",
        knowledge_value=plan
    )
    
    # Phase 4: Creative Ideas
    print(f"\n{'='*50}")
    print(f"PHASE 4: CREATIVE IDEAS")
    print(f"{'='*50}")
    creative_id = "creative"
    
    # Get creative to generate ideas with verbose output
    creative_question = f"Based on the implementation plan for {topic}, what are some creative and innovative approaches or extensions we could consider? Think outside the box and provide detailed ideas."
    print(f"\nMessage to Creative: {creative_question}\n")
    creative_ideas = network.interact_with_agent_programmatically(creative_id, creative_question)
    
    print(f"\n[CREATIVE RESPONSE]\n{'-'*30}")
    print(creative_ideas)
    print(f"{'-'*30}")
    
    # Share these ideas with the coordinator
    print(f"\nSharing creative ideas with the Coordinator...")
    network.share_knowledge(
        from_agent_id=creative_id,
        to_agent_id="coordinator",
        knowledge_key="creative_extensions",
        knowledge_value=creative_ideas
    )
    
    # Phase 5: Coordination and Synthesis
    print(f"\n{'='*50}")
    print(f"PHASE 5: COORDINATION AND SYNTHESIS")
    print(f"{'='*50}")
    coordinator_id = "coordinator"
    
    # Get coordinator to synthesize everything with verbose output
    synthesis_question = f"Synthesize all the information shared about {topic} into a comprehensive summary including key concepts, analysis, implementation plan, and creative extensions. Provide a structured final report."
    print(f"\nMessage to Coordinator: {synthesis_question}\n")
    final_synthesis = network.interact_with_agent_programmatically(coordinator_id, synthesis_question)
    
    print(f"\n[COORDINATOR RESPONSE - FINAL SYNTHESIS]\n{'-'*30}")
    print(final_synthesis)
    print(f"{'-'*30}")
    
    # Present the final collaborative output
    print(f"\n{'='*80}")
    print(f"FINAL COLLABORATIVE OUTPUT ON: {topic}")
    print(f"{'='*80}")
    print(final_synthesis)
    print(f"\n{'='*80}")
    
    # Share the final synthesis with all agents via broadcast
    print(f"\nBroadcasting final synthesis to all agents...")
    network.broadcast_message(coordinator_id, f"Final synthesis on {topic} is complete: {final_synthesis[:100]}...")
    
    print(f"\nDetailed agent interaction demo complete!")

if __name__ == "__main__":
    # Run the interaction demo with our specific topic
    show_agent_interactions("MCP and future of agentic work")