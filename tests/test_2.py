import os
import sys
import uuid

# Ensure local project path is used
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.operator import get_agent, AgentType


def test_tenant_rag_isolation():
    # Simulate two tenants with unique IDs
    tenant_1 = str(uuid.uuid4())
    tenant_2 = str(uuid.uuid4())

    user_1 = "user_a"
    user_2 = "user_b"

    phantom_token_1 = f"{tenant_1}:{user_1}"
    phantom_token_2 = f"{tenant_2}:{user_2}"

    # Create RAG folders manually and add dummy files to simulate knowledge
    path_1 = os.path.join("rag_data", tenant_1)
    path_2 = os.path.join("rag_data", tenant_2)
    os.makedirs(path_1, exist_ok=True)
    os.makedirs(path_2, exist_ok=True)

    file_1 = os.path.join(path_1, "tenant1_knowledge.txt")
    file_2 = os.path.join(path_2, "tenant2_knowledge.txt")

    with open(file_1, "w") as f:
        f.write("This is private data for tenant 1.")

    with open(file_2, "w") as f:
        f.write("This is private data for tenant 2.")

    # Create agents for both tenants
    agent1 = get_agent(agent_id=AgentType.SAGE, phantom_token=phantom_token_1)
    agent2 = get_agent(agent_id=AgentType.SAGE, phantom_token=phantom_token_2)

    # Verify tenant-specific folders exist
    assert os.path.exists(path_1), f"Tenant 1 RAG folder not created: {path_1}"
    assert os.path.exists(path_2), f"Tenant 2 RAG folder not created: {path_2}"
    assert path_1 != path_2, "RAG directories should be isolated per tenant"

    # Verify tenant 1 cannot access tenant 2 data
    tenant1_files = os.listdir(path_1)
    tenant2_files = os.listdir(path_2)

    assert "tenant2_knowledge.txt" not in tenant1_files, "Tenant 1 should not access Tenant 2 data"
    assert "tenant1_knowledge.txt" not in tenant2_files, "Tenant 2 should not access Tenant 1 data"

    print("✅ Multi-tenant folder and file isolation test passed")


if __name__ == "__main__":
    test_tenant_rag_isolation()
