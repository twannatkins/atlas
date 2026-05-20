# Wealth UI routes

The Wealth UI has four routes. Each demonstrates a Phase 2 capability that the Wholesale UI does not have.

## Route 1 — Advisor dashboard (`/`)

**What it shows:** The Wealth Advisor's assigned client book with coverage status and engagement indicators.

**Data driver (GraphQL):**
```graphql
query AdvisorDashboard($limit: Int) {
  searchCustomers(query: "", limit: $limit) {
    uri
    customerId
    label
    advisoryRelationships {
      advisor { label }
      isActive
      coverageStartDate
    }
  }
}
```

**Capability driver (Registry):** Wealth Advisor palette — behavioral-signal-agent, theme-summarizer, conversational-context-manager, nl-to-sparql-agent.

**Teaching moment:** The same `searchCustomers` query returns different clients than the Wholesale UI because Lake Formation scopes by persona. The Wealth Advisor sees their assigned coverage book, not the Consumer Banker's referral pipeline.

## Route 2 — Client 360 (`/clients/[uri]`)

**What it shows:** Full advisor-perspective detail: coverage history, behavioral signals, themes, and the conversational surface.

**Teaching moment:** Same `Customer` GraphQL type as the Wholesale UI but different fragments. The Wealth UI selects `advisoryRelationships`, `themes`, and `behavioralSignals`; the Wholesale UI selects `wealthSignals`, `household`, and `coverageGap`. Same backbone, different lens.

## Route 3 — Themes (`/themes`)

**What it shows:** Market and portfolio themes summarized by the theme-summarizer agent. Informational only — does not drive actions.

**Teaching moment:** The theme-summarizer is probabilistic and carries `is_probabilistic: true`. The UI renders a "probabilistic" badge on every theme card to make this visible. Themes inform; they do not recommend.

## Route 4 — Conversations (`/conversations`)

**What it shows:** Multi-turn conversational surface powered by conversational-context-manager with AgentCore Memory.

**Teaching moment:** Follow-up questions ("Of those, which...") work because memory persists within the session. Starting a new session clears all context — no permanent user state.
