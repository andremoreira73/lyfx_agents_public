# langgraph_agents/tools/scraping.py

import logging

from langchain_core.tools import tool
import requests
from requests.exceptions import Timeout, RequestException
from bs4 import BeautifulSoup
import os

import tiktoken

import json


## logger instance for this module
logger = logging.getLogger(f'IM_scanner.IM_scanner_tools')

@tool
def scrape_website(url: str) -> dict:
    """
    Scrape a website and return cleaned content and status.
    
    Args:
        url: The URL to scrape
        max_tokens: limits the length of the downloaded material based on the allowed llm maximum token
        
    Returns:
        dict with keys: status ('OK', 'TIMEOUT', 'ERROR'), content, error_message
    """
    try:
        # Get API keys from environment variables
        api_key = os.environ.get("SCRAPINGBEE_API_KEY")
        endpoint = os.environ.get("SCRAPINGBEE_ENDPOINT")
        
        # Parameters for ScrapingBee API
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        
        params = {
            'api_key': api_key,
            'url': url,
            'block_ads': 'True',
            'render_js': 'True',
            'wait': '5000'
        }
        
        # Make request with timeout 
        response, retry_status = _make_request_with_retries(endpoint, params, headers, 3, 20)
        
        # for debugging
        #logger.info(response.text)

        if retry_status == "Max retries":
            return {
                'status': 'ERROR',
                'content': '',
                'error_message': 'Max retries reached'
            }
        
        if response.status_code == 200:

            response_content = response.text

            ## TBD how to find a good way to reduce tokens without losing the important content
            #cleaned_content = extract_job_content(response.text)
            #
            # Fallback to raw content if extraction fails
            #if not cleaned_content or len(cleaned_content.strip()) < 100:
            #    logger.info("Poor extraction result, falling back to raw content")
            #    response_content = response.text
            #else:
            #    logger.info(f"Content extraction: reduced html content from {len(response.text)} to {len(cleaned_content)} chars")
            #    response_content = cleaned_content
            #
                                
            if not response_content:
                return {
                    'status': 'ERROR',
                    'content': '',
                    'error_message': 'Empty content'
                }
            
            limited_content = _limit_tokens(response_content, max_tokens=100000, model="o3-mini")

            return {
                'status': 'OK',
                'content': limited_content,
                'error_message': ''
            }
        
        else:
            return {
                'status': 'ERROR',
                'content': '',
                'error_message': f'HTTP {response.status_code}'
            }
            
    except Exception as e:
        return {
            'status': 'ERROR',
            'content': '',
            'error_message': str(e)
        }



##############################################################################################
def _make_request_with_retries(endpoint, params, headers, max_retries=3, timeout_duration=20):
    retry_count = 0
    while retry_count < max_retries:
        try:
            response = requests.get(
                endpoint, 
                params=params, 
                headers=headers, 
                timeout=timeout_duration)
            retry_status = 'OK'
            return (response, retry_status)
        except Timeout:
            logger.info(f"Request timed out. Attempt {retry_count + 1} of {max_retries}.")
        except RequestException as e:
            logger.info(f"Request failed: {e}. Attempt {retry_count + 1} of {max_retries}.")
        retry_count += 1
    
    # maximum number of attempts reached, return with this message
    return ('','Max retries')


#######################################################################################
def _limit_tokens(response_content: str, max_tokens: int, model: str = "gpt-4o") -> str:
    """
    Limit response content to a maximum number of tokens using actual tokenization.
    
    Args:
        response_content: The content to potentially truncate
        max_tokens: Maximum allowed tokens
        model: Model name for tokenizer (defaults to gpt-4o)
        
    Returns:
        Truncated content if necessary, capped at 80% of max_tokens
    """
    try:
        # Get the appropriate tokenizer for the model
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base for unknown models (works for most OpenAI models)
        encoding = tiktoken.get_encoding("cl100k_base")
    
    # Tokenize the content
    tokens = encoding.encode(response_content)
    
    # Check if truncation is needed
    if len(tokens) <= max_tokens:
        return response_content
    
    # Calculate 80% of max_tokens
    target_tokens = int(max_tokens * 0.8)
    
    # Truncate tokens and decode back to text
    truncated_tokens = tokens[:target_tokens]
    truncated_content = encoding.decode(truncated_tokens)
    
    # Add truncation notice
    truncated_content += "\n\n[CONTENT TRUNCATED DUE TO TOKEN LIMIT]"
    
    return truncated_content




##############################################################################
def extract_job_content(html_content):
    # Method 1: Look for structured data first
    structured_jobs = extract_structured_data(html_content)
    if structured_jobs:
        return structured_jobs
    
    # Method 2: Job-specific CSS selectors
    job_content = extract_with_job_selectors(html_content)
    if job_content and len(job_content) > 500:  # Reasonable content threshold
        return job_content
    
    # Method 3: Raw content as last resort
    return html_content


##################################
def extract_structured_data(html):
    """Extract JSON-LD or microdata job postings"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for JSON-LD
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                return json.dumps(data, indent=2)
            elif isinstance(data, list):
                jobs = [item for item in data if item.get('@type') == 'JobPosting']
                if jobs:
                    return json.dumps(jobs, indent=2)
        except:
            continue
    return None

#####################################
def extract_with_job_selectors(html):
    """Extract using job-specific CSS patterns"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Common job site patterns (English + German)
    job_selectors = [
        # English patterns
        '[class*="job"]', '[data-testid*="job"]', '[id*="job"]',
        '[class*="position"]', '[class*="vacancy"]', '[class*="career"]',
        '[class*="listing"]', '[class*="opening"]',
        
        # German patterns (for your energy company targets)
        '[class*="stelle"]', '[class*="karriere"]', '[class*="bewerbung"]',
        '[class*="vakanz"]', '[class*="jobs"]', '[class*="angebot"]'
    ]
    
    job_elements = []
    for selector in job_selectors:
        elements = soup.select(selector)
        job_elements.extend(elements)
    
    if job_elements:
        # Extract text from job elements
        job_texts = []
        for elem in job_elements:
            text = elem.get_text(separator=' ', strip=True)
            if len(text) > 50:  # Filter out tiny elements
                job_texts.append(text)
        
        return '\n\n'.join(job_texts)
    
    return None