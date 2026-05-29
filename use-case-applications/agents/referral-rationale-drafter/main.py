"""referral-rationale-drafter — AgentCore Runtime entrypoint.

Wraps the existing handler from referral_rationale_drafter.py in a
Strands BedrockAgentCoreApp for deployment to AgentCore Runtime.
The handler signature is preserved (event/payload, context) -> response.

This is the flagship probabilistic agent in the architecture. Given
a household URI and a list of triggering signal URIs, the agent
generates a narrative rationale that a Consumer Banker reviews
before any client-facing action. The rationale is a draft — not a
system-of-record statement.

Every response carries is_probabilistic=True and
requires_human_review=True. These flags are hardcoded in the
handler (line 117-118, line 249-250 of referral_rationale_drafter.py)
and persist even when Bedrock invocation fails — the response
schema preserves them at the error path as well, which is the
behavioral guarantee that lets upstream systems (the Wholesale UI,
Step Functions audit_write) trust the contract without per-response
configuration checks.

The agent loads its prompt template from S3 (PROMPT_TEMPLATE_S3_URI)
rather than constructing it inline. This separates prompt
maintenance from agent code: the platform team can iterate on
prompts without redeploying the Runtime. The prompt template path
is an operational concern, governed by the same review cycle as
the JSON descriptors in spec/04-aws-agent-registry/.

This implements the SR 11-7 / OCC 2011-12 framing in practice:
- Bedrock at the edge for narrative drafting
- Deterministic SPARQL for the grounding data (household context,
  signal summary)
- Explicit HIL flags in the response schema, non-configurable
- Audit-grade provenance (model ID, inference profile, queries
  executed) for regulatory traceability

The handler module's top-level sys.path.insert for the Workshop 1
atlas_sparql helper runs at module import time, so main.py needs
no additional path setup.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from referral_rationale_drafter import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler:
    a JSON object with 'household_uri' (atlas:Household URI),
    'signal_uris' (list of triggering atlas:Signal URIs that
    motivated the referral), and 'persona_claim' (the requesting
    Consumer Banker's persona).

    Returns a JSON object with:
    - The generated draft rationale (narrative for advisor review)
    - is_probabilistic = True (non-configurable)
    - requires_human_review = True (non-configurable)
    - provenance: model ID, inference profile, queries executed,
      prompt template version, execution time
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
