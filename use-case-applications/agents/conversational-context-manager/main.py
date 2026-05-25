"""conversational-context-manager — AgentCore Runtime entrypoint.

Wraps the existing handler from conversational_context_manager.py
in a Strands BedrockAgentCoreApp for deployment to AgentCore Runtime.
The handler signature is preserved (event/payload, context) -> response dict.

This agent supports multi-turn conversations on the Wealth Advisor's
Themes route. The interaction loop:
  1. Advisor sends a question with a stable session_id
  2. Handler loads prior session context from AgentCore Memory keyed
     by {AGENTCORE_MEMORY_NAMESPACE}/{session_id}
  3. Handler invokes nl-to-sparql-agent with both the question and
     the prior context (so follow-ups like "what about the next one"
     can resolve relative to prior turns)
  4. Handler appends the new turn to session context and writes back
     to AgentCore Memory (last 10 turns retained)

The handler already integrates real AgentCore Memory via
boto3.client("bedrock-agentcore"). The session_id key partitions
sessions per authenticated user (the Cognito sub claim becomes the
session_id in the UI's invocation), so cross-user isolation is
enforced by the Memory namespace key without additional code.

This is the only agent in the architecture that uses AgentCore
Memory. The architectural pattern (one Memory store per stack,
sessions partitioned by Cognito sub) lives entirely in this
component's call shape — other agents are stateless and do not
need Memory access.

The handler module's top-level sys.path.insert for the Workshop 1
shared helpers is present (consistent with the pattern across
agents) but the module itself imports only stdlib and boto3, so
main.py needs no additional path setup.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from conversational_context_manager import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler:
    a JSON object with 'question' (the user's natural-language input),
    'session_id' (stable per-user session identifier, typically the
    Cognito sub claim), and 'persona_claim'.

    Returns a JSON object with the NL-to-SPARQL result for the
    current turn plus the session_id echoed back. AgentCore Memory
    state changes (prior context loaded, new turn appended) happen
    inside the handler and do not surface in the response.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
