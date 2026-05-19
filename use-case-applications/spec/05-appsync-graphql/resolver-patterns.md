# Resolver patterns

Every resolver in the ATLAS GraphQL API delegates to an MCP server. The resolver itself is thin — it translates the GraphQL field selection into an MCP operation call and shapes the response back into the GraphQL type. No business logic lives in resolvers.

## Pattern 1 — SPARQL via Ontop (federated read path)

Used for: `customer`, `household`, `searchCustomers`, `accounts`, `transactions`, `holdings`

```
GraphQL query arrives
    ↓
AppSync resolver extracts persona claim from Cognito context
    ↓
Resolver builds SPARQL SELECT from the GraphQL field selection
    ↓
Resolver calls atlas-sparql-mcp.query(sparql, persona_claim, graph_tier="slgd")
    ↓
atlas-sparql-mcp routes through Ontop on ECS Fargate
    ↓
Ontop translates SPARQL to SQL against Lake Formation-scoped Iceberg tables
    ↓
Lake Formation enforces row/column filters based on persona claim
    ↓
Results flow back through Ontop → MCP → Resolver → GraphQL response
```

This is the primary read path for entity data. Lake Formation scoping means a Consumer Banker's query returns only their assigned book of clients, while a BSA Analyst's query returns the full corpus with compliance fields visible.

### Example resolver (pseudo-code)

```python
def resolve_customer(uri, info):
    persona = info.context["persona_claim"]
    sparql = f"""
        SELECT ?customerId ?label WHERE {{
            <{uri}> a atlas:Customer ;
                atlas:customerId ?customerId .
            OPTIONAL {{ <{uri}> rdfs:label ?label }}
        }}
    """
    result = invoke_mcp("atlas-sparql-mcp", "query", {
        "sparql": sparql,
        "persona_claim": persona,
        "graph_tier": "slgd",
    })
    row = result["rows"][0] if result["rows"] else None
    return {"uri": uri, "customerId": row["customerId"], "label": row.get("label")}
```

## Pattern 2 — Direct Neptune SPARQL (graph-native data)

Used for: `wealthSignals`, `advisoryRelationships`, `referrals`, `auditTrail`, `routingDecision`

Same as Pattern 1 but the MCP server queries Neptune directly (not through Ontop) because the data lives natively in the graph, not in Iceberg tables.

```
Resolver calls atlas-sparql-mcp.query(sparql, persona_claim, graph_tier="slgd")
    ↓
atlas-sparql-mcp queries Neptune SLGD directly (no Ontop)
    ↓
Named graph scoping (SHACL semantic layer) filters results
```

The distinction matters for performance: Ontop adds latency for the SQL translation step. Graph-native data (signals, routing decisions, audit records) skips that step.

## Pattern 3 — Entity Resolution

Used for: `resolveEntity`

```
Resolver calls atlas-er-mcp.lookup(source_system, source_id)
    ↓
atlas-er-mcp calls AWS Entity Resolution GetMatchId
    ↓
Returns canonical URI
    ↓
Resolver uses canonical URI to fetch Customer via Pattern 1
```

This pattern is used when a source-system ID arrives (e.g., from a CRM integration) and needs to be resolved to the canonical graph URI before further queries.

## Pattern 4 — Agent Registry (capability palette)

Used for: `capabilities`

```
Resolver calls atlas-registry-mcp.list_capabilities(persona_claim)
    ↓
Registry returns persona-filtered list of agents and MCP servers
    ↓
Resolver maps to Capability type
```

This is how the UI populates its capability palette without hardcoding agent names.

## Pattern 5 — Agent invocation (mutations)

Used for: `routeReferral`, `detectSignals`

```
Resolver calls atlas-registry-mcp.invoke_capability(capability_uri, input_payload, persona_claim)
    ↓
Registry proxies to the target agent Lambda
    ↓
Agent executes and returns result
    ↓
Resolver maps result to GraphQL mutation response type
```

Mutations always go through the registry's audit path so every invocation is recorded.

## Persona claim flow

The persona claim flows from the user's browser to the deepest data layer:

```
Browser → Cognito JWT → AppSync authorizer extracts group claim
    ↓
AppSync passes claim in resolver context
    ↓
Resolver passes claim to MCP server
    ↓
MCP server passes claim to Lake Formation / Neptune named graph filter
```

At no point does the GraphQL layer make its own authorization decision. It trusts the MCP layer to enforce scoping. This is deliberate: authorization logic lives in one place (the MCP server), not scattered across resolvers.
