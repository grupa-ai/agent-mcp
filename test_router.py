"""
Test the modified autonomous_langgraph_network to verify the router is working.

This simpler test just creates a modified version of the research_topic function
that prints the result of each invoke call to check the format of the returns.
"""

from autonomous_langgraph_network import AutonomousAgentNetwork
from langchain_core.messages import HumanMessage, AIMessage

def test_network():
    """Test the network's collaboration graph and routers."""
    # Initialize the network
    print("Initializing the autonomous agent network...")
    network = AutonomousAgentNetwork()
    network.create_network()
    
    # Create a simple test function that mimics research_topic but just runs one step
    def test_one_step():
        """Run just one step of the collaboration and print the result."""
        print("\nTesting collaboration graph with a simple message...")
        
        # Create a test message
        initial_message = HumanMessage(content="Can you help me research artificial intelligence ethics?")
        messages = [initial_message]
        
        # Run one step and print the result structure
        result = network.collaboration_graph.invoke({"messages": messages})
        print(f"Result type: {type(result)}")
        print(f"Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
        
        # If we have messages in the result, print the last one
        if isinstance(result, dict) and "messages" in result:
            print("\nLast message:")
            print(result["messages"][-1].content[:200] + "..." if len(result["messages"][-1].content) > 200 else result["messages"][-1].content)
        
        print("\nTest complete!")
    
    # Run the test
    test_one_step()

if __name__ == "__main__":
    test_network()