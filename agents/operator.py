from enum import Enum
from typing import List, Optional

from agents.sage import get_sage
from agents.scholar import get_scholar


class AgentType(Enum):
    SAGE = "sage"
    SCHOLAR = "scholar"


def get_available_agents() -> List[str]:
    """Returns a list of all available agent IDs."""
    return [agent.value for agent in AgentType]


def parse_phantom_token(phantom_token: str):
    try:
        tenant_id, user_id = phantom_token.split(":")
        return tenant_id, user_id
    except ValueError:
        raise ValueError("Invalid phantom token format. Expected 'tenant_id:user_id'")


def get_agent(
    phantom_token: Optional[str] = None,
    model_id: str = "gpt-4o",
    agent_id: Optional[AgentType] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    tenant_id = None
    user_id_extracted = user_id
    if phantom_token:
        tenant_id, user_id_extracted = parse_phantom_token(phantom_token)

    if agent_id == AgentType.SAGE:
        return get_sage(model_id=model_id, tenant_id=tenant_id, user_id=user_id_extracted, session_id=session_id, debug_mode=debug_mode)
    else:
        return get_scholar(model_id=model_id, tenant_id=tenant_id, user_id=user_id_extracted, session_id=session_id, debug_mode=debug_mode)
