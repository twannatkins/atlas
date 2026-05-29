"""wealth-signal-detector — AgentCore Runtime entrypoint.

Wraps the existing handler from wealth_signal_detector.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This agent mints wealth-readiness signals for a customer or household
by executing parameterized SPARQL CONSTRUCT queries from S3, then
validating each minted signal against the relevant SHACL shape via
atlas-shacl-mcp before writing to the SLGD. Failed validations are
returned in the response with the specific shape violation, so
upstream callers can surface the gap rather than silently fail.

The agent is deterministic — no LLM invocation. Bedrock is not in
the call path. This contrasts with nl-to-sparql-agent (Bedrock for
embeddings) and referral-rationale-drafter (Bedrock for narrative).

The handler module's top-level sys.path.insert for the Workshop 1
atlas_sparql helper runs at module import time, so main.py needs no
additional path setup.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from wealth_signal_detector import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler:
    a JSON object with 'target_uri' (Customer or Household URI),
    'persona_claim', and optionally 'signal_types' (filter to specific
    signal types; defaults to all Phase 1 signal types).

    Returns a JSON object with the list of minted signals, each
    annotated with provenance (which CONSTRUCT query produced it,
    which SHACL shape validated it).
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
