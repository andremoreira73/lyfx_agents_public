######## In this file we put all **programmatic** tools that the cccalc uses

from langchain_core.tools import tool

from pydantic import BaseModel, Field
from typing import Literal

from langchain.chat_models import init_chat_model

#import logging

## our files
from .prompts import (agent_system_prompt_type_1)

from .utils import (list_of_chemicals)


## logger instance for this module
#logger = logging.getLogger(f'langgraph_agents.cccalc.agents_tools')


##########################################################################
# DUMMY TOOLS

# @tool  # removed until we use this really a tool under LangGraph
def co2_price_check() -> float:
    """
    Provides an updated CO2 carbon credits price per ton.
    """
    return 0.5



####################################################################
# The "database" of chemicals
# ##################################################################

############################
class GWPdb(BaseModel):
    """look for specific values in our molecule database"""

    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )

    response: str = Field(
        description="The GWP result"
    )
    
    classification: Literal["not available", "ambiguous", "found"] = Field(
        description="""
        The classification: 
        'not available' if the chemical is not available in the database.
        'ambiguous' if the chemical's name is similar to one or more in the database and you are not sure.
        'found' if the chemical is in the database.
        """
    )

#############################################

# @tool  # removed until we use this really a tool under LangGraph
def GWP_check(chemical_name:str) -> tuple[str, float]:
    """
    A LLM based database of chemicals' GWP values
    
    Args:
        chemical_name: name of the molecule for which the GWP value is needed
    """
    # Initialize the model for chat interaction
    this_model = init_chat_model("openai:gpt-4o")
    #this_model = ChatOpenAI(model="gpt-4o")
        
    # Create a system prompt for tool mode
    GWPdb_system_prompt = agent_system_prompt_type_1.format(
        role = """
        You are a database. Your role is provide the GWP value for a given chemical.
        """,
        tools = "",
        instructions = f"""You are asked to provide the GWP value for the following chemical: {chemical_name}
        
        Below is a list containing chemicals names and their respective GWP values.

        Look in the list for {chemical_name}. If you find an exact match then retrieve its respective GWP value from the list. 
        Respond with this GWP value, and only this GWP value. No other text or value.

        If you do not find the chemical in the list, or the name is similar to some name in the database but 
        you are not absolutely sure they refer to the same chemical, respond with no value.

        ### Here is the list of chemical and their GWP values ###
        {list_of_chemicals}
        """
    )
    
    # Use a router for determining when to end the chat
    this_llm = this_model.with_structured_output(GWPdb)

    messages_for_llm = [{"role": "system", "content": GWPdb_system_prompt}]
    result = this_llm.invoke(messages_for_llm)

    if result.classification == 'found':
        # OK, we have a hit
        this_value = float(result.response) # convert to a float, as we need to send back with this format
        
    elif result.classification == 'ambiguous':
        # no hit or ambiguity - we need the user
        this_value = 0.0
    
    elif result.classification == 'not available':
        # no hit or ambiguity - we need the user
        this_value = 0.0

    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    
    #return (result.reasoning, this_value)
    return (result.classification, this_value)



###########################################################################
@tool
def information_struct() -> str:
    """
    Provides the information gathered about a chemical called SF.
    """
        
    response = """{"chemical_name": "SF",
    "annual_volume_ton": 10000,
    "production_footprint_per_ton": 10,
    "transportation": [{'step':'from production to warehouse', 'distance_km':50, 'mode':'road'},
                       {'step':'from warehouse to departure port', 'distance_km':250, 'mode':'rail'},
                       {'step':'from departure port to destination port', 'distance_km':26000, 'mode':'ship'}],
    "release_to_atmosphere_ton_p_a": 5000,
    "gwp_100":4000,
    "baseline_chemical": "HCN",
    "total_annual_emission_baseline_chemical": 30000000}                    
    """
    return (response)



###########################################################################
@tool
def chemicals_emission_calculator(chemical_name: str,
                                  annual_volume_ton: float, 
                                  production_footprint_per_ton: float,
                                  transportation: list[dict],
                                  release_to_atmosphere_ton_p_a:float,
                                  gwp_100:float) -> tuple[str, float]:
    
    """
    Programmatic emissions calculator for a given chemical
    """

    # Step 1: add up all the steps inside transportation

    # transportation is a list of dictionaries with the format (example):
    # [{'step':1, 'distance':50, 'mode':'road'},
    #  {'step':2, 'distance':250, 'mode':'rail'},
    #  {'step':3, 'distance':26000, 'mode':'ship'},
    # ]
    
    # Average per km emission of CO2e (ton CO2e / ton of cargo and km)
    # refs:
    # rail, road and ship: https://www.eea.europa.eu/data-and-maps/daviz/specific-co2-emissions-per-tonne-2#tab-chart_1
    # air: https://vitality.io/air-freight-vs-sea-freight-carbon-footprint
    transportation_mode_assumptions = {'road':0.00014, 'rail':0.000015, 'train':0.000015, 'ship':0.000136, 'air':0.0005}

    transportation_annual_emission = 0.0
    for transportation_segment in transportation:
        # Run through each step in the logistics, calculate and cumulate the emissions
        this_mode = transportation_segment.get('mode','road') # if all fails, use road for now...
        this_distance = transportation_segment.get('distance', 0.0) # if all fails, it is set to zero
        transportation_annual_emission += int(this_distance) * transportation_mode_assumptions.get(this_mode)


    # Step 2: annual production 
    production_annual_emission = annual_volume_ton * production_footprint_per_ton

    # Step 3: release to the atmosphere (annualized)
    release_annual_emission = release_to_atmosphere_ton_p_a * gwp_100

    total_annual_emission = transportation_annual_emission + production_annual_emission + release_annual_emission

    return (chemical_name, total_annual_emission)


###########################################################################
@tool
def substitution_carbon_credits_value(total_annual_emission_focus_chemical: float,
                             total_annual_emission_baseline_chemical: float,
                             co2_price:float) -> tuple[float, float]:
    """
    Estimates the economic value of a chemical substitution, returns the value in currency and
    the emissions avoided
    """

    change_in_emission = (total_annual_emission_focus_chemical - total_annual_emission_baseline_chemical)
    cc_value = abs(change_in_emission * co2_price)

    if change_in_emission < 0.0:
        return (cc_value, change_in_emission)
    else:
        # no emission reduction - no cc value...
        return (0.0, change_in_emission)







