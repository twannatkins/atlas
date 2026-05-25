"""household-traverser — AgentCore Runtime entrypoint.

Wraps the existing handler from household_traverser.py in a Strands
BedrockAgentCoreApp for deployment to AgentCore Runtime. The handler
signature is preserved (event/payload, context) -> response dict.

This agent returns the 1-hop relationship strip for a household URI:
spouse, dependents, joint accounts, beneficiaries — whatever
atlas:hasHouseholdMember and adjacent FIBO relationships expose for
the household. The query is parameterized SPARQL delegated to
atlas-sparql-mcp; the agent itself does no graph reasoning.

The agent is read-only and deterministic — single SPARQL MCP
dependency, no Bedrock, no SHACL. Demonstrates that not every agent
needs a model in the loop; many useful behaviors are deterministic
query-and-shape against the semantic layer.

The handler module's top-level sys.path.insert for the Workshop 1
atlas_sparql helper runs at module import time, so main.py needs no
additional path setup.
"""

from __future__ import annotations

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from household_traverser import handler

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload, context):
    """AgentCore Runtime entrypoint.

    Accepts the same payload structure as the existing Lambda handler:
    a JSON object with 'household_uri' (atlas:Household URI) and
    'persona_claim'.

    Returns a JSON object with the list of household member nodes
    and their relationships to the queried household.
    """
    return handler(payload, context)


if __name__ == "__main__":
    app.run()
