"""
Run LangGraph examples with pre-defined inputs to demonstrate a real use case.
"""

import time
import subprocess
import langgraph_agent_network
import langgraph_collaborative_task

def run_agent_network_scenario():
    """Run a real-world scenario with the agent network."""
    print("\n=== RUNNING AGENT NETWORK SCENARIO ===")
    print("This scenario demonstrates how different agents can collaborate on an AI assistant project.")
    
    # Create the network manually with our test case
    network = langgraph_agent_network.LangGraphAgentNetwork()
    network.create_network()
    
    # Set a specific topic related to AI assistants
    print("\n1. Setting the topic to 'AI Assistant Development with MCP'")
    network.set_topic("AI Assistant Development with MCP")
    time.sleep(1)
    
    # Show the workspace to see how it's initialized
    print("\n2. Examining the initial workspace")
    network.show_workspace()
    time.sleep(1)
    
    # First, let's ask the researcher to find information about MCP
    print("\n3. Asking the Researcher about MCP")
    agent_id = "researcher"
    query = "What is the Model Context Protocol and why is it important for AI assistants?"
    print(f"\nUser query to {agent_id}: {query}")
    
    # Interact with the researcher (simulate interaction)
    response = network.agents[agent_id].generate_reply(
        messages=[{"role": "user", "content": query}]
    )
    print(f"\nResponse from {agent_id}:\n{response}")
    
    # Add this information to the shared workspace
    network.update_workspace(
        section="research",
        key="mcp_definition",
        value=response,
        from_agent=agent_id
    )
    time.sleep(1)
    
    # Now, let's ask the analyst to analyze the implications
    print("\n4. Asking the Analyst to analyze the implications")
    agent_id = "analyst"
    query = "Based on the research about MCP, what are the key benefits and challenges for AI assistants?"
    print(f"\nUser query to {agent_id}: {query}")
    
    # Interact with the analyst
    response = network.agents[agent_id].generate_reply(
        messages=[{"role": "user", "content": query}]
    )
    print(f"\nResponse from {agent_id}:\n{response}")
    
    # Add this analysis to the workspace
    network.update_workspace(
        section="analysis",
        key="mcp_implications",
        value=response,
        from_agent=agent_id
    )
    time.sleep(1)
    
    # Finally, let's have the planner create a roadmap
    print("\n5. Asking the Planner to create an implementation roadmap")
    agent_id = "planner"
    query = "Create a roadmap for implementing MCP in our AI assistant platform."
    print(f"\nUser query to {agent_id}: {query}")
    
    # Interact with the planner
    response = network.agents[agent_id].generate_reply(
        messages=[{"role": "user", "content": query}]
    )
    print(f"\nResponse from {agent_id}:\n{response}")
    
    # Add this plan to the workspace
    network.update_workspace(
        section="plan",
        key="implementation_roadmap",
        value=response,
        from_agent=agent_id
    )
    time.sleep(1)
    
    # Show the final workspace with all the contributions
    print("\n6. Examining the final workspace with all contributions")
    network.show_workspace()
    
    # Show the message history
    print("\n7. Viewing the message history")
    network.show_messages()
    
    print("\n=== AGENT NETWORK SCENARIO COMPLETED ===")


def run_collaborative_task_scenario():
    """Run a real-world scenario with the collaborative task framework."""
    print("\n=== RUNNING COLLABORATIVE TASK SCENARIO ===")
    print("This scenario demonstrates a team working on developing an AI assistant with MCP.")
    
    # Create the project manually
    project = langgraph_collaborative_task.LangGraphCollaborativeProject(
        project_name="AI Assistant Development"
    )
    project.create_team()
    
    # Set the project topic and description
    print("\n1. Setting up the project with topic and description")
    project.set_project_topic(
        topic="AI Assistant with Model Context Protocol",
        description="Develop an AI assistant that leverages MCP for improved context handling."
    )
    time.sleep(1)
    
    # Show the initial workspace
    print("\n2. Examining the initial workspace")
    project.show_workspace()
    time.sleep(1)
    
    # Assign research task to the researcher
    print("\n3. Assigning a research task")
    task = project.assign_task(
        agent_id="researcher",
        task_name="Research MCP implementations",
        description="Find examples of how MCP is being implemented in various AI systems."
    )
    task_id = list(task.keys())[0]
    time.sleep(1)
    
    # Interact with the researcher to complete the task
    print("\n4. Working with the Researcher on the task")
    agent_id = "researcher"
    query = "I need you to complete your assigned task on researching MCP implementations."
    print(f"\nUser query to {agent_id}: {query}")
    
    # Simulate the researcher's response
    response = project.agents[agent_id].generate_reply(
        messages=[{"role": "user", "content": query}]
    )
    print(f"\nResponse from {agent_id}:\n{response}")
    
    # Update task status to completed
    print("\n5. Updating the task status to completed")
    project.update_task_status(
        task_id=task_id,
        status="completed",
        result=response
    )
    time.sleep(1)
    
    # Ask analyst to analyze the research
    print("\n6. Assigning analysis task to the Analyst")
    task = project.assign_task(
        agent_id="analyst",
        task_name="Analyze MCP implementation patterns",
        description="Identify patterns and best practices from the research findings."
    )
    analysis_task_id = list(task.keys())[0]
    time.sleep(1)
    
    # Interact with the analyst
    print("\n7. Working with the Analyst on their task")
    agent_id = "analyst"
    query = "Please analyze the research findings on MCP implementations and identify key patterns."
    print(f"\nUser query to {agent_id}: {query}")
    
    # Simulate the analyst's response
    response = project.agents[agent_id].generate_reply(
        messages=[{"role": "user", "content": query}]
    )
    print(f"\nResponse from {agent_id}:\n{response}")
    
    # Update task status
    project.update_task_status(
        task_id=analysis_task_id,
        status="completed",
        result=response
    )
    time.sleep(1)
    
    # Show the final workspace with completed tasks
    print("\n8. Examining the final workspace with completed tasks")
    project.show_workspace()
    
    # Show communication log
    print("\n9. Viewing the project communication log")
    project.show_communication()
    
    print("\n=== COLLABORATIVE TASK SCENARIO COMPLETED ===")


def main():
    """Run both demonstrations with real-world scenarios."""
    print("=== LANGGRAPH MCP EXAMPLE DEMONSTRATIONS ===")
    
    # Run the agent network scenario
    run_agent_network_scenario()
    
    # Run the collaborative task scenario
    run_collaborative_task_scenario()
    
    print("\n=== ALL DEMONSTRATIONS COMPLETED ===")


if __name__ == "__main__":
    main()