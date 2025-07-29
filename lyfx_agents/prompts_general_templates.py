

"""
These are very general prompt **templates** for different agents / situations

"""

#################################################
# system prompts
#################################################

#################################################
agent_system_prompt_type_1 = """
< Role >
{role}
</ Role >

< Tools >
You have access to the following tools:
{tools}
</ Tools >

< Instructions >
{instructions}
</ Instructions >
"""


###############################################
agent_system_prompt_type_2 = """
< Role >
{role}
</ Role >

< Tools >
You have access to the following tools:
{tools}
</ Tools >

< Instructions >
{instructions}
</ Instructions >

< Rules >
{rules}
</ Rules >
"""


###############################################
agent_system_prompt_type_3 = """
< Role >
{role}
</ Role >

< Background >
{background}. 
</ Background >

< Tools >
You have access to the following tools:

{tools}
</ Tools >

< Instructions >
{instructions}
</ Instructions >

< Rules >
{rules}
</ Rules >

< Few shot examples >
{examples}
</ Few shot examples >
"""


###############################################
triage_agent_system_prompt = """
< Role >
{role}
</ Role >

< Background >
{background}. 
</ Background >

< Instructions >
{instructions}
</ Instructions >

< Rules >
{rules}
</ Rules >
"""


###############################################
triage_agent_with_examples_system_prompt = """
< Role >
{role}
</ Role >

< Background >
{background}. 
</ Background >

< Instructions >
{instructions}
</ Instructions >

< Rules >
{rules}
</ Rules >

< Few shot examples >
{examples}
</ Few shot examples >
"""

#################################################
# user prompts
#################################################

#################################################
basic_agent_user_prompt = """
< Input from user >
{chatting}
</ Input from user >
"""









