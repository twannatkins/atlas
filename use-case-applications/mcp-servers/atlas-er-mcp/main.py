"""atlas-er-mcp — AgentCore Runtime entrypoint.

Wraps the existing handler from atlas_er_mcp.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This component wraps AWS Entity Resolution with persona-scoped access
control: every operation validates a persona_claim before invoking
the underlying boto3 entityresolution client. The ER_WORKFLOW_NAME
environment variable is read at module import time; no additional
path setup is needed in main.py.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from atlas_er_mcp import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler.
    Forwards to the existing handler function unchanged. The handler
    determines which operation to dispatch (lookup, resolve, link)
    based on the payload's 'operation' field.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
