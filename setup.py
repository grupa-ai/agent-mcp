from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agent-mcp",
    version="0.1.1",
    author="Samuel Ekpe",
    description="A bridge agent to enable agents  with Model Context Protocol capabilities to be added to a Multi-agent Collaboration Network (MCN) to run on a Multi-agent Collaboration Platform (MCP)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/geniusgeek/agent-mcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "autogen",
        "langchain",
        "langchain-openai",
        "langchain-community",
        "crewai>=0.11.0",
        "langgraph>=0.0.15",
        "openai>=1.12.0",
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "sse-starlette==1.8.2",
        "firebase-admin==6.4.0",
        "python-multipart==0.0.6",
        "python-dotenv==1.0.0",
        "google-cloud-firestore==2.13.1",
        "aiohttp==3.9.1",
        "duckduckgo-search==4.1.1"
    ],
    entry_points={
        'console_scripts': [
            'mcp-agent=autonomous_agent_workflow:main',
        ],
    },
)