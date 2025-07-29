
from langgraph_agents.chat_general.agents_for_chat import (
    chat_assistant_setup_graph,
    chat_assistant_v2_setup_graph,
    chat_assistant_v3_setup_graph,
    chat_assistant_v4_setup_graph,
)
import os, json

# directory and filenames with API keys
OAI_KEY_FILE = "/home/memology/Documents/keys/OpenAI_keys_swarm.json"

LS_KEY_FILE = "/home/memology/Documents/keys/LangSmith_key_2.json"

TAVILY_KEY_FILE = "/home/memology/Documents/keys/Tavily_k1.json"



def terminal_chat():

    def stream_graph_updates(chat_graph, config, user_input: str):
        events = chat_graph.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config,
            stream_mode="values",
            )
        for event in events:
            event["messages"][-1].pretty_print()


    initialize_api_keys_testing()
    chat_graph = chat_assistant_v4_setup_graph()

    config = {"configurable": {"thread_id": "1"}}

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q", "bye"]:
                print("Goodbye!")
                break
            stream_graph_updates(chat_graph, config, user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(chat_graph, config, user_input)
            break



########## workaround to initialize keys without django

def initialize_api_keys_testing():
    """Initialize API keys once at server startup"""

    # Get OpenAI key
    key_file = OAI_KEY_FILE
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                os.environ["OPENAI_API_KEY"] = api_data.get('key', '')
        except Exception as e:
            print(f"Error loading OpenAI API key: {e}")
    
    # Get Tavily key
    key_file = TAVILY_KEY_FILE
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                os.environ["TAVILY_API_KEY"] = api_data.get('key', '')
        except Exception as e:
            print(f"Error loading Tavily API key: {e}")
    
    # LangSmith keys and params
    key_file = LS_KEY_FILE
    if os.path.exists(key_file):
        try:
            with open(key_file, 'r') as file:
                api_data = json.load(file)
                os.environ["LANGSMITH_ENDPOINT"] = api_data.get('endpoint', '')
                os.environ["LANGCHAIN_API_KEY"] = api_data.get('key', '')
        except Exception as e:
            print(f"Error loading LangSmith API key: {e}")

    # Set LangSmith tracing settings - use getattr with defaults
    langsmith_tracing_bool = 'true'
    langsmith_project = 'lyfx_agents_testing'
    
    os.environ["LANGCHAIN_TRACING_V2"] = langsmith_tracing_bool
    os.environ["LANGCHAIN_PROJECT"] = langsmith_project
    
    return





if __name__ == "__main__":
    terminal_chat()