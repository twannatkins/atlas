"""atlas-sparql-mcp — AgentCore Runtime entrypoint.

Wraps the existing handler from atlas_sparql_mcp.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

The handler module's top-level sys.path.insert for the Workshop 1
atlas_sparql helper runs at module import time, so importing
atlas_sparql_mcp here sets up the path correctly without additional
manipulation in main.py.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from atlas_sparql_mcp import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler.
    Forwards to the existing handler function unchanged. The handler
    determines which operation to dispatch (query, update,
    construct_and_validate) based on the payload's 'operation' field.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
