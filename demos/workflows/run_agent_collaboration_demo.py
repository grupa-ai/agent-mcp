"""
Autonomous Agent Collaboration Demo

This script demonstrates how agents can autonomously collaborate on a topic without
hardcoded interaction patterns. The user only provides the topic, and the agents
decide for themselves who to collaborate with and in what order.
"""

from demos.langgraph.autonomous_langgraph_network import AutonomousAgentNetwork
import sys
import time

def run_autonomous_collaboration(topic):
    """
    Run an autonomous collaborative research process on a given topic.
    
    Args:
        topic: The topic for the agents to research and collaborate on
    """
    print(f"\n{'='*80}")
    print(f"AUTONOMOUS AGENT COLLABORATION: {topic}")
    print(f"{'='*80}\n")
    
    # Create the autonomous agent network
    print("Initializing autonomous agent network...")
    network = AutonomousAgentNetwork()
    network.create_network()
    print("Network created with autonomous decision-making capabilities")
    
    print(f"\nStarting collaborative research on: {topic}")
    print(f"{'='*40}")
    print("Each agent will autonomously decide which other agents to collaborate with.")
    print("Agents will share information through the workspace without predefined patterns.")
    print(f"{'='*40}\n")
    
    # Start the autonomous research process with a maximum number of steps
    max_steps = 10
    print(f"Beginning research (max {max_steps} interaction steps)...")
    
    # Run the autonomous research
    results = network.research_topic(topic, max_steps=max_steps)
    
    # Show the final state of the workspace
    print("\nFinal Shared Workspace State:")
    network.show_workspace()
    
    print(f"\n{'='*80}")
    print(f"RESEARCH COMPLETE")
    print(f"{'='*80}\n")
    return results

if __name__ == "__main__":
    # If a topic is provided as a command line argument, use that
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        # Otherwise use a default topic or ask for input
        topic = input("Enter a research topic for autonomous agent collaboration: ")
    
    if not topic:
        topic = "The future of autonomous AI agents in business"
    
    run_autonomous_collaboration(topic)