from setuptools import setup, find_packages
import os

def find_package_data(package, data_dirs):
    """Find package data files"""
    walk = [(dirpath.replace(package + os.sep, '', 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)
            if not any(part.startswith(('.', '_')) for part in dirpath.split(os.sep))]
    file_list = []
    for path, filenames in walk:
        for filename in filenames:
            if not filename.endswith(('.pyc', '.pyo', '.so', '.dll', '.pyd', '.pyx')):
                file_list.append(os.path.join(path, filename))
    return file_list

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Get dependencies from pyproject.toml
with open("pyproject.toml", "r") as f:
    pyproject = f.read()
    dependencies = []
    in_deps = False
    for line in pyproject.split('\n'):
        if 'dependencies' in line:
            in_deps = True
            continue
        if in_deps and ']' in line:
            break
        if in_deps and '=' in line and not line.strip().startswith('#'):
            dep = line.strip().strip(' ",')
            if dep:  # Only add non-empty dependencies
                dependencies.append(dep)

# Explicitly define packages to include
packages = find_packages(exclude=[
    "tests*", 
    "docs*",
    "examples*",
    "venv*",
    ".venv*",
    "*venv*",
    "build*",
    "dist*",
    "*.egg-info*",
])

setup(
    name="agent-mcp",
    version="0.1.4",
    author="GrupaAI",
    description="A bridge agent to enable agents with Model Context Protocol capabilities to be added to a Multi-agent Collaboration Network (MCN) to run on a Multi-agent Collaboration Platform (MCP)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/grupa-ai/agent-mcp",
    packages=packages,
    package_data={
        'agent_mcp': find_package_data('agent_mcp', ['*.py', '*.json', '*.yaml', '*.yml']),
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'mcp-agent=agent_mcp.cli:main',
        ],
    },
    zip_safe=False,
)