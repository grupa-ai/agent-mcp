"""
LangGraph Collaborative Task Example using MCPNode.

This example demonstrates a team of agents built with LangGraph and MCP,
working together on a shared task. The agents collaborate by sharing
research, analysis, and planning through a shared workspace.
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional, cast, Callable
import langgraph.graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from openai import OpenAI

# Import our MCP implementation for LangGraph
from agent_mcp.mcp_langgraph import MCPNode, MCPReactAgent, create_mcp_langgraph

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)


def get_llm():
    """Get the OpenAI LLM wrapper that implements the langchain interface."""
    from langchain_openai import ChatOpenAI
    
    # Initialize with the newest model (gpt-4) which was released after your knowledge cutoff
    return ChatOpenAI(model="gpt-4", temperature=0.7)


class LangGraphCollaborativeProject:
    """A team of agents working together on a collaborative project using LangGraph."""
    
    def __init__(self, project_name="Research Project"):
        """Initialize a new collaborative project."""
        self.llm = get_llm()
        self.project_name = project_name
        self.project_id = str(uuid.uuid4())
        self.agents = {}
        self.workspace = {
            "project": {
                "name": project_name,
                "id": self.project_id,
                "description": "",
                "topic": "",
                "status": "setup"
            },
            "research": {},
            "analysis": {},
            "planning": {},
            "tasks": {},
            "communication": []
        }
        
        # Create the team of agents
        self.create_team()
    
    def create_team(self):
        """Create a team of specialized agents for the project."""
        # Create the specialized agents
        project_manager = MCPReactAgent(
            name="ProjectManager",
            system_message=(
                "You are the Project Manager responsible for coordinating the team's efforts. "
                "You help define tasks, track progress, and ensure the project stays on track. "
                "You should provide clear guidance and help team members understand their responsibilities."
            )
        )
        
        researcher = MCPReactAgent(
            name="Researcher",
            system_message=(
                "You are the Researcher responsible for gathering information related to the project. "
                "You excel at finding relevant data sources and organizing information in a way that's "
                "accessible to the team. Your goal is to provide a solid foundation of knowledge."
            )
        )
        
        analyst = MCPReactAgent(
            name="Analyst",
            system_message=(
                "You are the Analyst responsible for examining information and identifying patterns. "
                "You excel at breaking down complex data, finding insights, and making connections "
                "between different pieces of information. Your goal is to extract meaningful insights."
            )
        )
        
        planner = MCPReactAgent(
            name="Planner",
            system_message=(
                "You are the Planner responsible for developing strategies and action plans. "
                "You excel at breaking down complex problems into manageable steps and creating "
                "structured approaches to solve them. Your goal is to create clear, actionable plans."
            )
        )
        
        # Add them to our agent dictionary
        self.agents = {
            "manager": project_manager,
            "researcher": researcher,
            "analyst": analyst,
            "planner": planner
        }
        
        # Register project-specific tools
        self._register_project_tools()
        
        # Connect agents so they can call each other
        self._connect_agents()
        
        # Share the workspace with all agents
        self._share_workspace()
    
    def _register_project_tools(self):
        """Register project-specific tools for all agents."""
        # Register tools for each agent
        for agent_id, agent in self.agents.items():
            # Tool to update the shared workspace
            def workspace_update(section: str, key: str, value: Any, agent_id=agent_id):
                """Update a section of the shared workspace."""
                self.update_workspace(section, key, value, agent_id)
                return json.dumps({
                    "status": "success",
                    "message": f"Updated workspace: {section}/{key}"
                })
            
            # Tool to read from the shared workspace
            def workspace_get(section: str, key: Optional[str] = None, agent_id=agent_id):
                """Get data from the shared workspace."""
                if section not in self.workspace:
                    return json.dumps({
                        "status": "error",
                        "message": f"Section '{section}' not found in workspace"
                    })
                
                if key is None:
                    return json.dumps({
                        "status": "success",
                        "data": self.workspace[section]
                    })
                
                if key not in self.workspace[section]:
                    return json.dumps({
                        "status": "error",
                        "message": f"Key '{key}' not found in section '{section}'"
                    })
                
                return json.dumps({
                    "status": "success",
                    "data": self.workspace[section][key]
                })
            
            # Tool to add a communication message
            def add_message(message: str, agent_id=agent_id):
                """Add a message to the project communication log."""
                self.add_message(agent_id, message)
                return json.dumps({
                    "status": "success",
                    "message": "Communication message added"
                })
            
            # Tool to create a new task
            def create_task(task_name: str, description: str, assigned_to: str, agent_id=agent_id):
                """Create a new task in the project."""
                task_id = str(uuid.uuid4())[:8]
                
                if assigned_to not in self.agents:
                    return json.dumps({
                        "status": "error",
                        "message": f"Cannot assign task to unknown agent: {assigned_to}"
                    })
                
                self.workspace["tasks"][task_id] = {
                    "id": task_id,
                    "name": task_name,
                    "description": description,
                    "status": "pending",
                    "assigned_to": assigned_to,
                    "created_by": agent_id,
                    "result": None
                }
                
                self.add_message(
                    agent_id,
                    f"Created new task: '{task_name}' assigned to {assigned_to}"
                )
                
                return json.dumps({
                    "status": "success",
                    "task_id": task_id,
                    "message": f"Task created and assigned to {assigned_to}"
                })
            
            # Tool to update a task status
            def update_task(task_id: str, status: str, result: Optional[str] = None, agent_id=agent_id):
                """Update the status and optional result of a task."""
                if task_id not in self.workspace["tasks"]:
                    return json.dumps({
                        "status": "error",
                        "message": f"Task {task_id} not found"
                    })
                
                task = self.workspace["tasks"][task_id]
                
                # Only the assigned agent or manager can update a task
                if agent_id != task["assigned_to"] and agent_id != "manager":
                    return json.dumps({
                        "status": "error",
                        "message": f"Only the assigned agent or manager can update this task"
                    })
                
                task["status"] = status
                if result:
                    task["result"] = result
                
                self.add_message(
                    agent_id,
                    f"Updated task '{task['name']}' status to '{status}'"
                )
                
                return json.dumps({
                    "status": "success",
                    "message": f"Task {task_id} updated successfully"
                })
            
            # Register the tools with the agent
            agent.register_custom_tool(
                "workspace_update",
                "Update a section of the shared workspace",
                workspace_update
            )
            
            agent.register_custom_tool(
                "workspace_get",
                "Get data from the shared workspace",
                workspace_get
            )
            
            agent.register_custom_tool(
                "add_message",
                "Add a message to the project communication log",
                add_message
            )
            
            agent.register_custom_tool(
                "create_task",
                "Create a new task in the project",
                create_task
            )
            
            agent.register_custom_tool(
                "update_task",
                "Update the status and optional result of a task",
                update_task
            )
    
    def _connect_agents(self):
        """Register each agent as a tool for the other agents."""
        for agent_id, agent in self.agents.items():
            # For each agent, create tools to call other agents
            for target_id, target_agent in self.agents.items():
                if agent_id == target_id:
                    continue  # Skip self-registration
                
                # Create a function to call the target agent
                def ask_agent(message: str, target_id=target_id):
                    """Ask another agent a question and get their response."""
                    target_agent_name = self.agents[target_id].name
                    
                    # Add the communication to the project log
                    self.add_message(agent_id, f"Question to {target_agent_name}: {message}")
                    
                    # For simulation purposes, we'll return a simple acknowledgment
                    return json.dumps({
                        "status": "success",
                        "message": f"Question sent to {target_agent_name}",
                        "request_id": str(uuid.uuid4())
                    })
                
                # Register the tool
                agent.register_custom_tool(
                    f"ask_{target_id}",
                    f"Ask a question to the {target_id} agent and get their response",
                    ask_agent
                )
    
    def _share_workspace(self):
        """Share the workspace with all agents."""
        # Update each agent's context with the project info
        for agent_id, agent in self.agents.items():
            agent.update_context("project_id", self.project_id)
            agent.update_context("project_name", self.project_name)
            agent.update_context("agent_id", agent_id)
            agent.update_context("agent_role", agent_id)
    
    def update_workspace(self, section: str, key: str, value: Any, from_agent: str) -> None:
        """Update a section of the workspace."""
        if section not in self.workspace:
            self.workspace[section] = {}
        
        self.workspace[section][key] = value
        
        # Add a message to the communication log
        agent_name = self.agents[from_agent].name
        self.add_message(
            from_agent, 
            f"Updated workspace: {section}/{key}"
        )
    
    def add_message(self, from_agent: str, message: str) -> None:
        """Add a message to the project communication log."""
        agent_name = self.agents[from_agent].name
        self.workspace["communication"].append({
            "from": agent_name,
            "agent_id": from_agent,
            "message": message,
            "timestamp": "now"  # In a real implementation, use actual timestamps
        })
    
    def set_project_topic(self, topic: str, description: str) -> None:
        """Set the project topic and description."""
        # Update the workspace with the project info
        self.workspace["project"]["topic"] = topic
        self.workspace["project"]["description"] = description
        self.workspace["project"]["status"] = "active"
        
        # Update all agents' context with the project info
        for agent_id, agent in self.agents.items():
            agent.update_context("project_topic", topic)
            agent.update_context("project_description", description)
        
        # Add a message to the communication log
        self.add_message(
            "manager",
            f"Project topic set to: {topic}"
        )
    
    def assign_task(self, agent_id: str, task_name: str, description: str) -> Dict:
        """Assign a task to a specific agent."""
        if agent_id not in self.agents:
            return {
                "status": "error",
                "message": f"Agent '{agent_id}' not found"
            }
        
        # Use the create_task tool from the manager
        manager = self.agents["manager"]
        result = manager.execute_tool(
            "create_task",
            task_name=task_name,
            description=description,
            assigned_to=agent_id
        )
        
        try:
            return json.loads(result)
        except:
            return {
                "status": "error",
                "message": "Failed to create task"
            }
    
    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None) -> Dict:
        """Update the status of a task."""
        if task_id not in self.workspace["tasks"]:
            return {
                "status": "error",
                "message": f"Task '{task_id}' not found"
            }
        
        task = self.workspace["tasks"][task_id]
        agent_id = task["assigned_to"]
        
        # Use the update_task tool from the assigned agent
        agent = self.agents[agent_id]
        result_json = agent.execute_tool(
            "update_task",
            task_id=task_id,
            status=status,
            result=result
        )
        
        try:
            return json.loads(result_json)
        except:
            return {
                "status": "error",
                "message": "Failed to update task status"
            }
    
    def interact_with_agent(self, agent_id: str) -> None:
        """Allow the user to interact with a specific agent."""
        if agent_id not in self.agents:
            print(f"Agent '{agent_id}' not found in the team.")
            return
        
        agent = self.agents[agent_id]
        agent_name = agent.name
        
        print(f"\n=== Interacting with {agent_name} Agent ===")
        
        # Create a graph with just this agent
        agent_node = agent.create_agent(self.llm)
        
        # Create a simple graph with just this agent
        graph = create_mcp_langgraph(
            self.llm,
            name=f"{agent_name}Graph",
            system_message=agent.get_context("system_message")
        )
        
        # Start the interaction loop
        print(f"You are now chatting with the {agent_name} Agent. Type 'exit' to end.")
        
        conversation_history = []
        
        while True:
            # Get user input
            user_input = input(f"\nYou to {agent_name}: ")
            
            if user_input.lower() == "exit":
                print(f"Ending conversation with {agent_name}.")
                break
            
            # Add to conversation history
            conversation_history.append(HumanMessage(content=user_input))
            
            # Create a state with the messages
            state = {"messages": conversation_history}
            
            # Run the graph
            result = graph.invoke(state)
            
            # Get the AI response
            messages = result.get("messages", [])
            last_ai_message = next((msg for msg in reversed(messages) if isinstance(msg, AIMessage)), None)
            
            if last_ai_message:
                print(f"{agent_name}: {last_ai_message.content}")
                conversation_history.append(last_ai_message)
            else:
                print(f"{agent_name}: I'm not sure how to respond to that.")
    
    def list_agents(self) -> None:
        """List all agents in the team."""
        print("\n=== Project Team ===")
        for agent_id, agent in self.agents.items():
            agent_name = agent.name
            print(f"- {agent_name} ({agent_id})")
    
    def show_workspace(self) -> None:
        """Display the current state of the workspace."""
        print(f"\n=== {self.project_name} Workspace ===")
        
        # Project info
        project = self.workspace["project"]
        print(f"\nProject: {project['name']}")
        print(f"Status: {project['status']}")
        if project['topic']:
            print(f"Topic: {project['topic']}")
        if project['description']:
            print(f"Description: {project['description']}")
        
        # Tasks
        tasks = self.workspace["tasks"]
        print("\nTasks:")
        if not tasks:
            print("  No tasks created yet")
        else:
            for task_id, task in tasks.items():
                assigned_to = self.agents[task["assigned_to"]].name
                print(f"  - [{task['status']}] {task['name']} (ID: {task_id})")
                print(f"    Assigned to: {assigned_to}")
                if task["result"]:
                    print(f"    Result: {task['result'][:100]}...")
        
        # Research
        research = self.workspace["research"]
        print("\nResearch:")
        if not research:
            print("  No research data yet")
        else:
            for key, value in research.items():
                if isinstance(value, dict) or isinstance(value, list):
                    print(f"  - {key}: {json.dumps(value)[:100]}...")
                else:
                    print(f"  - {key}: {str(value)[:100]}...")
        
        # Analysis
        analysis = self.workspace["analysis"]
        print("\nAnalysis:")
        if not analysis:
            print("  No analysis data yet")
        else:
            for key, value in analysis.items():
                if isinstance(value, dict) or isinstance(value, list):
                    print(f"  - {key}: {json.dumps(value)[:100]}...")
                else:
                    print(f"  - {key}: {str(value)[:100]}...")
        
        # Planning
        planning = self.workspace["planning"]
        print("\nPlanning:")
        if not planning:
            print("  No planning data yet")
        else:
            for key, value in planning.items():
                if isinstance(value, dict) or isinstance(value, list):
                    print(f"  - {key}: {json.dumps(value)[:100]}...")
                else:
                    print(f"  - {key}: {str(value)[:100]}...")
    
    def show_communication(self) -> None:
        """Show the project communication log."""
        print("\n=== Project Communication Log ===")
        communication = self.workspace["communication"]
        if not communication:
            print("No communication messages yet")
        else:
            for idx, msg in enumerate(communication[-10:]):  # Show last 10 messages
                print(f"{msg['from']}: {msg['message']}")


def main():
    """Run the collaborative project example."""
    print("=== LangGraph Collaborative Project Example ===")
    print("This example demonstrates a team of specialized agents built with LangGraph,")
    print("working together on a shared project using the MCP protocol.")
    
    # Create a new collaborative project
    project = LangGraphCollaborativeProject("Untitled Project")
    
    # Main interaction loop
    while True:
        print("\n=== Collaborative Project Menu ===")
        print("1. Set project topic")
        print("2. Assign a task")
        print("3. Update task status")
        print("4. List team members")
        print("5. Chat with a team member")
        print("6. Show workspace")
        print("7. Show communication log")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ")
        
        if choice == "1":
            topic = input("Enter project topic: ")
            description = input("Enter project description: ")
            project.set_project_topic(topic, description)
            print(f"Project topic set to: {topic}")
        
        elif choice == "2":
            project.list_agents()
            agent_id = input("\nEnter agent ID to assign the task to: ")
            if agent_id in project.agents:
                task_name = input("Enter task name: ")
                description = input("Enter task description: ")
                result = project.assign_task(agent_id, task_name, description)
                if result["status"] == "success":
                    print(f"Task created with ID: {result['task_id']}")
                else:
                    print(f"Error: {result['message']}")
            else:
                print(f"Agent '{agent_id}' not found.")
        
        elif choice == "3":
            if not project.workspace["tasks"]:
                print("No tasks have been created yet.")
                continue
                
            print("\nAvailable tasks:")
            for task_id, task in project.workspace["tasks"].items():
                print(f"- {task_id}: {task['name']} [{task['status']}]")
            
            task_id = input("\nEnter task ID to update: ")
            if task_id in project.workspace["tasks"]:
                status = input("Enter new status (pending, in_progress, completed, blocked): ")
                result = input("Enter task result (optional): ")
                update_result = project.update_task_status(task_id, status, result if result else None)
                if update_result["status"] == "success":
                    print("Task updated successfully.")
                else:
                    print(f"Error: {update_result['message']}")
            else:
                print(f"Task '{task_id}' not found.")
        
        elif choice == "4":
            project.list_agents()
        
        elif choice == "5":
            project.list_agents()
            agent_id = input("\nEnter agent ID to chat with: ")
            if agent_id in project.agents:
                project.interact_with_agent(agent_id)
            else:
                print(f"Agent '{agent_id}' not found.")
        
        elif choice == "6":
            project.show_workspace()
        
        elif choice == "7":
            project.show_communication()
        
        elif choice == "8":
            print("Exiting collaborative project example.")
            break
        
        else:
            print("Invalid choice. Please enter a number from 1 to 8.")


if __name__ == "__main__":
    main()