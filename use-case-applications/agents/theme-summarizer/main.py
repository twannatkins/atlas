"""theme-summarizer — AgentCore Runtime entrypoint.

Wraps the existing handler from theme_summarizer.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This agent generates a narrative summary of a market theme by
fetching theme-relevant articles via atlas-sparql-mcp and asking
Claude Sonnet (us.anthropic.claude-sonnet-4-6 by default) to
summarize them. Every response carries is_probabilistic=True and
requires_human_review=True — the summary is a draft for an advisor
to refine, not a system-of-record statement.

This is the first of two probabilistic agents in the architecture
(the other is referral-rationale-drafter). Both follow the same
pattern: Bedrock at the edge for narrative drafting, deterministic
SPARQL for the grounding data, explicit HIL flags in the response
schema. This implements the SR 11-7 / OCC 2011-12 framing — an LLM
generates the prose, a human approves it before any client-facing
action.

The handler module's top-level sys.path.insert for the Workshop 1
shared helpers runs at module import time, so main.py needs no
additional path setup.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from theme_summarizer import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler:
    a JSON object with 'theme_uri' (atlas:Theme URI) and 'persona_claim'.

    Returns a JSON object with the generated summary, the source
    articles used as grounding, the model and inference profile ID,
    and the is_probabilistic / requires_human_review flags set to true.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
