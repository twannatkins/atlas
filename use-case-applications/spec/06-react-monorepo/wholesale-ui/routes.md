# Wholesale UI routes

The Wholesale UI has three routes. Each demonstrates a different aspect of the two-driver architecture.

## Route 1 — Dashboard (`/`)

**What it shows:** The Consumer Banker's assigned book of clients, sorted by signal strength. A quick-scan view that answers "who should I look at today?"

**Data driver (GraphQL):**
```graphql
query Dashboard {
  searchCustomers(query: "", limit: 50) {
    uri
    customerId
    label
    wealthSignals {
      signalType
      strength
      signalDate
    }
    household {
      uri
      label
      memberCount
    }
  }
}
```

**Capability driver (Registry):** The capability palette is rendered in the sidebar. On the dashboard, it shows global actions (e.g., "Detect wealth signals" for batch detection).

**Teaching moment:** The dashboard only shows the banker's assigned book (45 of 200 customers) because Lake Formation scopes the query by persona. The novice should notice that the same query run by a BSA Analyst would return all 200.

## Route 2 — Entity 360 (`/customers/[uri]`)

**What it shows:** Full detail for a single customer: accounts, holdings, transactions, wealth signals with provenance, household membership, advisory relationships.

**Data driver (GraphQL):**
```graphql
query Customer360($uri: ID!) {
  customer(uri: $uri) {
    uri
    customerId
    label
    accounts {
      accountId
      accountType
      balanceUSD
      transactions(limit: 10) {
        transactionDate
        amountUSD
        transactionType
      }
    }
    wealthSignals {
      uri
      signalType
      strength
      signalDate
      provenance {
        validatedBy
        derivedFrom
        generatedBy
      }
    }
    household {
      uri
      label
      members {
        uri
        label
      }
    }
    advisoryRelationships {
      advisor { label }
      coverageStartDate
      isActive
    }
  }
}
```

**Capability driver (Registry):** Context-specific capabilities appear based on the entity state. If the customer has signals but no advisor, "Route to advisor" and "Draft referral rationale" appear. If the customer already has an active advisory relationship, those capabilities are suppressed.

**Components on this page:**
- `entity-360.tsx` — the page layout
- `signal-card.tsx` — one per wealth signal, with provenance badge
- `provenance-badge.tsx` — shows SHACL shape + R2RML mapping
- `household-strip.tsx` — inline graph view (from household-traverser)
- `capability-palette.tsx` — sidebar actions

## Route 3 — Referral Detail (`/referrals/[uri]`)

**What it shows:** A specific referral in progress or completed. The signals that triggered it, the drafted rationale (editable if pending), the routing decision, the audit trail.

**Data driver (GraphQL):**
```graphql
query ReferralDetail($uri: ID!) {
  household(uri: $uri) {
    label
    members { uri label }
  }
  wealthSignals(customerUri: $uri) {
    signalType
    strength
    provenance { validatedBy derivedFrom }
  }
  referrals(householdUri: $uri) {
    approvedRationale
    routingDecision {
      selectedRoute
      humanReview { reviewOutcome reviewDate }
    }
    provenance { generatedBy generatedAtTime }
  }
}
```

**Capability driver (Registry):** "Draft referral rationale" (invokes referral-rationale-drafter) and "Route to advisor" (invokes referral-orchestrator). Both require the human-in-the-loop pattern: the rationale must be reviewed and approved before routing.

**Components on this page:**
- `compliance-banner.tsx` — the tipping-off-safe banner
- `signal-card.tsx` — signals that justify the referral
- `rationale-editor.tsx` — editable draft with "Approve and route" button
- `household-strip.tsx` — relationship context
- `provenance-badge.tsx` — on every signal and decision

**The compliance banner rule:**
- If the household has an active compliance review: show `"Active compliance review — contact BSA team before client outreach"`
- Never show `"SAR filed"` or any SAR-specific language to non-BSA personas
- The banner component checks `persona_claim !== "atlas-bsa-analyst"` before rendering the safe version
