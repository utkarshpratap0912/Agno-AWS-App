
import os
import sys
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agents.operator import get_agent, AgentType

def test_tenant_rag_isolation():
    # Simulate two tenants
    tenant_1 = str(uuid.uuid4())
    tenant_2 = str(uuid.uuid4())

    user_1 = "user_a"
    user_2 = "user_b"

    phantom_token_1 = f"{tenant_1}:{user_1}"
    phantom_token_2 = f"{tenant_2}:{user_2}"

    # Create agents for both tenants
    agent1 = get_agent(agent_id=AgentType.SAGE, phantom_token=phantom_token_1)
    agent2 = get_agent(agent_id=AgentType.SCHOLAR, phantom_token=phantom_token_2)

    # Check if tenant-specific folders exist
    path_1 = os.path.join("rag_data", tenant_1)
    path_2 = os.path.join("rag_data", tenant_2)

    assert os.path.exists(path_1), f"Tenant 1 RAG folder not created: {path_1}"
    assert os.path.exists(path_2), f"Tenant 2 RAG folder not created: {path_2}"
    assert path_1 != path_2, "RAG directories should be isolated per tenant"

if __name__ == "__main__":
    test_tenant_rag_isolation()
    print("✅ Multi-tenant test passed")
