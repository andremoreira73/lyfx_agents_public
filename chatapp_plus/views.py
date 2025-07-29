from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
import openai
import json
import markdown2
import os
from django.conf import settings
from agents.models import Agent  # Import the Agent model

##############################
def chat_plus_view(request):
    agent_name = request.GET.get('agent_name')
    this_assistant = request.GET.get('assistant')
    this_vector_store = request.GET.get('vector_store')
    
    # Check if the agent exists and if it's public or the user is logged in
    try:
        agent = Agent.objects.get(name=agent_name)
        
        # If agent is private and user is not logged in, redirect to login
        if not agent.public and not request.user.is_authenticated:
            # Save the URL to redirect back after login
            next_url = request.get_full_path()
            login_url = reverse('login') + f'?next={next_url}'
            return redirect(login_url)
            
    except Agent.DoesNotExist:
        # If agent doesn't exist, redirect to home
        return redirect('agents:home')
    
    # Continue with the existing code
    markdown_file_location = getattr(settings, 'MARKDOWN_LOCATION', None)
    markdown_file = os.path.join(markdown_file_location, f"{agent_name}.md")

    if os.path.exists(markdown_file):
        with open(markdown_file, 'r') as md_file:
            markdown_content = md_file.read()
            html_content = markdown2.markdown(markdown_content)
        html_content = "AI-generated content" + html_content
    else:
        print("!!! ", markdown_file)
        html_content = "<p>No additional information available for this agent.</p>"

    # Define the greeting message
    greeting_message = "Hello and welcome. Use this interface to chat with me."

    if request.method == 'POST':
        # Check if user is authenticated for POST requests (chat messages)
        if not request.user.is_authenticated and not agent.public:
            return JsonResponse({'reply': 'Please log in to chat with this agent.'}, status=403)
            
        user_message = request.POST.get('message')

        # Initialize the OpenAI client with beta headers if needed
        openai.api_base = 'https://api.openai.com/v1beta'
        openai.request_headers = {
            "OpenAI-Beta": "assistants=v2"
        }

        # Interact with your assistant
        oai_key = os.environ.get("OPENAI_API_KEY", "")
        client = openai.OpenAI(api_key=oai_key, default_headers={"OpenAI-Beta": "assistants=v2"})
        thread = client.beta.threads.create()
        my_assistant_id = this_assistant

        assistant = client.beta.assistants.update(
            assistant_id=my_assistant_id,
            tool_resources={"file_search": {"vector_store_ids": [this_vector_store]}},
        )

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        run = client.beta.threads.runs.create_and_poll(
          thread_id=thread.id, assistant_id=my_assistant_id
        )

        stat = run.status
        while stat != 'completed':
            stat = run.status
        
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )

        assistant_reply = messages.data[0].content[0].text.value

        return JsonResponse({'reply': assistant_reply})

    return render(request, 'chatapp_plus/chat_plus.html', {
        'agent_name': agent_name,
        'html_content': html_content,
        'greeting_message': greeting_message
    })