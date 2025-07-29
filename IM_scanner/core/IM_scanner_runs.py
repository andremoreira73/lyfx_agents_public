
import logging

from .IM_scanner_targets import targets
from .IM_scanner_setup import IM_scanner_graph_setup

import random


## logger instance for this module
logger = logging.getLogger(f'IM_scanner.IM_scanner_runs')

def run_IM_scanner():
    """
    Semi-programmatic workflow to scan target websites and extract jobs
    """

    # Prepare the staring target list
    targets_ll = []
    for name, url in targets.items():
        targets_ll.append(url)
    initial_state = {
        "url_queue": targets_ll,
        "processed_urls": [],
        "follow_up_urls": [],
        "jobs_found": [],
        "jobs_top_pick": []
    }

    counter = 1
    max_counter = 3 ## max number of graph runs we will perform - indirectly related to search depth
    max_pages_per_run = 30

    continue_runs = True
    jobs_found_ll = []
    jobs_top_picks_ll = [] # make this a list, as there may be a few from different runs
    processed_urls_ll = []

    # create a graph
    IM_workflow = IM_scanner_graph_setup()

    while continue_runs:

        logger.info(f"""
    ###########################
    run number {counter}
    ###########################
        """)
        
        # run the graph
        graph_result = IM_workflow.invoke(initial_state)
        counter += 1
        
        # now we process the results of this run
        new_url_queue = graph_result.get('url_queue')   # each time comes ready for the next run (from last node update)
        new_processed_urls = graph_result.get('processed_urls')  # cumulate
        new_jobs_found = graph_result.get('jobs_found') # cumulate
        new_jobs_top_pick = graph_result.get('jobs_top_pick')

        processed_urls_ll.extend(new_processed_urls)
        jobs_found_ll.extend(new_jobs_found)

        if new_jobs_top_pick:  # Check if list is not empty
            jobs_top_picks_ll.extend(new_jobs_top_pick)  # extend since it is a list

        # make sure we do not scrape more than a pre-set number of pages in one run - time and cost control
        if len(new_url_queue) > max_pages_per_run:
            new_url_queue = random.sample(new_url_queue, max_pages_per_run)
                
        # reset the initial state
        initial_state = {
            "url_queue": new_url_queue,
            "processed_urls": [],
            "follow_up_urls": [],
            "jobs_found": [],
            "jobs_top_pick": []
            }

        # check if we stop or continue
        if not new_url_queue:  # if there is no list of urls to follow up, stop the runs
            continue_runs = False
        elif counter > max_counter:
            continue_runs = False
        else:
            continue_runs = True

    logger.info("-------exited runs--------")

    # Return structured results for database integration
    return {
        'jobs_found_ll': jobs_found_ll,
        'jobs_top_picks_ll': jobs_top_picks_ll,
        'processed_urls_ll': processed_urls_ll,
        'total_jobs': len(jobs_found_ll),
        'total_top_picks': len(jobs_top_picks_ll),
        'total_pages_processed': len(processed_urls_ll)
    }