
## Django settings
from django.conf import settings
import logging
import os

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal

import sqlite3

from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt
from langgraph.graph import StateGraph, END

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver


from langchain_core.messages import RemoveMessage


from langgraph.errors import NodeInterrupt


## Our files

from ..shared_resources.shared_types_and_classes import State

from .agents_tools import (co2_price_check,
                           chemicals_emission_calculator,
                           substitution_carbon_credits_value,
                           GWP_check
                           )

from .prompts import (agent_system_prompt_type_1,
                     agent_system_prompt_type_2, 
                     triage_agent_system_prompt
                     )

from .utils import customize_function_create_prompt



## logger instance for this module
logger = logging.getLogger(f'langgraph_agents.cccalc.agents_setup')


#################################################
## THE GRAPH / WORKFLOW of this specific agent
#################################################


def cccalc_workflow_graph_setup(interaction_thread_id):
    """
    Set up the graphs / workflow
    """
    
    ########### Set up ReAct agents, if any ##########

    calculation_agent = setup_calculation_agent()


    # Use this for dev time, or if only 1 worker, using a single uvicorn worker and in-RAM memory
    # memory = MemorySaver()

    ########### Set up the workflow ###########
    logger.info(f"Setting up graph")

    # Get DB URI from settings
    db_settings = settings.DATABASES['default']
    DB_URI = f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}?sslmode=disable"
    # Create fresh checkpointer for this request
    with PostgresSaver.from_conn_string(DB_URI) as checkpointer:

        workflow = StateGraph(State)
    
        # Add nodes - use the processed agent directly
        # Note: agents that return Command do not need a conditional edge
        
        workflow.add_node("triage", triage_router)
        workflow.add_node("information_gatherer_agent", information_gatherer_agent)
        workflow.add_node("calculation_agent", calculation_agent)

        workflow.add_node("chat_agent_1", chat_agent_1)

        # Non routing agents:
        workflow.add_edge("calculation_agent", "triage")

        # Special case: add an edge to itself so the chat agent can loop back after an interrupt
        # only to be used for testing the agent only, etc. not for practical cases
        #workflow.add_edge("chat_agent_1", "chat_agent_1")
        workflow.add_conditional_edges("chat_agent_1", chat_agent_1_router,{
            "information_gatherer_agent": "information_gatherer_agent",
            "triage": "triage",
            "chat_agent_1": "chat_agent_1"
            }
        )

        # Routing agents: no edges needed (return Command objects)
        # - triage_router returns Command
        # - information_gatherer_agent returns Command (triage, chat_agent_1 or self)
        # - chat_agent_1 returns Command (information_gatherer_agent - the 'caller_node' or self)
        # - handle_user_response returns a Command back to chat_agent_1 

    
        # Set entry point
        workflow.set_entry_point("triage")

        # create the workflow object
        #cccalc_graph = workflow.compile(checkpointer=memory)
        # If the graph comes to chat_agent_1, it will be interrupted for input or simply go back to caller
        #cccalc_graph = workflow.compile(interrupt_after=["chat_agent_1"] , checkpointer=memory)
        cccalc_graph = workflow.compile(checkpointer=checkpointer)

        # Create checkpoint config
        checkpoint_config = {"configurable": {"thread_id": str(interaction_thread_id)}}

        yield cccalc_graph, checkpoint_config



###############################################################
#### Calculation agent
###############################################################
def setup_calculation_agent():
    """
    Sets up the calculation agent
    """

    logger.info("setting up the calculation agent")

    tools=[chemicals_emission_calculator, substitution_carbon_credits_value]

    calculation_agent_system_prompt = agent_system_prompt_type_1.format(
        role = 'You are an expert in CO2 emissions calculations.',
        tools = """
        1. chemicals_emission_calculator: calculates the annual emissions of a specific chemical; it expects the following
        Formats and inputs for chemicals_emission_calculator:
        - chemical_name: str - the chemical's name
        - annual_volume_ton: float - annual production volume
        - production_footprint_per_ton: float - the CO2 footprint per ton of produced chemical
        - transportation: list[dict] - a list of dictionaries for each transportation step, including distances in km and the respective transportation mode (road, train, ship or air), for instance [{'step':1, 'distance':50, 'mode':'road'}, {'step':2, 'distance':250, 'mode':'rail'}]
        - release_to_atmosphere_ton_p_a: float - how much of the chemical is released to the atmosphere in a year
        - gwp_100: float - the GWP100 value

        2. substitution_carbon_credits_value: calculates the economical value and change in emissions when substituting the baseline chemical by the focus chemical
        Formats and inputs for substitution_carbon_credits_value:
        - total_annual_emission_focus_chemical: float - total annual emission of the focus chemical in tons
        - total_annual_emission_baseline_chemical: float - total annual emission of the baseline chemical in tons
        - co2_price: float - current CO2 price per ton
        """,
        instructions = """
        Use the tools as appropriate. Pay attention on correctly formatting the inputs that the tools need. 
        Once you finished your calculations, the result back to the triage agent.
        """
    )

    # instantiate system prompt function and agent
    create_prompt = customize_function_create_prompt(calculation_agent_system_prompt)
    calculation_agent = create_react_agent(
        "openai:gpt-4o",
        tools=tools,
        prompt=create_prompt,
    )

    return calculation_agent





###############################################################
#### Information gatherer agent
###############################################################
class ToolCall(BaseModel):
    name: Literal["co2_price_check", "GWP_check"]
    #args: Dict[str, Any] = Field(default_factory=dict)
    args: str = Field(default_factory=str)

class InformationGathererRouter(BaseModel):
    """Information gatherer with routing decisions"""
    
    reasoning: str = Field(
        description="Step-by-step reasoning about what information is needed"
    )
    
    tool_calls: Optional[List[ToolCall]] = Field(
        default_factory=list,
        description="Tools to calls, including tool name and respective parameters.")
    
    chat_instructions: str = Field(
        description="Instructions for chat agent if user interaction is needed")
    
    collected_data_summary: str = Field(
        description="Summary of all information collected so far"
    )
    
    classification: Literal["use_tools", "need_user_input", "information_complete"] = Field(
        default="need_user_input",
        description="""
        Next action:
        'use_tools' - call tools to gather more information
        'need_user_input' - route to chat agent for user interaction  
        'information_complete' - route back to triage with complete data
        """
    )


def information_gatherer_agent(state: State) -> Command[str]:
    """
    Hybrid information gatherer that can use tools or route to chat
    'Debugging' version
    """
    
    logger.info("Starting information_gatherer_agent")
    
    try:
        llm = init_chat_model("openai:gpt-4o")
        structured_llm = llm.with_structured_output(InformationGathererRouter, method="function_calling")
        
        # Get current state
        collected_data_state = state.get("collected_data", "")
        
        system_prompt = triage_agent_system_prompt.format(
            role='You gather information about chemical emissions.',

            background = """You are a valued member a team of expert agents in CO2 emissions and carbon credits. 
            Your responsibility is to interact with the user and obtain information that other agents need 
            to proceed with their work. 
            """,
                    
            instructions=f"""
            Collect information about:
            1. Chemical name or abbreviation
            2. Annual production volume (tons)
            3. Global Warming Potential (GWP 100)
            4. GHG footprint per ton produced (tons)
            5. Transportation details (distances, modes)
            6. Atmospheric release (tons/year)
            7. Current CO2 price
            
            Current collected data: {collected_data_state}
            
            Decide your next action:

            - If you can get missing info with tools, specify which tools to call
            These tools are available:
            1. co2_price_check: gets the latest CO2 price per ton, useful for carbon credits economic value calculation.
            args: none

            2. GWP_check: provides a value for a chemical's Global Warming Potential (GWP) over 100 years.
            args: the chemical's name

            - If you need user input, specify what questions to ask

            - If you have everything needed, mark as complete
            """,
            
            rules="""
            - Prioritize tools over user questions
            - Only ask users for info not available through tools
            - Be specific about what information is missing
            """
        )
        
        # Get the decision
        message_for_llm = [{"role": "system", "content": system_prompt}] + state["messages"]
        logger.info("About to call structured LLM")
        result = structured_llm.invoke(message_for_llm)
        logger.info(f"Structured LLM returned classification: {result.classification}")
        
        if result.classification == "use_tools":
            
            logger.info(f"Tool calls received: {result.tool_calls}")
            
            # Execute the specified tools
            tool_results = ""
            tool_used_str = "Used tools: "

            for tool_call in result.tool_calls:
                tool_name = tool_call.name
                tool_args = tool_call.args
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                
                try:
                    if tool_name == "co2_price_check":
                        logger.info("Calling co2_price_check()")
                        tool_result = co2_price_check()
                        logger.info(f"co2_price_check returned: {tool_result}")
                        
                    elif tool_name == "GWP_check":
                        logger.info(f"Calling GWP_check with: {str(tool_args)}")
                        tool_result_tuple = GWP_check(str(tool_args))
                        logger.info(f"GWP_check returned: {tool_result_tuple}")
                        
                        if tool_result_tuple[0] == "found":
                            tool_result = tool_result_tuple[1]
                        else:
                            tool_result = f"No GWP value available for this chemical in this database."
                    
                    else:
                        tool_result = f"Unknown tool: {tool_name}"
                        
                    logger.info(f"Tool {tool_name} completed successfully with result: {tool_result}")
                    
                    # Add results to collected data
                    tool_results = tool_results + f"\nThe tool {tool_name} provided this result: {tool_result}"
                    tool_used_str = tool_used_str + f"{tool_name}, "
                    
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
                    logger.error(f"Exception type: {type(e)}")
                    logger.error(f"Exception args: {e.args}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    
                    tool_result = f"Error executing {tool_name}: {str(e)}"
                    tool_results = tool_results + f"\nThe tool {tool_name} encountered an error: {tool_result}"
                    tool_used_str = tool_used_str + f"{tool_name} (failed), "
            
            logger.info("All tools executed, preparing response")
            
            # The tool results are now part of the collected data
            collected_data_summary = result.collected_data_summary + tool_results

            # Stay in information_gatherer to continue gathering
            goto = "information_gatherer_agent"
            update = {
                "messages": [{"role": "assistant", "content": tool_used_str}],
                "collected_data": collected_data_summary
            }
            
            logger.info(f"Returning Command with goto: {goto}")
            
        elif result.classification == "need_user_input":
            logger.info("Classification: need_user_input")
            # Route to chat agent
            goto = "chat_agent_1"
            update = {
                "messages": [{"role": "assistant", "content": result.chat_instructions}],
                "caller_node": "information_gatherer_agent",
                "instructions": result.chat_instructions,
                "collected_data": result.collected_data_summary
            }
            
        elif result.classification == "information_complete":
            logger.info("Classification: information_complete")
            # Route back to triage
            goto = "triage"
            update = {
                "messages": [{"role": "assistant", "content": "Information gathering complete"}],
                "collected_data": result.collected_data_summary
            }
        
        else:
            raise ValueError(f"Invalid classification: {result.classification}")
        
        logger.info("information_gatherer_agent completed successfully")
        return Command(goto=goto, update=update)
        
    except Exception as e:
        logger.error(f"CRITICAL ERROR in information_gatherer_agent: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        # Re-raise to fail the workflow visibly
        raise



def information_gatherer_agent_v0(state: State) -> Command[str]:
    """
    Hybrid information gatherer that can use tools or route to chat
    """
    
    llm = init_chat_model("openai:gpt-4o")
    structured_llm = llm.with_structured_output(InformationGathererRouter, method="function_calling")
    #structured_llm = llm.with_structured_output(InformationGathererRouter)
    
    # Get current state
    collected_data_state = state.get("collected_data", "")
    
    system_prompt = triage_agent_system_prompt.format(
        role='You gather information about chemical emissions.',

        background = """You are a valued member a team of expert agents in CO2 emissions and carbon credits. 
        Your responsibility is to interact with the user and obtain information that other agents need 
        to proceed with their work. 
        """,
                
        instructions=f"""
        Collect information about:
        1. Chemical name or abbreviation
        2. Annual production volume (tons)
        3. Global Warming Potential (GWP 100)
        4. GHG footprint per ton produced (tons)
        5. Transportation details (distances, modes)
        6. Atmospheric release (tons/year)
        7. Current CO2 price
        
        Current collected data: {collected_data_state}
        
        Decide your next action:

        - If you can get missing info with tools, specify which tools to call
        These tools are available:
        1. co2_price_check: gets the latest CO2 price per ton, useful for carbon credits economic value calculation.
        args: none

        2. GWP_check: provides a value for a chemical's Global Warming Potential (GWP) over 100 years.
        args: the chemical's name

        - If you need user input, specify what questions to ask

        - If you have everything needed, mark as complete
        """,
        
        rules="""
        - Prioritize tools over user questions
        - Only ask users for info not available through tools
        - Be specific about what information is missing
        """
    )
    
    # Get the decision
    message_for_llm = [{"role": "system", "content": system_prompt}] + state["messages"]
    result = structured_llm.invoke(message_for_llm)
    
    if result.classification == "use_tools":
        
        logger.info(f"Tool calls received: {result.tool_calls}")
        
        # Execute the specified tools
        tool_results = ""
        tool_used_str = "Used tools: "

        for tool_call in result.tool_calls:
            tool_name = tool_call.name
            tool_args = tool_call.args
            
            try:
                if tool_name == "co2_price_check":
                    tool_result = co2_price_check()
                    
                elif tool_name == "GWP_check":
                    tool_result_tuple = GWP_check(str(tool_args))
                    
                    if tool_result_tuple[0] == "found":
                        tool_result = tool_result_tuple[1]
                    else:
                        tool_result = f"No GWP value available for this chemical in this database."
                
                else:
                    tool_result = f"Unknown tool: {tool_name}"
                    
                # Add results to collected data
                tool_results = tool_results + f"\nThe tool {tool_name} provided this result: {tool_result}"
                tool_used_str = tool_used_str + f"{tool_name}, "
                
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                tool_result = f"Error executing {tool_name}: {str(e)}"
                tool_results = tool_results + f"\nThe tool {tool_name} encountered an error: {tool_result}"
                tool_used_str = tool_used_str + f"{tool_name} (failed), "
        
        
        # The tool results are now part of the collected data
        collected_data_summary = result.collected_data_summary + tool_results

        # Stay in information_gatherer to continue gathering
        goto = "information_gatherer_agent"
        update = {
            "messages": [{"role": "assistant", "content": tool_used_str}],
            "collected_data": collected_data_summary
        }
        
    elif result.classification == "need_user_input":
        # Route to chat agent
        goto = "chat_agent_1"
        update = {
            "messages": [{"role": "assistant", "content": result.chat_instructions}], # persists in the state during chat's run
            "caller_node": "information_gatherer_agent",
            "instructions": result.chat_instructions,  # becomes part of the system prompt
            "collected_data": result.collected_data_summary
        }
        
    elif result.classification == "information_complete":
        # Route back to triage
        goto = "triage"
        update = {
            "messages": [{"role": "assistant", "content": "Information gathering complete"}],
            "collected_data": result.collected_data_summary
        }
    
    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    
    return Command(goto=goto, update=update)




###############################################################
#### simple chat agent
###############################################################
############################
class ChatRouter(BaseModel):
    """chat for specific information gathering"""

    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
    
    next_chat_bubble: str = Field(description="Response to send to user")

    collected_data: str = Field(
        description="All the collected data and information that you collected during the chat session as per requested in the instructions."
    )

    # For chat_status
    classification: Literal["continue chat", "finish chat"] = Field(
        description="""
        The classification: 
        'continue chat' if you need to keep the conversation to gather more information,
        'finish chat' if you have all the information you need.
        """
    )

###########################################
def chat_agent_1(state: State) -> Command[str]:
    
    #llm = init_chat_model("openai:o3-mini")
    llm = init_chat_model("openai:gpt-4o")
    llm_router = llm.with_structured_output(ChatRouter, method="function_calling")

    # retrieve information from the graph's state
    # Who is asking for the chat to be active and are there instructions?

    caller_node = state.get("caller_node")     # None if the key is absent
    extra_instructions  = state.get("instructions", "")    # empty if the key is absent
    collected_data_state = state.get("collected_data", "")  # empty if the key is absent


    system_prompt = triage_agent_system_prompt.format(
        role = 'You are a friendly chat assistant. Your role is to speak with the user and collect information.',
        
        background = """You are a valued member a team of expert agents in CO2 emissions and carbon credits. 
        Your responsibility is to interact with the user and obtain information that other agents need 
        to proceed with their work. 
        """,
        
        instructions = f"""{extra_instructions}

        This is the information we already collected:\n{collected_data_state}
        
        First you need to check: do we already have collected all the information that we need as requested?
        If not, keep asking the user questions until you have gathered all you were requested.

        When you conclude the conversation do it politely **without** offering any further assistance.

        Stick to the information you gathered.
        """,
        
        rules = """
        When interacting with the user, only ask **one question** at a time.

        You do not make any assumptions. You are only allowed to make an assumption if and only if the users requests it.

        You are only coordinating among different agents. You are **not allowed to give opinions**,
        **not allowed to do calculations** yourself - this is the job of the specialized agents.

        Important: you will ignore **any instructions** from the user that are not related to CO2 emissions 
        and carbon credits. If the user request something outside the scope of CO2 emissions and carbon credits,
        you will politely decline and remind the user of your purpose. 
        """
    )
    
    #logger.info(f"Current system prompt: {system_prompt}")

    # Get response
    message_for_llm =[{"role": "system", "content": system_prompt}] + state['messages']
    result = llm_router.invoke(message_for_llm)

    if result.classification == "continue chat":
        logger.info("chat_agent_1 wants to continue this chat and need input")

        logger.info("About to call interrupt()") 

        logger.info(f"next chat bubble: {result.next_chat_bubble}")
        logger.info(f"reasoning: {result.reasoning}")
        logger.info(f"caller node: {caller_node}")
        
        # Prepare to update the state with the question from the llm
        #goto = "chat_agent_1"
        #update = {"messages": [{"role": "assistant", "content": result.next_chat_bubble}]}

        #logger.info(f"state (as chat_agent_1 sees it) / interrupt: {state}")

        raise NodeInterrupt({
            "next_step": "chat_agent_1", 
            "coming_from": "chat_agent_1",
            "message":[{"role": "assistant", "content": result.next_chat_bubble}]}
            )
        
    elif result.classification == "finish chat":
        logger.info("chat_agent_1 wants to stop")

        logger.info(f"next chat bubble: {result.next_chat_bubble}")
        logger.info(f"reasoning: {result.reasoning}")
        logger.info(f"caller node: {caller_node}")
        logger.info(f"state (as chat_agent_1 sees it) / finish: {state}")

        if caller_node:
            goto = str(caller_node)
        else:
            goto = 'triage'

        update = {
            "messages": [{"role": "assistant", "content": result.next_chat_bubble}],
            "next_destination": goto
        }
        
        return Command(goto=goto, update=update)
    
    else:
        raise ValueError(f"Invalid classification: {result.classification}")


def chat_agent_1_router(state: State):
    next_dest = state.get("next_destination", "triage")
    # defensive code: if for some reason the next_destination key results in an empty string, go to triage
    return next_dest if next_dest else "triage"
    



###############################################################
#### Triage agent
###############################################################
class TriageRouter(BaseModel):
    """Analyze the information provided and route it according to its content."""

    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
    classification: Literal["gather information", "calculate", 
                            "respond and conclude"] = Field(description="""
        The classification:
        'gather information' for gathering information necessary for calculations,
        'calculate' if you collected all the necessary information needed for the calculations,
        'respond and conclude' if you are ready to provide user an response to their request and conclude the conversation.
        """
    )
    response: str = Field(
        description="A response to the user's request; if intermediate step (response not yet fully ready), just state 'working on it'."
    )

###########################################

def triage_router(state: State) -> Command[Literal["calculation_agent", 
                                                   "information_gatherer_agent",
                                                   "__end__"]]:
    
    #llm = init_chat_model("openai:o3-mini")
    llm = init_chat_model("openai:gpt-4o")
    llm_router = llm.with_structured_output(TriageRouter)

    formated_triage_agent_system_prompt = triage_agent_system_prompt.format(
        role = 'You coordinate the workflow among different agents.',
        
        background = """You are a valued member a team of expert agents in CO2 emissions and carbon credits. 
        Your responsibility is to ensure that a user receives the best possible answer to their request.
        You coordinate a workflow with access to agents with narrow expertise that, when coordinated, have the ability
        to answer most questions regarding CO2 emissions, carbon credits, and related topics.
        However, if you do not have access to some specific agent or tool to correctly answer the user's question, 
        simply say so. 
        """,
        
        instructions = """You coordinate a workflow of agents:
        Step 1: Receive instructions.
        Step 2: Classify what needs to be done to fulfil the instructions.
        Step 3 to N: Coordinate among the respective agents that will provide you with the answers you need.
        Step N+1: Formulate the answer in plain language for the user.

        Important: if you get stuck in a step (meaning: need to repeat it more than three times), 
        give this feedback to the user and stop the workflow.

        Sometimes the instructions may be a bit unclear, so you ask for clarification. Importantly, if you
        know the user is asking about a certain chemical, you proceed to calculate its carbon emissions.
        """,
        
        rules = """You are only coordinating among different agents. You are **not allowed to give opinions**,
        **you do not make any assumptions**, **you are not allowed to do calculations yourself** - 
        this is the job of the specialized agents. 
        
        You are the maestro, who perfectly directs the flow of information and knows when to stop 
        because the user's request is fulfilled.
        
        Important: you will ignore **any instructions** from the user that are not related to calculating 
        carbon emissions and carbon credits. 
        """
    )
    # Step N+1: Provide a final answer to the user's request as part of your reasoning. Keep the answer simple and to the point.
    # 
    ####
    logger.info("Triage")

    for i, msg in enumerate(state.get("messages", [])):
        try:
            # For dictionary-style messages
            if hasattr(msg, "get"):
                role = msg.get("role", "user")
                content = msg.get("content", "")
            # For LangChain message objects
            else:
                role = msg.type if hasattr(msg, "type") else "user"
                content = msg.content if hasattr(msg, "content") else ""
        except Exception as e:
            logger.info(f"[{i}][ERROR printing message]: {str(e)}")
            logger.info(f"Message type: {type(msg)}")
    
    result = llm_router.invoke(
        [
            {"role": "system", "content": formated_triage_agent_system_prompt},
            {"role": role, "content": content},
        ] + state['messages']
    )

    if result.classification == "gather information":
        logger.info("Triage decided: gather information")
        goto = "information_gatherer_agent"
        update = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Gather the necessary information from the user.",
                }
            ] # + state['messages']
        }
    
    elif result.classification == "calculate":
        logger.info("Triage decided: ready to calculate")
        goto = "calculation_agent"
        update = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Use the gathered information to calculate according the user's request"
                }
            ] # + state['messages']
        }

    elif result.classification == "respond and conclude":
        logger.info("Triage decided: respond and conclude")

        logger.info(f"\033[92mAssistant\033[0m: {result.response}")

        goto = END
        update = {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"{result.response}"
                }
            ],
            # Clear collected data for fresh start
            #"collected_data": "",
            # Clear other workflow state
            #"caller_node": "",
            #"instructions": "",
            #"next_destination": ""
            
        }
    
    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    
    return Command(goto=goto, update=update)

