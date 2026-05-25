"""behavioral-signal-agent — AgentCore Runtime entrypoint.

Wraps the existing handler from behavioral_signal_agent.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This agent mints behavioral signals (engagement, risk aversion,
liquidity preference) by executing parameterized SPARQL CONSTRUCT
queries, then validating each minted signal against the relevant
SHACL shape via atlas-shacl-mcp before writing to the SLGD.

The agent is deterministic — no LLM invocation. Bedrock is not in
the call path. This mirrors wealth-signal-detector but targets
behavioral rather than wealth-readiness signals.

The handler module's top-level sys.path.insert for the Workshop 1
atlas_sparql helper runs at module import time, so main.py needs no
additional path setup.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from behavioral_signal_agent import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler:
    a JSON object with 'target_uri' (Customer or Household URI),
    'persona_claim', and optionally 'signal_types' (filter to specific
    behavioral signal types; defaults to all Phase 1 behavioral signals).

    Returns a JSON object with the list of minted behavioral signals,
    each annotated with provenance (which CONSTRUCT query produced it,
    which SHACL shape validated it).
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
