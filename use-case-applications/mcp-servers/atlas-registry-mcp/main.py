"""atlas-registry-mcp — AgentCore Runtime entrypoint.

Wraps the existing handler from atlas_registry_mcp.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This component wraps AWS Agent Registry with persona-scoped access:
every operation validates a persona_claim and filters results to
capabilities the persona is authorized to see. The MCP server itself
is in the registry it serves — every agent in ATLAS discovers tools
through this component, including itself.

The REGISTRY_ENDPOINT environment variable is read at module import
time; no additional path setup is needed in main.py.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from atlas_registry_mcp import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler.
    Forwards to the existing handler function unchanged. The handler
    determines which operation to dispatch (list_capabilities,
    get_agent, get_mcp_server, invoke_capability) based on the
    payload's 'operation' field.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
