# langgraph_api_1/agent_registry.py
"""
Agent Registry - Central management of all LangGraph agents
This provides a clean interface between the API and specific agents
"""

from typing import Dict, Any, Optional, Protocol
import logging

logger = logging.getLogger(f'langgraph_api_1.agent_registry')





##############################
# for "clean python..."
class AgentExecutor(Protocol):
    """Protocol defining the interface that all agent executors must implement"""
    
    def execute(self, initial_state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Execute the agent workflow"""
        ...  # signature only
    
    def resume(self, checkpoint_config: Any, user_input: str, thread_id: str) -> Dict[str, Any]:
        """Resume the agent workflow from a checkpoint with user input"""
        ... # signature only
    
    def execute_kwargs(self, thread_id: str, **kwargs) -> Dict[str, Any]:
        """Execute or resume the agent workflow from a checkpoint, depending on the kwargs passed"""
        ... # signature only



############################################################################
# Specific for each LangGraph agent that is available in the backend
#
#
class CCCalcExecutor:
    """Executor for the CO2 Calculator (cccalc) agent
    This needs a resume function because the node is interrupted during the conversation,
    while information is being provided and then the node has to continue execution.
    """
    
    def __init__(self):
        self.name = "cccalc"
        self.description = "CO2 emissions calculator agent"
    
    def execute(self, initial_state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Execute the CO2 calculator workflow"""
        try:
            from langgraph_agents.cccalc.agent_adapter_APIs import execute_cccalc_workflow
            return execute_cccalc_workflow(initial_state, thread_id)
        except ImportError as e:
            logger.error(f"Failed to import cccalc workflow: {e}")
            raise ValueError(f"CCCalc agent not available: {e}")
    
    def resume(self, user_input: str, thread_id: str) -> Dict[str, Any]:
        """Resume the CO2 calculator workflow from a checkpoint"""
        try:
            from langgraph_agents.cccalc.agent_adapter_APIs import resume_cccalc_workflow
            return resume_cccalc_workflow(user_input, thread_id)
        except ImportError as e:
            logger.error(f"Failed to import cccalc resume function: {e}")
            raise ValueError(f"CCCalc resume not available: {e}")
    
    def execute_kwargs(self, thread_id: str, **kwargs) -> Dict[str, Any]:
        """Execute or resume the CO2 calculator workflow from a checkpoint, depending on the kwargs passed"""
        try:
            from langgraph_agents.cccalc.agent_adapter_APIs import execute_cccalc_workflow_kwargs
            return execute_cccalc_workflow_kwargs(thread_id, **kwargs)
        except ImportError as e:
            logger.error(f"Failed to import cccalc workflow with kwargs: {e}")
            raise ValueError(f"CCCalc agent not available: {e}")

class LyrasExecutor:
    """Executor for lyras chat agent"""
    
    def __init__(self):
        self.name = "lyras"
        self.description = "lyfX.ai interaction agent"
    
    def execute(self, initial_state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
        """Execute lyras workflow"""
        try:
            from langgraph_agents.lyras.agent_adapter_APIs import execute_lyras_workflow
            return execute_lyras_workflow(initial_state, thread_id)
        except ImportError as e:
            logger.error(f"Failed to import lyras workflow: {e}")
            raise ValueError(f"lyras agent not available: {e}")
    
    def resume(self, user_input: str, thread_id: str) -> Dict[str, Any]:
        """Resume lyras workflow; 
        Note that, unlike cccalc where there was a node interrupt, here we simple execute the graph again
        as the conversation memory is tied with the thread.
        """
        try:
            from langgraph_agents.lyras.agent_adapter_APIs import execute_lyras_workflow
            return execute_lyras_workflow(user_input, thread_id)
        except ImportError as e:
            logger.error(f"Failed to import import lyras workflow (resume): {e}")
            raise ValueError(f"lyras (resume) agent not available: {e}")
    


##################################
# Registry of all available agents
_AGENT_REGISTRY: Dict[str, AgentExecutor] = {
    'cccalc': CCCalcExecutor(),
    'lyras': LyrasExecutor(),
    # Add more agents here as you develop them:
    # 'chat_general': ChatGeneralExecutor(),
    # 'financial_analysis': FinancialAnalysisExecutor(),
    # 'document_processor': DocumentProcessorExecutor(),
}



#####################################################################
def get_agent_executor(assistant_id: str) -> Optional[AgentExecutor]:
    """
    Get the executor for a specific assistant/agent
    
    Args:
        assistant_id: The ID of the assistant (e.g., 'cccalc', 'chat_general')
    
    Returns:
        AgentExecutor instance or None if not found
    """
    executor = _AGENT_REGISTRY.get(assistant_id)
    if not executor:
        logger.warning(f"Unknown assistant_id: {assistant_id}")
        logger.info(f"Available assistants: {list(_AGENT_REGISTRY.keys())}")
    return executor







###########################################################################
# The functions below are only for future implementations, not in use now

#########################################################################
def register_agent(assistant_id: str, executor: AgentExecutor) -> None:
    """
    Register a new agent executor
    
    Args:
        assistant_id: The ID to register the agent under
        executor: The executor instance
    """
    _AGENT_REGISTRY[assistant_id] = executor
    logger.info(f"Registered agent: {assistant_id}")

##############################################
def list_available_agents() -> Dict[str, str]:
    """
    List all available agents with their descriptions
    
    Returns:
        Dictionary mapping agent IDs to their descriptions
    """
    return {
        agent_id: executor.description 
        for agent_id, executor in _AGENT_REGISTRY.items()
    }

##################################################################
def get_agent_info(assistant_id: str) -> Optional[Dict[str, str]]:
    """
    Get information about a specific agent
    
    Args:
        assistant_id: The ID of the assistant
    
    Returns:
        Dictionary with agent information or None if not found
    """
    executor = _AGENT_REGISTRY.get(assistant_id)
    if not executor:
        return None
    
    return {
        'id': assistant_id,
        'name': executor.name,
        'description': executor.description,
        'available': True
    }

#######################################################
# Utility function for debugging
def debug_registry():
    """Print registry information for debugging"""
    logger.info("=== Agent Registry Debug Info ===")
    logger.info(f"Total registered agents: {len(_AGENT_REGISTRY)}")
    for agent_id, executor in _AGENT_REGISTRY.items():
        logger.info(f"  - {agent_id}: {executor.name} ({executor.description})")
    logger.info("=================================")