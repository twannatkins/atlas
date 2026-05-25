"""atlas-fibo-mcp — AgentCore Runtime entrypoint.

Wraps the existing handler from atlas_fibo_mcp.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This component has no sys.path manipulation — it depends only on
boto3 and the standard library, delegating SPARQL queries to
atlas-sparql-mcp via Lambda invocation. The wrapper has no
additional setup beyond the standard BedrockAgentCoreApp pattern.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from atlas_fibo_mcp import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler.
    Forwards to the existing handler function unchanged. The handler
    determines which operation to dispatch (class_info, list_classes,
    subclasses_of) based on the payload's 'operation' field.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
