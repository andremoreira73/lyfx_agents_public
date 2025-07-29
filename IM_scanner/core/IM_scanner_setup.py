
import operator
import logging

from typing import (List, Optional, TypedDict, 
                    Literal, Annotated
                    )

from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END, START
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.constants import Send


# our files #
from .IM_scanner_tools import scrape_website
from .IM_scanner_targets import targets

from lyfx_agents.prompts_general_templates import agent_system_prompt_type_2


## logger instance for this module
logger = logging.getLogger(f'IM_scanner.IM_scanner_setup')



########### Classes ###############

### STRUCTURED LLM RESPONSES (pydantic)

class IMJobs(BaseModel):
    job_title: str = Field(description="Job title")
    company: str = Field(description="Company name") 
    location: str = Field(description="Job location")
    description_summary: str = Field(description="Brief summary of job description")
    apply_url: str = Field(description="URL to apply for the job")


class PageResponse(BaseModel):
    """Response format from the ReAct agent"""
    page_type: Literal["job_list", "job_posting", "not_relevant"] = Field(
        description="Type of page analyzed"
    )
    IM_relevant: bool = Field(
        default = False,
        description="True if relevant according to instructions, False if not."
    )
    relevant_urls: List[str] = Field(
        default_factory=list, 
        description="List of URLs to relevant jobs according to instructions (only for job_list type)"
    )
    reasoning: str = Field(
        description="Explanation of your decisions"
    )
    # Job data fields (only populated for job_posting type)
    IM_jobs_found: Optional[IMJobs] = Field (description="Jobs found that fit the instructions")


class TopPickJob(BaseModel):
    id_list: list[int]


### STATES - LangGraph states

class OverallState(TypedDict):
    """State for the IM Scanner workflow"""
    url_queue: list[str]          # URLs to process
    processed_urls: list[str]     # URLs already processed (avoid loops)
    follow_up_urls: Annotated[list, operator.add]  # URLs from job lists that need follow up - needed for parallel processing
    jobs_found: Annotated[list[IMJobs], operator.add]  # add to the list of jobs found
    jobs_top_pick: list[IMJobs] # the absolute favorites of a given run, according to the AI


# We create a "private" state for a single page scraping
# note that page_url has the same type as the elements of url_queue (url_queue = list of page_url s)
class PageState(TypedDict):
    page_url: str


################################################################
# Singletons - create only once and share across functions
# Global variable to cache the graph
_scraper_agent = None

def get_scraper_agent():
    """Get or create the scraper agent (singleton pattern)"""
    global _scraper_agent
    
    # Cache the graph (stateless, can be shared)
    if _scraper_agent is None:
        _scraper_agent = scraper_agent_setup()
        logger.info("Created new scraper agent instance")
    
    return _scraper_agent




###################################################################
# Graphs
###################################################################

def IM_scanner_graph_setup():
    """
    Set up the graphs / workflow
    """

    # Construct the graph: here we put everything together to construct our graph
    graph = StateGraph(OverallState)
    graph.add_node("soft_start", soft_start)
    graph.add_node("scrape_a_page", scrape_a_page)
    graph.add_node("results_from_run", results_from_run)

    graph.add_edge(START, "soft_start")
    graph.add_conditional_edges("soft_start", scrape_in_parallel, ["scrape_a_page"])
    graph.add_edge("scrape_a_page", "results_from_run")
    graph.add_edge("results_from_run", END)

    # Compile the graph
    IM_workflow = graph.compile()

    return IM_workflow



###################################################################
# Nodes
###################################################################

###################################
def soft_start(state:OverallState):
    """ 
    A dummy start point of the graph, because the next 
    step is already going parallelized 
    """
    logger.info(f"Starting a graph run. This is the current target list:\n {state.get('url_queue')} \n")
    return



############################################
def scrape_in_parallel(state: OverallState):
    """
    This node function reads in the url_queue from the overall state and triggers 
    parallel scraping for each URL through Send
    """
    return [Send("scrape_a_page", {"page_url": singe_url}) for singe_url in state["url_queue"]]

def scrape_a_page(state: PageState):

    local_scraper_agent = get_scraper_agent()   # creates a singleton the first time it is called, otherwise access the one already created

    prompt = {"messages": [{"role": "user", "content": state["page_url"]}]}
    response = local_scraper_agent.invoke(prompt)
    structured_data = response.get('structured_response')  # retrieve the structured response from the agent

    # check if this was a job list - if so, return the update accordingly
    this_page_type = structured_data.page_type
    
    # for debugging only
    logger.info(f"""\n\nVisited {state["page_url"]} // This is {this_page_type}""")
    
    if this_page_type == "job_list":
        # it is a job list page - update only the follow up urls that were retrieved from it
        urls = structured_data.relevant_urls or []  # Convert None to []

        update_dict = {"follow_up_urls": urls}   ## This is why we need the annotated follow_up_urls, or the information gets lost when run in parallel
        
    elif this_page_type == "job_posting":
        # it is an actual job post - but is it relevant?
        if structured_data.IM_relevant and structured_data.IM_jobs_found is not None:
            # OK, the model thinks this is relevant AND we have actual job data
            update_dict = {"jobs_found": [structured_data.IM_jobs_found]}
        else:
            # Either not relevant or job data extraction failed
            if structured_data.IM_relevant and structured_data.IM_jobs_found is None:
                logger.warning(f"Job posting at {state['page_url']} was marked as relevant but job data extraction failed")
            update_dict = {}


    
    elif this_page_type == "not_relevant":
            # the page is not deemed relevant for our objective
            update_dict = {}
    else:
        # wrong format?
        logger.info('wrong format by llm - job_type')
        update_dict = {}

    return update_dict

##########################################
def results_from_run(state:OverallState):
    
    ll_jobs_found = state['jobs_found']
    ll_follow_up_urls = state['follow_up_urls']

    # Filter out None values from jobs_found
    ll_jobs_found = [job for job in ll_jobs_found if job is not None]
    
    logger.info(f"Results from current the graph run: found {len(ll_jobs_found)} relevant jobs.")

    jobs_top_pick = []  # Initialize outside if block
    top_job_response_ll = []

    if len(ll_jobs_found) >= 3: # we found some jobs in this run, let's pick our three favorites
        pick_top_job_prompt = """
        You are an expert job analyzer. Below you will find a list of jobs we found, these are senior 
        positions with focus on project management, transformation, technical leadership, strategy, 
        change management, turnaround, or solving a defined business challenge. 

        Select the three best ones. Return the IDs of the three best ones, starting 0 as the ID for the first job.

        Jobs: 

        {jobs_list}
        """
        try:
            model = ChatOpenAI(model="o3-mini")
            jobs_list = "\n\n".join([f"Job {i}: {job.model_dump_json()}" 
                                    for i, job in enumerate(ll_jobs_found)])  # convert the pydantic model instance into a JSON string representation
            #jobs_list = "\n\n".join(ll_jobs_found)
            prompt = pick_top_job_prompt.format(jobs_list=jobs_list)
            top_job_response = model.with_structured_output(TopPickJob).invoke(prompt)
            top_job_response_ll = [i for i in top_job_response.id_list if 0 <= i < len(ll_jobs_found)]
        except Exception as e:
            logger.error(f"Error in top job selection: {e}")
            top_job_response_ll = []


    if top_job_response_ll: 
        jobs_top_pick = [ll_jobs_found[i] for i in top_job_response_ll]
        
    
    processed_urls = state.get('url_queue', []) + state.get('processed_urls', [])
    return {
        "url_queue": ll_follow_up_urls, 
        "processed_urls": processed_urls, 
        "follow_up_urls": [],
        "jobs_top_pick": jobs_top_pick
    }


###################################################################
# Agents
###################################################################


############################################################
def customize_function_create_prompt(custom_system_prompt):
    def create_prompt(state):
        return [
            {
                "role": "system", 
                "content": custom_system_prompt
            }
        ] + state['messages']
    return create_prompt


#############################################################
def scraper_agent_setup():
    """
    ReAct agent that scrapes pages using a scraping tool.
    """

    react_IM_scanner_prompt = agent_system_prompt_type_2.format(
    role = """You are an expert job analyzer.""",
    tools = f"""scrape_website: fetches the full content of a URL; it needs the url (str of the target URL)""",
    instructions = """
    ## Task

    For each user-supplied URL decide whether it is:
    1) JOB LIST - a page listing several job postings.
    2) SINGLE JOB POSTING - a page describing one specific role.
    3) NOT RELEVANT - anything else.

    ### Job criteria

    A role is relevant when most of these apply:
    - Seniority: Director, Vice President, Head of Department, Senior Manager, Project Lead.
    - Focus: project management, transformation, technical leadership, or strategy.
    - Purpose: change management, turnaround, or solving a defined business challenge.
    - **Exclude** entry-level, junior, or support positions.
    - **Exclude** IT positions.
    """,

    rules = """
    ## Important
    Never include entry-level, junior, or support positions in job lists or as single job posts.
    Never include IT positions, even if very senior ones.
        
    ## Data extraction

    ### For JOB LIST pages
    - List of extracted URL links that lead to job postings fitting the Job criteria.

    ### For SINGLE JOB POSTING:
    Extract: title, company, location, duration, key_requirements, description_summary, apply_url.
    """
    )

    this_model = {'model_name': 'openai:o3-mini', 'model_max_tokens': 150000}  # put a bit conservative number in the max_tokens
    
    create_prompt = customize_function_create_prompt(react_IM_scanner_prompt)
    tools = [scrape_website]  # TBD: limit the number of tokens that are returned already at this level or not?

    scraper_agent = create_react_agent(
            model=this_model.get('model_name'),
            tools=tools,
            prompt=create_prompt,
            response_format=PageResponse,
        )
    
    return scraper_agent