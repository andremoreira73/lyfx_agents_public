## Here we put some centrally defined types, classes, etc
## so we avoid circular imports at runtime


#### centrally defined classes that we need for the agents (avoid circular references in the code)

#from typing import TypedDict, Annotated
from typing import Annotated
from typing_extensions import TypedDict
from typing import Optional, Dict, Any
from langgraph.graph import add_messages

# shared State for cccalc
class State(TypedDict):
    messages: Annotated[list, add_messages]
    collected_data: Optional[str]  # Store the collected data here
    caller_node: Optional[str]  # Add this to track who called what
    next_destination: Optional[str]  # Add this to track where to go after chat_agent_1
    instructions: Optional[str]  # Add specific instructions
    chat_status : Optional[str]  # for controlling any chat functionality ('continue chat' or 'finish chat')
    

# shared State for chats
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    chat_status : str  # for controlling any chat functionality ('continue chat' or 'finish chat')


