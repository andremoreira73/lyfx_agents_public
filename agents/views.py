from django.shortcuts import render
from .models import Agent, UserAgentAccess
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group



def home(request):
    """
    Public landing page view that shows different content based on authentication status
    """
    # Get public agents for everyone
    public_agents = Agent.objects.filter(public=True)
    
    # Featured agents are a subset of public agents
    #featured_agents = public_agents.filter(featured=True)[:3]
    featured_agents = public_agents.filter(featured=True)
    
    # Regular public agents (not featured)
    regular_agents = public_agents.exclude(featured=True)
    
    # Add chat URLs to the agents dynamically - needed for the template
    for agent in list(featured_agents) + list(regular_agents):
        agent.chat_url = _generate_agent_url(agent)
    
    return render(request, 'agents/home.html', {
        'featured_agents': featured_agents,
        'regular_agents': regular_agents,
        'is_home': True
    })



@login_required
def agent_dashboard(request):
    """
    Dashboard view showing agents separated into private and public sections
    """
    # Check if the user is in the 'AccessAllAgents' group
    if request.user.groups.filter(name='AccessAllAgents').exists():
        # User has access to all agents - separate public and private
        private_agents = Agent.objects.filter(public=False).order_by('name')
        public_agents = Agent.objects.filter(public=True).order_by('name')
    else:
        # Regular user - get their specific private agents + all public agents
        public_agents = Agent.objects.filter(public=True).order_by('name')
        
        # User-specific private agents through UserAgentAccess
        user_agent_ids = UserAgentAccess.objects.filter(user=request.user).values_list('agent_id', flat=True)
        private_agents = Agent.objects.filter(id__in=user_agent_ids, public=False).order_by('name')

    # Add chat URLs to both groups
    for agent in list(private_agents) + list(public_agents):
        agent.chat_url = _generate_agent_url(agent)

    return render(request, 'agents/dashboard.html', {
        'private_agents': private_agents,
        'public_agents': public_agents
    })


def _generate_agent_url(agent):
    """Generate the appropriate URL for an agent based on its type"""
    if agent.chat_type == 'chatapp_plus':
        return f"/chat_plus/chat_plus/?agent_name={agent.name}&assistant={agent.assistant}&vector_store={agent.vector_store}"
    elif agent.chat_type == 'chatapp':
        return f"/chat/chat/?agent_name={agent.name}&assistant={agent.assistant}&vector_store={agent.vector_store}"
    elif agent.chat_type == 'langgraph':
        return f"/agent/{agent.name}/"
    elif agent.chat_type == 'custom':
        # Use the api_endpoint field for custom applications like IM Scanner
        return agent.api_endpoint if agent.api_endpoint else "/"
    else:
        # Default fallback
        return f"/chat/chat/?agent_name={agent.name}&assistant={agent.assistant}&vector_store={agent.vector_store}"