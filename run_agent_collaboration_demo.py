"""
Agent Collaboration Demo

This script demonstrates agents collaborating and executing on a topic without requiring
manual interaction. It automates a flow between agents in a network to solve a problem
or address a topic together.
"""

import os
import json
import time
from typing import Dict, List, Any

# Import the agent network implementation
from agent_network_example import AgentNetwork


def run_collaboration_demo(topic: str):
    """
    Run a complete collaboration demonstration on a specific topic.
    
    This function will:
    1. Initialize the agent network
    2. Set the topic
    3. Have each specialized agent contribute to the topic
    4. Show how agents can build on each other's knowledge
    5. Produce a final output combining all contributions
    
    Args:
        topic: The topic for agents to collaborate on
    """
    print(f"\n{'='*50}")
    print(f"AGENT COLLABORATION DEMO: {topic}")
    print(f"{'='*50}\n")
    
    # Create the agent network
    print("Initializing agent network...")
    network = AgentNetwork()
    network.create_network()  # Important: create the actual agents in the network
    
    # Set the collaboration topic
    print(f"\nSetting collaboration topic: {topic}")
    network.set_topic(topic)
    time.sleep(1)
    
    # Record all the knowledge that gets shared
    knowledge_record = {}
    
    # Step 1: Researcher investigates the topic
    researcher_id = "researcher"
    print(f"\n[STEP 1] {researcher_id.upper()} is researching the topic")
    
    # Simulate the researcher doing research
    research_question = f"What is {topic} and why is it important? Provide key concepts and components."
    research_findings = network.interact_with_agent_programmatically(researcher_id, research_question)
    
    # Save the research findings to our knowledge base
    knowledge_key = "key_concepts"
    knowledge_record[knowledge_key] = research_findings
    
    # Share this knowledge with the network
    print(f"\nSharing research findings with the network...")
    network.share_knowledge(
        from_agent_id=researcher_id,
        to_agent_id="analyst",
        knowledge_key=knowledge_key,
        knowledge_value=research_findings
    )
    time.sleep(1)
    
    # Step 2: Analyst evaluates the research findings
    analyst_id = "analyst"
    print(f"\n[STEP 2] {analyst_id.upper()} is analyzing the research findings")
    
    analysis_question = f"Based on the research about {topic}, what are the key benefits, challenges, and potential applications?"
    analysis = network.interact_with_agent_programmatically(analyst_id, analysis_question)
    
    # Save the analysis to our knowledge base
    knowledge_key = "analysis"
    knowledge_record[knowledge_key] = analysis
    
    # Share this knowledge with the network
    print(f"\nSharing analysis with the network...")
    network.share_knowledge(
        from_agent_id=analyst_id,
        to_agent_id="planner",
        knowledge_key=knowledge_key,
        knowledge_value=analysis
    )
    time.sleep(1)
    
    # Step 3: Planner develops an implementation approach
    planner_id = "planner"
    print(f"\n[STEP 3] {planner_id.upper()} is creating an implementation plan")
    
    planning_question = f"Based on the research and analysis about {topic}, create a step-by-step implementation plan."
    plan = network.interact_with_agent_programmatically(planner_id, planning_question)
    
    # Save the plan to our knowledge base
    knowledge_key = "implementation_plan"
    knowledge_record[knowledge_key] = plan
    
    # Share this knowledge with the network
    print(f"\nSharing implementation plan with the network...")
    network.share_knowledge(
        from_agent_id=planner_id,
        to_agent_id="creative",
        knowledge_key=knowledge_key,
        knowledge_value=plan
    )
    time.sleep(1)
    
    # Step 4: Creative comes up with innovative ideas
    creative_id = "creative"
    print(f"\n[STEP 4] {creative_id.upper()} is generating innovative ideas")
    
    creative_question = f"Based on the implementation plan for {topic}, what are some creative and innovative approaches or extensions we could consider?"
    creative_ideas = network.interact_with_agent_programmatically(creative_id, creative_question)
    
    # Save the creative ideas to our knowledge base
    knowledge_key = "creative_extensions"
    knowledge_record[knowledge_key] = creative_ideas
    
    # Share these ideas with the network
    print(f"\nSharing creative ideas with the network...")
    network.share_knowledge(
        from_agent_id=creative_id,
        to_agent_id="coordinator",
        knowledge_key=knowledge_key,
        knowledge_value=creative_ideas
    )
    time.sleep(1)
    
    # Step 5: Coordinator synthesizes everything
    coordinator_id = "coordinator"
    print(f"\n[STEP 5] {coordinator_id.upper()} is synthesizing all contributions")
    
    synthesis_question = f"Synthesize all the information shared about {topic} into a comprehensive summary including key concepts, analysis, implementation plan, and creative extensions."
    final_synthesis = network.interact_with_agent_programmatically(coordinator_id, synthesis_question)
    
    # Present the final collaborative output
    print(f"\n{'='*50}")
    print(f"FINAL COLLABORATIVE OUTPUT ON: {topic}")
    print(f"{'='*50}\n")
    print(final_synthesis)
    print(f"\n{'='*50}")
    
    # Share the final synthesis with all agents via broadcast
    print(f"\nBroadcasting final synthesis to all agents...")
    network.broadcast_message(coordinator_id, f"Final synthesis on {topic} is complete: {final_synthesis[:100]}...")
    
    print(f"\nCollaboration demo complete!")
    return knowledge_record


def main():
    """Run the agent collaboration demonstration."""
    # Topics that would demonstrate collaboration well
    topics = [
        "Model Context Protocol for AI Assistants",
        "Building a Multi-Agent System for Customer Support",
        "Implementing a Collaborative Research Platform"
    ]
    
    # Ask the user to select a topic or provide their own
    print("Agent Collaboration Demo")
    print("This will demonstrate how agents can work together on a shared topic.")
    print("\nAvailable Topics:")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")
    print(f"{len(topics) + 1}. Custom topic")
    
    while True:
        try:
            choice = input("\nSelect a topic number or enter 'custom' to provide your own: ")
            if choice.lower() == 'custom':
                custom_topic = input("Enter your custom topic: ")
                selected_topic = custom_topic
                break
            choice = int(choice)
            if 1 <= choice <= len(topics):
                selected_topic = topics[choice - 1]
                break
            elif choice == len(topics) + 1:
                custom_topic = input("Enter your custom topic: ")
                selected_topic = custom_topic
                break
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a valid number or 'custom'.")
    
    # Run the collaboration demonstration
    run_collaboration_demo(selected_topic)


if __name__ == "__main__":
    # When started directly, run with a specific topic without prompting
    run_collaboration_demo("MCP and future of agentic work")