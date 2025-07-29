
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import Http404
from agents.models import Agent
import markdown2
import os
from django.conf import settings


def chat_view(request, agent_name):
    """
    Unified chat view for LangGraph agents only
    """
    # Get the agent or 404
    try:
        agent = get_object_or_404(Agent, name=agent_name)
    except Agent.DoesNotExist:
        raise Http404("Agent not found")
    
    # Only handle LangGraph agents in this app
    if agent.chat_type != 'langgraph':
        # Redirect to appropriate legacy chat app
        if agent.chat_type == 'chatapp_plus':
            return redirect(f"/chat_plus/chat_plus/?agent_name={agent.name}&assistant={agent.assistant}&vector_store={agent.vector_store}")
        elif agent.chat_type == 'chatapp':
            return redirect(f"/chat/chat/?agent_name={agent.name}&assistant={agent.assistant}&vector_store={agent.vector_store}")
        else:
            raise Http404("Unsupported agent type")
    
    # Check permissions for private agents
    if not agent.public and not request.user.is_authenticated:
        next_url = request.get_full_path()
        login_url = reverse('login') + f'?next={next_url}'
        return redirect(login_url)
    
    # Check if help content exists
    help_content_exists = load_agent_help_content(agent_name) is not None
    
    # Determine placeholder text
    placeholder_text = agent.example_message if agent.example_message else "Type your message..."

    # DEBUG: Print what we're getting
    #print(f"DEBUG: Agent name: {agent_name}")
    #print(f"DEBUG: Sidebar content: {sidebar_content}")
    #if sidebar_content:
    #    print(f"DEBUG: Content type: {sidebar_content.get('type')}")
    #    print(f"DEBUG: Content preview: {sidebar_content.get('content', '')[:100]}...")
    
    # Prepare context for template
    context = {
        'agent': agent,
        'agent_name': agent_name,
        'help_content_exists': help_content_exists,
        'placeholder_text': placeholder_text,
        'api_base_url': '/api',  # Base URL for langgraph_api_1
        'greeting_message': f"Hello! I'm {agent_name}. How can I help you today?",
    }
    
    return render(request, 'agent_chat/chat.html', context)


def load_agent_help_content(agent_name):
    """
    Load sidebar content for an agent (flexible approach)
    Priority: HTML > Markdown > None
    """
    markdown_location = getattr(settings, 'MARKDOWN_LOCATION', '')
    
    if not markdown_location:
        return None
    
    # Try HTML first
    html_file = os.path.join(markdown_location, f"{agent_name}.html")
    if os.path.exists(html_file):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                return {'type': 'html', 'content': f.read()}
        except Exception:
            pass
    
    # Try Markdown
    md_file = os.path.join(markdown_location, f"{agent_name}.md")
    if os.path.exists(md_file):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
                html_content = markdown2.markdown(markdown_content)
                return {'type': 'markdown', 'content': html_content}
        except Exception:
            pass
    
    return None

def help_view(request, agent_name):
    """
    Help page for an agent
    """
    # Get the agent or 404
    try:
        agent = get_object_or_404(Agent, name=agent_name)
    except Agent.DoesNotExist:
        raise Http404("Agent not found")
    
    # Load help content
    help_content = load_agent_help_content(agent_name)
    if not help_content:
        raise Http404("Help content not found")
    
    context = {
        'agent': agent,
        'agent_name': agent_name,
        'help_content': help_content,
    }
    
    return render(request, 'agent_chat/help.html', context)