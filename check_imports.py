import sys
print(f"Python path: {sys.path}")

try:
    import autogen
    print(f"autogen is installed (version: {autogen.__version__})")
    print(f"Contains ConversableAgent? {'ConversableAgent' in dir(autogen)}")
except ImportError:
    print("autogen is not installed")

# Also check for other packages that might be needed
try:
    import openai
    print(f"openai is installed (version: {openai.__version__})")
except ImportError:
    print("openai is not installed")