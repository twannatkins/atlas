"""nl-to-sparql-agent — AgentCore Runtime entrypoint.

Wraps the existing handler from nl_to_sparql_agent.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This agent translates natural-language questions into SPARQL queries
using embedding-based semantic similarity against a curated template
set. The pipeline:
  1. Generate Titan Embed v2 embedding for the user's question
  2. Find the nearest few-shot template by cosine similarity
  3. Parameterize the template and delegate execution to
     atlas-sparql-mcp

The handler module's top-level sys.path.insert for the Workshop 1
atlas_sparql helper runs at module import time, so importing
nl_to_sparql_agent here sets up the path correctly without additional
manipulation in main.py.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from nl_to_sparql_agent import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler:
    a JSON object with 'question' (the natural-language input),
    'persona_claim' (the requesting persona), and optionally
    'context' (additional grounding for template selection).

    Returns a JSON object with the synthesized SPARQL query, the
    matched template, the matched score, and execution provenance.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
