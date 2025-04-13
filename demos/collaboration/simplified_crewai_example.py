"""
Example of using the one-line MCP integration with CrewAI agents.
"""

import os
from crewai import Agent as CrewAgent
from agent_mcp.mcp_decorator import mcp_agent
 

from crewai import Task

# One-line integration with CrewAI
@mcp_agent(name="ResearchAgent")
class ResearchAgent(CrewAgent):
    def __init__(self):
        super().__init__(
            name="ResearchAgent",
            role="Research Analyst",
            goal="Conduct thorough research on given topics",
            backstory="Expert research analyst with deep analytical skills",
            llm_model="gpt-3.5-turbo",  # Specify the model explicitly
            verbose=True  # Show what the agent is doing
        )
    
    def analyze(self, topic: str) -> str:
        """Analyze a given research topic"""
        task = Task(
            description=f"Analyze the following topic and provide key insights: {topic}",
            expected_output="A detailed analysis with key insights, trends, and potential impacts",
            agent=self
        )
        return self.execute_task(task)

# Create and use the agent
if __name__ == "__main__":
    agent = ResearchAgent()
    result = agent.analyze("AI trends in 2025")
    print(f"Analysis result: {result}")
    print(f"Available MCP tools: {agent.mcp_tools.keys()}")
