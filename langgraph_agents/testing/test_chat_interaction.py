# test_chat_interaction.py

# run it:
# python test_chat_interaction.py


import requests
import json
import time
import uuid
import sys

# Configuration
API_URL = "http://localhost:8000/api"
ASSISTANT_ID = "cccalc"  # Use the agent ID that you need to test

def print_colored(text, color="white"):
    """Print colored text to terminal"""
    colors = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",      # Dark yellow (instead of bright \033[93m)
    "orange": "\033[38;5;208m", # Orange (good alternative to yellow)
    "blue": "\033[94m",
    "darkblue": "\033[34m",    # Darker blue
    "purple": "\033[95m",
    "magenta": "\033[35m",     # Darker purple/magenta
    "cyan": "\033[96m",
    "darkcyan": "\033[36m",    # Darker cyan
    "white": "\033[97m",
    "gray": "\033[90m",        # Dark gray
    "bold": "\033[1m",         # Bold (can combine with colors)
    "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def test_chat_interaction():
    # Step 1: Create a new thread
    print_colored("Creating new thread...", "darkblue")
    response = requests.post(
        f"{API_URL}/threads",
        json={"metadata": {}}
    )
    
    if response.status_code != 200:
        print_colored(f"Error creating thread: {response.text}", "red")
        return
    
    thread_data = response.json()
    thread_id = thread_data["id"]
    print_colored(f"Thread created with ID: {thread_id}", "green")
    
    # Step 2: Add initial message
    initial_message = "Hello. I need to calculate CO2 emission of a chemical called SF."
    print_colored(f"Sending initial message: '{initial_message}'", "darkblue")
    
    response = requests.post(
        f"{API_URL}/threads/{thread_id}/messages",
        json={"role": "user", "content": initial_message}
    )
    
    if response.status_code != 200:
        print_colored(f"Error adding message: {response.text}", "red")
        return
    
    print_colored("Message added successfully", "green")
    
    # Step 3: Start a run
    print_colored(f"Starting run with assistant: {ASSISTANT_ID}", "darkblue")
    response = requests.post(
        f"{API_URL}/threads/{thread_id}/runs",
        json={"assistant_id": ASSISTANT_ID}
    )
    
    if response.status_code != 200:
        print_colored(f"Error starting run: {response.text}", "red")
        return
    
    run_data = response.json()
    run_id = run_data["id"]
    print_colored(f"Run started with ID: {run_id}", "green")
    
    # Step 4: Poll for run status and handle interaction
    while True:
        print_colored("Checking run status...", "darkblue")
        response = requests.get(f"{API_URL}/threads/{thread_id}/runs/{run_id}")
        
        if response.status_code != 200:
            print_colored(f"Error checking run status: {response.text}", "red")
            break
        
        run_status = response.json()
        status = run_status.get("status")
        #print_colored(f"Current status: {status}", "cyan")
        
        # Get latest messages to display
        response = requests.get(f"{API_URL}/threads/{thread_id}/messages")
        if response.status_code == 200:
            messages = response.json().get("data", [])

            msg_ll = []
            for msg in messages:
                if msg["role"] == "assistant":
                    msg_ll.append(msg)

            msg_last = msg_ll[-1]
            print_colored(f"Assistant: {msg_last['content']}", "green")
        
        # Handle different statuses
        if status == "requires_action":
            print_colored("The assistant is waiting for your input!", "yellow")
            user_input = input("Your response: ")
            
            print_colored("Submitting your response...", "darkblue")
            response = requests.post(
                # f"{API_URL}/runs/{run_id}/submit_tool_outputs",
                f"{API_URL}/runs/{run_id}/submit_tool_outputs",
                json={
                    "tool_outputs": [
                        {"type": "text", "content": user_input}
                    ]
                }
            )
            
            if response.status_code != 200:
                print_colored(f"Error submitting response: {response.text}", "red")
                break
                
            print_colored("Response submitted successfully", "green")
            
        elif status == "completed":
            print_colored("Run completed successfully!", "green")
            break
            
        elif status == "failed":
            print_colored("Run failed!", "red")
            print_colored(f"Error: {run_status.get('error', 'Unknown error')}", "red")
            break
            
        elif status == "cancelled":
            print_colored("Run was cancelled", "yellow")
            break
            
        # Wait before polling again
        time.sleep(2)
    
    print_colored("Test completed!", "purple")

if __name__ == "__main__":
    test_chat_interaction()