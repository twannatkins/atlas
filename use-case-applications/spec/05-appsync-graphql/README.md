# 05 — AppSync GraphQL (FIBO-shaped)

The GraphQL schema that both UIs consume. FIBO-shaped means the types in the schema correspond to FIBO classes (or Workshop 1's `atlas:` extensions of them). A developer writing a UI component writes a GraphQL fragment against `Customer`, `Household`, `WealthSignal`, `AdvisoryRelationship` — not against arbitrary backend types.

## Why GraphQL, why FIBO-shaped

Two reasons the UI talks to GraphQL instead of calling agents directly:

1. **Shape.** The UI needs a schema it can write components against. GraphQL provides this; agent calls do not. A React component that renders a Customer 360 needs to know what fields exist on a Customer. The GraphQL schema is that contract.

2. **Legibility.** The schema being FIBO-shaped means anyone who knows FIBO can read it. A developer writing a new screen doesn't need to know which agent to call — they write a fragment against `Customer.advisoryRelationships`, and the resolver behind it figures out whether to call SPARQL, Entity Resolution, or a federated Iceberg table.

This is Thesis 2 from the architecture: two UIs, one backbone. The Wholesale UI and the Wealth UI both consume this schema. The differences between them are in the *lens* (which fragments they query, which fields they render), not the *substrate* (the schema itself).

## Schema design principles

- Every GraphQL type maps to exactly one ontology class (Workshop 1's `atlas:` or Workshop 2's `atlas-part-2:`)
- Field names are camelCase versions of the ontology property local names
- Connections (1:many relationships) use Relay-style pagination (`edges`, `node`, `cursor`)
- Every type that carries provenance has a `provenance` field returning `Provenance` type
- The schema does not expose internal identifiers — URIs are the identifiers

## Resolver patterns

Three resolver patterns cover all queries:

| Pattern | What it resolves | Backend |
|---|---|---|
| **SPARQL via Ontop** | Customer, Account, Household, Transaction, Holding | `atlas-sparql-mcp` → Ontop on ECS → Neptune SLGD (Lake Formation scoped via Iceberg) |
| **Direct Neptune SPARQL** | WealthSignal, RoutingDecision, AuditRecord, AdvisoryRelationship | `atlas-sparql-mcp` → Neptune SLGD directly |
| **Entity Resolution** | Canonical URI lookup when source-system IDs arrive | `atlas-er-mcp` |

All resolvers pass the user's persona claim through to the MCP server. The MCP server enforces Lake Formation scoping. The GraphQL layer does not duplicate that enforcement — it trusts the MCP layer.

## The schema

See `schema.graphql` for the full SDL. Key types:

### Core types (from Workshop 1 ontology)

```graphql
type Customer {
  uri: ID!
  customerId: String!
  label: String
  accounts: [Account!]!
  household: Household
  wealthSignals: [WealthSignal!]!
  advisoryRelationships: [AdvisoryRelationship!]!
  eligibility: Eligibility
  previousSurfacings: [PreviousSurfacing!]!
  provenance: Provenance
}
```

### Workshop 2 extension types

```graphql
type Referral {
  uri: ID!
  household: Household!
  signals: [WealthSignal!]!
  approvedRationale: String!
  routingDecision: RoutingDecision
  originatedBy: String!
  referralDate: DateTime!
  provenance: Provenance
}
```

### Capability palette type (from Agent Registry)

```graphql
type Capability {
  name: String!
  displayName: String!
  displayIcon: String!
  posture: String!
  capabilityTag: String!
}

type Query {
  capabilities(personaClaim: String!): [Capability!]!
}
```

## Persona scoping in GraphQL

The GraphQL API does not implement its own authorization layer. Instead:

1. The AppSync authorizer extracts the Cognito group claim (which maps to the IDC persona)
2. Every resolver passes that claim to the MCP server as `persona_claim`
3. The MCP server enforces Lake Formation scoping
4. The resolver returns whatever the MCP server returns — no additional filtering

This is the four-layer permission model in action: Identity (IDC) → Application (Cognito groups) → Data (Lake Formation via MCP) → Semantic (SHACL named graphs).

## Deployment

The AppSync API is deployed by the CDK stack (`spec/07-cdk-stack/`). The schema file in this directory is the source of truth; the CDK stack reads it at deploy time.

## What the novice learns

Notebook `04_graphql_federation.ipynb` teaches this layer. The novice:
1. Sees the schema and understands why each type maps to an ontology class
2. Executes three queries that exercise three different resolver patterns
3. Observes that the same query returns different data for different personas (because the resolver passes the persona claim through to the MCP server)
