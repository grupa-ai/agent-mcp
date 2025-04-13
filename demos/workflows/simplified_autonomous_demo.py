"""
Simplified autonomous agent collaboration demonstration
"""

from demos.langgraph.autonomous_langgraph_network import AutonomousAgentNetwork
import sys
import time

def main():
    """Run a simplified autonomous collaboration demo"""
    print(f"\n{'='*80}")
    print(f"SIMPLIFIED AUTONOMOUS AGENT COLLABORATION DEMO")
    print(f"{'='*80}\n")
    
    # Get topic from command line or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "Future of remote work"
    
    print(f"Research topic: {topic}")
    print(f"{'='*40}")
    
    # Create the autonomous agent network
    print("Creating autonomous agent network...")
    network = AutonomousAgentNetwork()
    network.create_network()
    
    # Initialize the shared workspace
    print("\nInitial workspace state:")
    network.show_workspace()
    
    # Set up a minimal autonomous collaboration
    # We'll manually introduce messages between agents to see how they route
    print("\nStarting autonomous collaboration...")
    
    # Start with coordinator introducing the topic
    coordinator_message = f"""
    I need the team to collaboratively research the topic: "{topic}"
    
    Each agent should contribute based on their specialty.
    """
    
    # Add initial message as if from "user"
    initial_messages = [{"role": "user", "content": coordinator_message}]
    
    # Set up research topic in context
    network.context.set("research_topic", {
        "title": topic, 
        "started_at": time.time()
    })
    
    # Create the initial message for the coordinator
    initial_message = {
        "role": "user", 
        "content": f"I need your help researching the topic: '{topic}'. Please work with the other agents to explore this topic collaboratively."
    }
    
    # Run a few steps of autonomous collaboration
    print("\nStarting autonomous collaboration with 5 max steps...")
    
    # Use the research_topic method with a limited number of steps
    network.research_topic(topic, max_steps=5)
    
    # Show the final workspace state
    print("\nFinal workspace state after collaboration:")
    network.show_workspace()
    
    print(f"\n{'='*80}")
    print(f"AUTONOMOUS COLLABORATION DEMO COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()