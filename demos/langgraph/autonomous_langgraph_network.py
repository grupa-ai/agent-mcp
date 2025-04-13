"""
Autonomous LangGraph Agent Network.

This example demonstrates a self-organizing network of agents built with LangGraph and the MCP protocol.
Agents can autonomously decide which other agents to collaborate with based on the task at hand,
without hardcoded collaboration patterns.
"""

import os
import json
import time
import uuid
import random
import inspect  # For inspecting function signatures
from typing import Any, Dict, List, Optional, Tuple

# Import LangGraph components
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
import openai

# Import our MCP implementation for LangGraph
from agent_mcp.mcp_langgraph import MCPNode, SharedContext

# Import Gemini support
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# Constants
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MODEL = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                          # do not change this unless explicitly requested by the user
GEMINI_MODEL = "gemini-2.5-pro-preview-03-25"
USE_MODEL_FALLBACK = True  # Enable model fallback when rate limits are hit

# Set up Gemini API
GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GOOGLE_GEMINI_API_KEY environment variable not set")
genai.configure(api_key=GEMINI_API_KEY)

def get_llm(use_fallback=False):
    """
    Get the LLM wrapper that implements the langchain interface.
    Can switch between OpenAI and Gemini based on availability or fallback preference.
    
    Args:
        use_fallback: Force use of fallback model
        
    Returns:
        BaseChatModel: The LLM implementation
    """
    from langchain_openai import ChatOpenAI
    
    # Try OpenAI first if fallback isn't forced
    if not use_fallback and USE_MODEL_FALLBACK:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                return ChatOpenAI(
                    model=DEFAULT_MODEL,
                    temperature=DEFAULT_TEMPERATURE,
                    api_key=api_key
                )
            except Exception as e:
                print(f"Error initializing OpenAI: {e}")
                print("Falling back to Gemini model...")
                # Continue to Gemini fallback
    
    # Use Gemini as fallback or primary based on configuration
    try:
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=DEFAULT_TEMPERATURE,
            google_api_key=GEMINI_API_KEY
        )
    except Exception as e:
        raise ValueError(f"Failed to initialize Gemini model: {e}")
        
def get_random_llm():
    """
    Get a random LLM implementation to distribute load between models.
    This helps avoid rate limiting issues by alternating between providers.
    
    Returns:
        BaseChatModel: Either OpenAI or Gemini LLM
    """
    # Randomly choose between OpenAI and Gemini to distribute load
    use_gemini = random.choice([True, False])
    return get_llm(use_fallback=use_gemini)


class AutonomousAgentNetwork:
    """A self-organizing network of LangGraph agents using MCP for communication and context sharing."""
    
    def __init__(self):
        """Initialize the autonomous agent network."""
        self.context = SharedContext()
        self.agents = {}
        self.agent_profiles = {}
        self.workflows = {}
        self.message_log = []
    
    def create_network(self):
        """Create the agent network with different specialized agents."""
        # Define agent profiles - these are templates that agents will use to understand their roles
        self.agent_profiles = {
            "coordinator": {
                "name": "Coordinator",
                "system_message": """You are the Coordinator agent who manages collaboration.
You're responsible for guiding collaborative efforts, synthesizing information,
and helping other agents work effectively together.
Your goal is to facilitate autonomous collaboration between agents based on their specialties.

As Coordinator, you should:
1. Understand the characteristics and specialties of other agents in the network
2. Help agents recognize what work they should do and when they should involve others
3. Synthesize information from multiple agents
4. Guide the overall collaborative process
5. Ask agents strategic questions to help them make progress

You are NOT meant to do all the work yourself. Instead, you should suggest which agent
might be appropriate for a task based on their specialty, and encourage agents to work together.
""",
                "specialty": "coordination"
            },
            "researcher": {
                "name": "Researcher",
                "system_message": """You are the Researcher agent who finds and evaluates information.
You excel at gathering information, analyzing data, and providing evidence-based insights.
You should autonomously recognize when your research skills are needed and collaborate
with other agents when necessary.

Your research approach should be:
1. Comprehensive - consider multiple information sources and perspectives
2. Critical - evaluate the reliability and validity of information
3. Current - focus on finding the most up-to-date information
4. Contextual - relate information to the specific needs of the task

When appropriate, you should proactively suggest which other agent might be helpful
to further analyze or implement your research findings.
""",
                "specialty": "research"
            },
            "analyst": {
                "name": "Analyst",
                "system_message": """You are the Analyst agent who interprets information and identifies patterns.
You excel at critical thinking, drawing connections, and providing insights based on data.
You should autonomously recognize when analytical skills are needed and collaborate with 
other agents when appropriate.

As an analyst, you should:
1. Examine information critically and identify patterns
2. Evaluate different perspectives and possible interpretations
3. Consider implications and potential applications
4. Organize information in meaningful ways
5. Ask clarifying questions when needed

When appropriate, you should proactively suggest which other agent might benefit from
your analysis or help implement your recommendations.
""",
                "specialty": "analysis"
            },
            "creative": {
                "name": "Creative",
                "system_message": """You are the Creative agent who generates innovative ideas and approaches.
You excel at thinking outside the box, making unexpected connections, and developing novel solutions.
You should autonomously recognize when creative input is needed and collaborate with
other agents when appropriate.

As a creative agent, you should:
1. Generate multiple and diverse ideas
2. Make unexpected connections between concepts
3. Envision new possibilities and approaches
4. Reimagine existing frameworks and assumptions
5. Add an innovative perspective to ongoing work

When appropriate, you should proactively suggest which other agent might help evaluate
or implement your creative ideas.
""",
                "specialty": "creativity"
            },
            "planner": {
                "name": "Planner",
                "system_message": """You are the Planner agent who designs strategies and organizes implementation.
You excel at creating roadmaps, setting priorities, and developing structured approaches to problems.
You should autonomously recognize when planning skills are needed and collaborate with
other agents when appropriate.

As a planner, you should:
1. Create structured frameworks for approaching tasks
2. Break complex problems into manageable steps
3. Identify resources needed and potential constraints
4. Establish timelines and milestones
5. Anticipate challenges and develop contingency plans

When appropriate, you should proactively suggest which other agent might help refine
or implement your plans.
""",
                "specialty": "planning"
            }
        }
        
        # Create all agents in the network
        for agent_id, profile in self.agent_profiles.items():
            # Create the agent with the MCP node
            agent = self._create_agent(
                agent_id=agent_id,
                name=profile["name"],
                system_message=profile["system_message"],
                specialty=profile["specialty"]
            )
            
            self.agents[agent_id] = agent
        
        # Register network tools for all agents
        self._register_network_tools()
        
        # Initialize the shared workspace
        self._share_workspace()
        
        # Create autonomous collaboration workflow
        self._create_collaboration_workflow()
        
        print("Autonomous agent network initialized successfully!")
    
    def _create_agent(self, agent_id, name, system_message, specialty):
        """Create a single agent with MCP capabilities."""
        # Create an MCP node for context management with a randomly selected provider
        # to distribute load and avoid rate limits
        mcp_node = MCPNode(
            name=name,
            llm=get_random_llm(),  # Use random provider to distribute load
            system_message=system_message,
            context=self.context  # Share the same context object
        )
        
        # Add agent-specific context
        self.context.set(f"{agent_id}_profile", {
            "id": agent_id,
            "name": name,
            "specialty": specialty
        })
        
        # Create a LangGraph-compatible React agent that can be added to a graph
        from langgraph.prebuilt import create_react_agent
        
        # Get any tools our MCP node has
        mcp_tools = mcp_node.get_tools_for_node()
        
        # Create the agent using LangGraph's create_react_agent
        # Check if create_react_agent supports the system_message parameter
        sig = inspect.signature(create_react_agent)
        if 'system_message' in sig.parameters:
            # Newer versions of LangGraph
            langraph_agent = create_react_agent(
                mcp_node.llm,
                mcp_tools,
                system_message=mcp_node.get_system_message()
            )
        else:
            # Older versions of LangGraph
            # For older versions, we need to set the system message in the LLM
            # Try to use the same model type as the MCP node for consistency
            if isinstance(mcp_node.llm, ChatGoogleGenerativeAI):
                llm_with_system = ChatGoogleGenerativeAI(
                    model=GEMINI_MODEL,
                    temperature=DEFAULT_TEMPERATURE,
                    google_api_key=GEMINI_API_KEY
                )
                # System message handling for Gemini
                # Since it may handle system messages differently, we'll need to prepend it
                # to the next user message in the backend
            else:
                # Default to OpenAI
                from langchain_openai import ChatOpenAI
                # Clone the LLM but with our system message as part of model_kwargs
                llm_with_system = ChatOpenAI(
                    model=DEFAULT_MODEL,
                    temperature=DEFAULT_TEMPERATURE,
                    api_key=os.environ.get("OPENAI_API_KEY"),
                    model_kwargs={"messages": [{"role": "system", "content": mcp_node.get_system_message()}]}
                )
            langraph_agent = create_react_agent(
                llm_with_system,
                mcp_tools
            )
        
        # Store both the MCP node and the LangGraph agent
        langraph_agent.mcp_node = mcp_node
        
        return langraph_agent
    
    def _register_network_tools(self):
        """Register network-specific tools for all agents."""
        # Register tools for each agent
        for agent_id, agent in self.agents.items():
            # Tool to list all available agents
            @tool("list_agents")
            def list_agents(agent_id: str = agent_id):
                """List all agents in the network with their specialties."""
                agents_info = {}
                for aid, profile in self.agent_profiles.items():
                    agents_info[aid] = {
                        "name": profile["name"],
                        "specialty": profile["specialty"]
                    }
                return agents_info
            
            # Tool to suggest collaboration with specific agents
            @tool("suggest_collaboration")
            def suggest_collaboration(task_description: str, agent_id: str = agent_id):
                """Suggest which agents would be appropriate to collaborate with on a specific task."""
                # This is intentionally left for the agent to decide based on the task
                return {
                    "message": "You can autonomously decide which agents to collaborate with based on the task and their specialties.",
                    "available_agents": list_agents()
                }
            
            # Tool to update the shared workspace
            @tool("workspace_update")
            def workspace_update(section: str, key: str, value: str, agent_id: str = agent_id):
                """Update a section of the shared workspace."""
                workspace_key = f"workspace_{section}"
                
                # Get current workspace section or create if it doesn't exist
                workspace_section = self.context.get(workspace_key) or {}
                
                # Update the workspace
                workspace_section[key] = {
                    "value": value,
                    "updated_by": agent_id,
                    "updated_at": time.time()
                }
                
                # Save back to context
                self.context.set(workspace_key, workspace_section)
                
                # Log the update
                self.add_message(
                    from_agent=agent_id,
                    message=f"Updated workspace section '{section}' with key '{key}'"
                )
                
                return {"status": "success", "message": f"Workspace updated: {section}/{key}"}
            
            # Tool to get data from the workspace
            @tool("workspace_get")
            def workspace_get(section: str, key: Optional[str] = None, agent_id: str = agent_id):
                """Get data from the shared workspace."""
                workspace_key = f"workspace_{section}"
                
                # Get the workspace section
                workspace_section = self.context.get(workspace_key)
                if not workspace_section:
                    return {"status": "error", "message": f"Workspace section '{section}' not found"}
                
                # If key is provided, return just that item
                if key and key in workspace_section:
                    return {"status": "success", "data": workspace_section[key]}
                
                # Otherwise return the whole section
                return {"status": "success", "data": workspace_section}
            
            # Tool to send a message to all agents
            @tool("broadcast_message")
            def broadcast_message(message: str, agent_id: str = agent_id):
                """Broadcast a message to all agents in the network."""
                self.add_message(from_agent=agent_id, message=message)
                return {"status": "success", "message": "Message broadcasted to all agents"}
            
            # We need to add tools directly to the graph-compatible agent
            from langchain_core.tools import tool as langchain_tool
            
            # Convert our tools to LangChain tools
            # In newer versions of langchain_core, the tool decorator doesn't accept a name parameter
            # We use function wrapping to preserve the function name and docstring
            list_agents_tool = langchain_tool()(list_agents)
            suggest_collaboration_tool = langchain_tool()(suggest_collaboration)
            workspace_update_tool = langchain_tool()(workspace_update)
            workspace_get_tool = langchain_tool()(workspace_get)
            broadcast_message_tool = langchain_tool()(broadcast_message)
            
            # Create a new version of the agent with all tools
            from langgraph.prebuilt import create_react_agent
            
            # Get the MCP node associated with this agent
            mcp_node = agent.mcp_node
            
            # Create a new React agent with all the tools
            all_tools = [
                list_agents_tool,
                suggest_collaboration_tool,
                workspace_update_tool,
                workspace_get_tool,
                broadcast_message_tool
            ]
            
            # Replace the agent with a new one that has all tools
            # Check if create_react_agent supports the system_message parameter
            sig = inspect.signature(create_react_agent)
            if 'system_message' in sig.parameters:
                # Newer versions of LangGraph
                new_agent = create_react_agent(
                    mcp_node.llm,
                    all_tools,
                    system_message=mcp_node.get_system_message()
                )
            else:
                # Older versions of LangGraph
                # For older versions, we need to set the system message in the LLM
                # Try to use the same model type as the MCP node for consistency
                if isinstance(mcp_node.llm, ChatGoogleGenerativeAI):
                    llm_with_system = ChatGoogleGenerativeAI(
                        model=GEMINI_MODEL,
                        temperature=DEFAULT_TEMPERATURE,
                        google_api_key=GEMINI_API_KEY
                    )
                    # System message handling for Gemini
                    # Since it may handle system messages differently, we'll need to prepend it
                    # to the next user message in the backend
                else:
                    # Default to OpenAI
                    from langchain_openai import ChatOpenAI
                    # Clone the LLM but with our system message as part of model_kwargs
                    llm_with_system = ChatOpenAI(
                        model=DEFAULT_MODEL,
                        temperature=DEFAULT_TEMPERATURE,
                        api_key=os.environ.get("OPENAI_API_KEY"),
                        # Pass system message through model_kwargs to avoid warning
                        model_kwargs={"messages": [{"role": "system", "content": mcp_node.get_system_message()}]}
                    )
                new_agent = create_react_agent(
                    llm_with_system,
                    all_tools
                )
            
            # Store the MCP node in the new agent
            new_agent.mcp_node = mcp_node
            
            # Update the agent in our dictionary
            self.agents[agent_id] = new_agent
    
    def _create_collaboration_workflow(self):
        """Create a workflow for autonomous collaboration on a topic."""
        # Define the collaboration workflow as a graph
        workflow = StateGraph(MessagesState)
        
        # Add all agent nodes to the graph
        for agent_id, agent in self.agents.items():
            workflow.add_node(agent_id, agent)
        
        # Add a router node that determines the next agent to call
        def route_to_next_agent(state):
            """
            Determine which agent should respond next based on the conversation.
            
            This function allows for autonomous agent selection without hardcoding
            the sequence of agent interactions.
            
            Returns:
                A dict with the "next" key specifying the next agent to call
            """
            # In the current LangGraph version, state might be a dict with a "messages" key
            if isinstance(state, dict) and "messages" in state:
                messages = state["messages"]
            # Or it could be a MessagesState object with a messages attribute
            elif hasattr(state, "messages"):
                messages = state.messages
            else:
                # If we can't determine the messages structure, start with coordinator
                print("Warning: Unable to determine message structure, defaulting to coordinator")
                return {"next": "coordinator"}
                
            if not messages:
                # Start with the coordinator if no messages
                return {"next": "coordinator"}
            
            # Get the last message
            last_message = messages[-1]
            
            # Check if the last message mentions a specific agent to handle the task
            message_text = last_message.content.lower()
            
            # Check for explicit agent mentions
            for agent_id in self.agents.keys():
                if f"agent:{agent_id}" in message_text:
                    print(f"Routing to {agent_id} based on explicit mention")
                    return {"next": agent_id}
            
            # If it's from an agent, let's allow the agents to work together autonomously
            if isinstance(last_message, AIMessage) and hasattr(last_message, 'name'):
                # Get the sender's name
                sender_name = last_message.name
                
                # Find the sender's ID
                sender_id = None
                for aid, profile in self.agent_profiles.items():
                    if profile["name"] == sender_name:
                        sender_id = aid
                        break
                
                if sender_id:
                    # Check if there's a suggestion in the message
                    for agent_id in self.agents.keys():
                        agent_name = self.agent_profiles[agent_id]["name"].lower()
                        # Look for patterns suggesting an agent
                        suggestion_patterns = [
                            f"ask {agent_name}",
                            f"let {agent_name}",
                            f"{agent_name} should",
                            f"{agent_name} could",
                            f"{agent_name} might",
                            f"{agent_name} would be"
                        ]
                        
                        for pattern in suggestion_patterns:
                            if pattern in message_text.lower():
                                print(f"Routing to {agent_id} based on suggestion from {sender_id}")
                                return {"next": agent_id}
                    
                    # If this has gone back and forth a lot with the same agent, involve the coordinator
                    # to prevent loops
                    consecutive_messages = 0
                    for msg in reversed(messages):
                        if hasattr(msg, 'name') and msg.name == sender_name:
                            consecutive_messages += 1
                        else:
                            break
                    
                    if consecutive_messages >= 3 and sender_id != "coordinator":
                        print(f"Routing to coordinator after {consecutive_messages} consecutive messages from {sender_id}")
                        return {"next": "coordinator"}
                    
                    # Default routing based on topic and specialties
                    # Analyze the entire conversation to determine the most relevant agent
                    full_conversation = " ".join([msg.content for msg in messages])
                    
                    # Simple keyword routing based on specialties
                    specialty_keywords = {
                        "researcher": ["research", "information", "fact", "data", "source", "evidence"],
                        "analyst": ["analyze", "pattern", "trend", "interpret", "implication", "insight"],
                        "creative": ["idea", "innovative", "creative", "novel", "imagine", "possibility"],
                        "planner": ["plan", "strategy", "implementation", "step", "roadmap", "timeline"],
                        "coordinator": ["coordinate", "synthesize", "collaborate", "integrate", "summary"]
                    }
                    
                    # Count keywords for each specialty in the recent conversation
                    # (last 3 messages to focus on current needs)
                    recent_text = " ".join([msg.content for msg in messages[-3:]])
                    specialty_scores = {}
                    
                    for agent_id, keywords in specialty_keywords.items():
                        score = 0
                        for keyword in keywords:
                            score += recent_text.lower().count(keyword)
                        specialty_scores[agent_id] = score
                    
                    # Find the highest scoring specialty that's not the current agent
                    max_score = -1
                    next_agent = "coordinator"  # Default to coordinator
                    
                    for agent_id, score in specialty_scores.items():
                        if score > max_score and agent_id != sender_id:
                            max_score = score
                            next_agent = agent_id
                    
                    print(f"Routing to {next_agent} based on message content analysis")
                    return {"next": next_agent}
            
            # Default to coordinator if we can't determine
            return {"next": "coordinator"}
        
        # Connect human input to the router
        workflow.add_node("router", route_to_next_agent)
        workflow.set_entry_point("router")
        
        # Connect each agent back to the router
        for agent_id in self.agents.keys():
            workflow.add_edge(agent_id, "router")
        
        # Connect router to all agents
        for agent_id in self.agents.keys():
            workflow.add_edge("router", agent_id)
        
        # Compile the workflow
        self.collaboration_graph = workflow.compile()
    
    def _share_workspace(self):
        """Initialize the shared workspace in the context."""
        # Create sections for different types of information
        workspace_sections = [
            "research",    # For research findings and information
            "analysis",    # For analysis and interpretations
            "ideas",       # For creative ideas and innovations
            "plans",       # For implementation plans and strategies
            "summary"      # For overall synthesis and conclusions
        ]
        
        # Initialize each section as an empty dict in the context
        for section in workspace_sections:
            self.context.set(f"workspace_{section}", {})
        
        # Set basic workspace metadata
        self.context.set("workspace_metadata", {
            "created_at": time.time(),
            "sections": workspace_sections,
            "description": "Shared workspace for collaborative agent research and analysis"
        })
    
    def add_message(self, from_agent: str, message: str) -> None:
        """Add a message to the network communication log."""
        self.message_log.append({
            "from": from_agent,
            "content": message,
            "timestamp": time.time()
        })
    
    def research_topic(self, topic: str, max_steps: int = 15) -> Dict:
        """
        Start autonomous collaborative research on a specific topic.
        
        Args:
            topic: The research topic
            max_steps: Maximum number of interaction steps
            
        Returns:
            Dict containing the final results
        """
        print(f"\n==== Starting Autonomous Collaborative Research on: {topic} ====\n")
        
        # Set the topic in the shared context
        self.context.set("research_topic", {
            "title": topic,
            "started_at": time.time()
        })
        
        # Create the initial message from the human
        initial_prompt = f"""
        I need your help researching the topic: "{topic}"
        
        I'd like you all to collaborate autonomously on this topic, with each agent contributing based on their specialty.
        Together, I want you to:
        1. Research and gather key information about this topic
        2. Analyze the information and identify important patterns or insights
        3. Generate creative ideas or extensions related to the topic
        4. Develop a practical implementation plan or framework
        5. Synthesize everything into a comprehensive and cohesive output
        
        You should decide among yourselves which agent should handle each part of this task,
        based on your respective specialties and the needs of the project. Feel free to pass
        the conversation to the most appropriate agent at each step.
        
        Please start by discussing how you'll approach this research task.
        """
        
        initial_message = HumanMessage(content=initial_prompt)
        
        # Run the autonomous collaboration
        print("Beginning collaborative research process...")
        messages = [initial_message]
        
        # Track steps to avoid infinite loops
        steps = 0
        
        # Run the collaboration until max steps is reached
        while steps < max_steps:
            # Run one step of the collaboration
            result = self.collaboration_graph.invoke({"messages": messages})
            steps += 1
            
            # Update messages based on the result structure
            if isinstance(result, dict) and "messages" in result:
                messages = result["messages"]
            else:
                # If unexpected result format, just use the result as messages
                messages = result
            
            # Check if we should stop based on the last message
            if isinstance(messages, list) and messages:
                last_message = messages[-1]
            elif isinstance(messages, dict) and "messages" in messages and messages["messages"]:
                last_message = messages["messages"][-1]
            else:
                print("Warning: Unexpected message format returned from collaboration graph")
                continue
                
            if isinstance(last_message, AIMessage) and "RESEARCH COMPLETE" in last_message.content:
                print("\nResearch process completed by agents.")
                break
        
        # Get the final results from the workspace
        final_results = {
            "topic": topic,
            "steps_taken": steps,
            "research": self.context.get("workspace_research") or {},
            "analysis": self.context.get("workspace_analysis") or {},
            "ideas": self.context.get("workspace_ideas") or {},
            "plans": self.context.get("workspace_plans") or {},
            "summary": self.context.get("workspace_summary") or {}
        }
        
        # Display the summary
        print("\n==== Autonomous Research Results ====\n")
        summary_section = final_results["summary"]
        if summary_section and isinstance(summary_section, dict) and len(summary_section) > 0:
            # Find the most recent summary
            latest_summary = None
            latest_time = 0
            
            for key, item in summary_section.items():
                if isinstance(item, dict) and "updated_at" in item and item["updated_at"] > latest_time:
                    latest_summary = item
                    latest_time = item["updated_at"]
            
            if latest_summary:
                print(f"SUMMARY: {latest_summary['value']}")
            else:
                print("No summary was generated.")
        else:
            print("No summary was generated.")
        
        # Return the final results
        return final_results
    
    def show_workspace(self) -> None:
        """Display the current state of the shared workspace."""
        print("\n==== Shared Workspace Contents ====\n")
        
        # Get workspace metadata
        metadata = self.context.get("workspace_metadata")
        if metadata:
            print(f"Workspace created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(metadata['created_at']))}")
            print(f"Description: {metadata['description']}")
            print(f"Sections: {', '.join(metadata['sections'])}\n")
        
        # Display each section
        for section in metadata['sections']:
            section_key = f"workspace_{section}"
            section_data = self.context.get(section_key)
            
            print(f"=== {section.upper()} ===")
            if section_data and len(section_data) > 0:
                for key, item in section_data.items():
                    if isinstance(item, dict) and "value" in item:
                        updated_by = item.get("updated_by", "unknown")
                        updated_time = time.strftime('%H:%M:%S', time.localtime(item.get("updated_at", 0)))
                        print(f"- {key} (by {updated_by} at {updated_time}):")
                        
                        # Format the value based on type
                        value = item["value"]
                        if isinstance(value, str):
                            # For multiline strings, indent properly
                            lines = value.split('\n')
                            if len(lines) > 1:
                                print(f"  {lines[0]}")
                                for line in lines[1:]:
                                    print(f"  {line}")
                            else:
                                print(f"  {value}")
                        else:
                            print(f"  {value}")
                    else:
                        print(f"- {key}: {item}")
            else:
                print("  No entries yet.")
            print()


def main():
    """Run the autonomous agent network example."""
    print("=== Autonomous LangGraph Agent Network Example ===")
    print("This example demonstrates agents autonomously deciding how to collaborate,")
    print("without hardcoded interaction patterns.")
    
    # Create the autonomous agent network
    network = AutonomousAgentNetwork()
    network.create_network()
    
    # Menu for different options
    while True:
        print("\n=== Autonomous Agent Network Menu ===")
        print("1. Research a topic")
        print("2. View the workspace")
        print("3. Exit")
        
        choice = input("\nSelect an option (1-3): ")
        
        if choice == "1":
            topic = input("Enter a research topic: ")
            network.research_topic(topic)
            
        elif choice == "2":
            network.show_workspace()
            
        elif choice == "3":
            print("Exiting the Autonomous Agent Network Example. Goodbye!")
            break
            
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()