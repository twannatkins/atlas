# atlas-registry-mcp

The MCP server that exposes the Agent Registry itself. The UI uses this to populate the capability palette; Kiro uses it to discover what agents exist in the registry without hardcoding.

## Purpose

`atlas-registry-mcp` makes the Agent Registry itself accessible as an MCP server. This sounds circular — but it is the right design. The registry is a service like any other; exposing it through MCP means the UI's capability palette and Kiro's discovery flow use the same protocol everything else does.

## What it exposes

- `list_capabilities(persona_claim)` — return all agents and MCP servers discoverable by the given persona
- `get_agent(agent_name)` — return the registry record for a specific agent
- `get_mcp_server(mcp_name)` — return the registry record for a specific MCP server
- `invoke_capability(capability_uri, input_payload, persona_claim)` — proxy invocation through the registry's audit path

## What it does not do

- Does not bypass the registry's persona filtering. Discovery is always claim-scoped.
- Does not invoke unregistered Lambdas. If a capability is not in the registry, it cannot be invoked through this server.

## Dependencies

- AWS Agent Registry
- Phase 1: IAM-based auth. Phase 2: JWT-based auth via Cognito.
