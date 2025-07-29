
## Here we put the execution functions that act as an interface between the graph(s) and the API calls

import os
import json
from typing import Dict, Any, List
import logging

from langgraph.types import Command
from langgraph.errors import NodeInterrupt

from .agents_setup import get_lyras_graph

## logger instance for this module
logger = logging.getLogger(f'langgraph_agents.lyras.agent_adapter_APIs')



##############################
def adapt_messages_format(api_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert API-format messages to LangGraph format"""
    langgraph_messages = []
    for msg in api_messages:
        langgraph_messages.append({
            'role': msg.get('role', 'user'),
            'content': msg.get('content', '')
        })
    return langgraph_messages



##################################################################
def execute_lyras_workflow(initial_state, interaction_thread_id):
    """Execute the lyras workflow, accounts for possible interruptions for human input.
    """

    logger.info(f"Executing lyras workflow for thread: {interaction_thread_id}")
    
    # Extract messages from initial_state (like cccalc does)
    if 'messages' in initial_state:
        msg = initial_state['messages']
    else:
        # Fallback if called differently
        msg = [{'role': 'user', 'content': str(initial_state)}]
   
    # Run the workflow

    logger.info(f"thread_id: {str(interaction_thread_id)}")

    # Note that get_lyras_graph does not "return", it "yields", so we use it as a proper generator
    gen = get_lyras_graph(interaction_thread_id)
    lyras_graph, checkpoint_config = next(gen)
    
    try:
        result = lyras_graph.invoke({"messages": msg}, checkpoint_config)

        state_snapshot = lyras_graph.get_state(checkpoint_config)
        logger.info(f"state_snapshot (execute) as we come back in: {state_snapshot}")

        message_from_llm = state_snapshot.values.get('messages', [])[-1].content

        # Note that for lyras, each interaction is running the graph once; so it is, in a sense, always interrupted
        return_dict = {
                "status": "interrupted",
                "interrupt_data": {"message": message_from_llm}
                }


        state_snapshot = lyras_graph.get_state(checkpoint_config)
        logger.info(f"state_snapshot (execute) as we leave it: {state_snapshot}")
    except Exception as e:
        logger.error(f"graph execution with error {e}")
    finally:
        # Clean up the generator (closes the context)
        gen.close()

    return return_dict




