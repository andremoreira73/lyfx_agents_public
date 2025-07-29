
## Here we put the execution functions that act as an interface between the graph(s) and the API calls

from typing import Dict, Any, List
import logging

from .agents_setup import cccalc_workflow_graph_setup

## logger instance for this module
logger = logging.getLogger(f'langgraph_agents.cccalc.agent_adapter_APIs')


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
def execute_cccalc_workflow_kwargs(interaction_thread_id, **kwargs):
    """Execute the CO2 calculator workflow, accounts for possible interruptions for human input.
    --> Placeholder for future code"""
    pass
    


##################################################################
def execute_cccalc_workflow(initial_state, interaction_thread_id):
    """Execute the CO2 calculator workflow, accounts for possible interruptions for human input."""

    logger.info(f"Executing cccalc workflow for thread: {interaction_thread_id}")
        
    # Adapt the message format if needed
    if 'messages' in initial_state:
        initial_state['messages'] = adapt_messages_format(initial_state['messages'])
    
    # Run the workflow

    logger.info(f"thread_id: {str(interaction_thread_id)}")

    # Note that get_lyras_graph does not "return", it "yields", so we use it as a proper generator
    gen = cccalc_workflow_graph_setup(interaction_thread_id)
    cccalc_graph, checkpoint_config = next(gen)
    
    try:

        result = cccalc_graph.invoke(initial_state, checkpoint_config)

        state_snapshot = cccalc_graph.get_state(checkpoint_config)
        logger.info(f"state_snapshot (execute) as we come back in: {state_snapshot}")
    
        next_destination = state_snapshot.values.get("next_destination", "chat_agent_1") 
        # meaning: if chat_agent_1 set a Command, it passes this; otherwise, it just interrupted again, 
        # so it goes back to it

        if state_snapshot.interrupts:

            # There was an interruption, so the llm needs input
            coming_from = result["__interrupt__"][0].value["coming_from"]
            next_step = result["__interrupt__"][0].value["next_step"]
            message_from_llm = result["__interrupt__"][0].value["message"]

            logger.info(f"interrupt values: {coming_from} // {next_step} // {message_from_llm}")

            # update the state here before sending the message to the API
            new_cfg = cccalc_graph.update_state(
                config=checkpoint_config,                
                values={"messages": message_from_llm, "next_destination": next_destination},
                as_node="chat_agent_1")  #
            
            return_dict = {
                "status": "interrupted",
                "interrupt_data": {"message": message_from_llm}
                }
        else:
            # no interrupt means it finished the execution without further questions
            #result = cccalc_graph.invoke(initial_state, checkpoint_config)
            state_snapshot = cccalc_graph.get_state(checkpoint_config)
            message_from_llm = state_snapshot.values['messages'][-1].content

            logger.info(f"message_from_llm: {message_from_llm}")

            return_dict = {
                "status": "completed",
                "interrupt_data": {"message": message_from_llm}
                }        

        state_snapshot = cccalc_graph.get_state(checkpoint_config)
        logger.info(f"state_snapshot (execute) as we leave it: {state_snapshot}")
    except Exception as e:
        logger.error(f"graph execution with error {e}")
    finally:
        # Clean up the generator (closes the context)
        gen.close()

    return return_dict



#########################################################################
def resume_cccalc_workflow(user_input, interaction_thread_id):
    """Resume the workflow from a checkpoint with user input"""

    logger.info(f"Resuming cccalc workflow for thread: {interaction_thread_id}")


    # Note that get_lyras_graph does not "return", it "yields", so we use it as a proper generator
    gen = cccalc_workflow_graph_setup(interaction_thread_id)
    cccalc_graph, checkpoint_config = next(gen)

    state_snapshot = cccalc_graph.get_state(checkpoint_config)
    
    logger.info(f"state_snapshot (resume) before resuming: {state_snapshot}")

    # ready to restart: prepare the relevant updates
    collected_data_for_update = f"""
    {state_snapshot.values["collected_data"]} 
    To the question: {state_snapshot.values['messages'][-1].content} the user answered {user_input}
    """
    
    # Keep as reference: doing this runs the FULL graph from the start point with the updated state
    #result = cccalc_graph.invoke(state_update, config=checkpoint_config, )

    next_destination = state_snapshot.values.get("next_destination", "chat_agent_1") 
    # meaning: if chat_agent_1 set a Command, it passes this; otherwise, it just interrupted again, 
    # so it goes back to it

    logger.info(f"next destination from resuming: {next_destination}")

    values_update = {"messages": [{"role": "user", "content": user_input}],
                    "collected_data": collected_data_for_update,
                    "next_destination": next_destination
                    }
    
    new_cfg = cccalc_graph.update_state(
        checkpoint_config,                
        values = values_update,
        as_node = "chat_agent_1")
    
    try:
        result = cccalc_graph.invoke(None, new_cfg)
        logger.info(f"result: {result}")

        state_snapshot = cccalc_graph.get_state(checkpoint_config)

        # this will now re-enter through chat_agent_1, and continue the conversation, 
        # until the next interrupt happens or it finishes the workflow
        if state_snapshot.interrupts:

            # There was an interruption, so the llm needs input
            coming_from = result["__interrupt__"][0].value["coming_from"]
            next_step = result["__interrupt__"][0].value["next_step"]
            message_from_llm = result["__interrupt__"][0].value["message"]

            logger.info(f"interrupt values: {coming_from} // {next_step} // {message_from_llm}")

            # update the state here before sending the message to the API
            new_cfg = cccalc_graph.update_state(
                config=checkpoint_config,                
                values={"messages": message_from_llm},
                as_node="chat_agent_1")  #
            
            return_dict = {
                "status": "interrupted",
                "interrupt_data": {"message": message_from_llm}
                }

        else:
            # no interrupt or got END: it finished the execution without further questions

            message_from_llm = state_snapshot.values['messages'][-1].content

            logger.info(f"message_from_llm: {message_from_llm}")

            return_dict = {
                "status": "completed",
                "interrupt_data": {"message": message_from_llm}
                }
        
        state_snapshot = cccalc_graph.get_state(checkpoint_config)
        logger.info(f"state_snapshot (resume) as we leave it: {state_snapshot}")
    except Exception as e:
        logger.error(f"graph execution with error {e}")
    finally:
        # Clean up the generator (closes the context)
        gen.close()

    return return_dict


