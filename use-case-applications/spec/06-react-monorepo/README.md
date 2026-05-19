# 06 — React monorepo

Two applications, one monorepo. The Wholesale UI serves Consumer Bankers (Phase 1). The Wealth UI serves Wealth Advisors (Phase 2). Both consume the same FIBO-shaped GraphQL API and the same Agent Registry. The differences are in the lens, not the substrate.

## Monorepo structure

```
use-case-applications/apps/
├── wholesale-ui/              # Phase 1 — Consumer Banker referral workflow
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx       # Dashboard: assigned book overview
│   │   │   ├── customers/
│   │   │   │   └── [uri]/
│   │   │   │       └── page.tsx   # Entity 360
│   │   │   └── referrals/
│   │   │       └── [uri]/
│   │   │           └── page.tsx   # Referral Detail
│   │   ├── components/
│   │   │   ├── capability-palette.tsx
│   │   │   ├── compliance-banner.tsx
│   │   │   ├── entity-360.tsx
│   │   │   ├── signal-card.tsx
│   │   │   ├── provenance-badge.tsx
│   │   │   ├── household-strip.tsx
│   │   │   └── rationale-editor.tsx
│   │   ├── graphql/
│   │   │   ├── fragments.ts
│   │   │   ├── queries.ts
│   │   │   └── mutations.ts
│   │   └── hooks/
│   │       ├── use-capabilities.ts
│   │       ├── use-customer.ts
│   │       └── use-signals.ts
│   ├── package.json
│   └── tsconfig.json
│
├── wealth-ui/                 # Phase 2 — Wealth Advisor workbench
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx       # Advisor dashboard: coverage book
│   │   │   ├── clients/
│   │   │   │   └── [uri]/
│   │   │   │       └── page.tsx   # Client 360 (advisor perspective)
│   │   │   ├── themes/
│   │   │   │   └── page.tsx   # Market themes
│   │   │   └── conversations/
│   │   │       └── page.tsx   # Conversational surface
│   │   ├── components/
│   │   │   ├── capability-palette.tsx
│   │   │   ├── client-360.tsx
│   │   │   ├── theme-card.tsx
│   │   │   ├── conversation-panel.tsx
│   │   │   └── coverage-strip.tsx
│   │   ├── graphql/
│   │   │   ├── fragments.ts
│   │   │   ├── queries.ts
│   │   │   └── mutations.ts
│   │   └── hooks/
│   │       ├── use-capabilities.ts
│   │       ├── use-client.ts
│   │       └── use-themes.ts
│   ├── package.json
│   └── tsconfig.json
│
└── shared/                    # Shared libraries across both UIs
    ├── ui/                    # shadcn/ui primitives + design tokens
    │   ├── components/
    │   │   ├── button.tsx
    │   │   ├── card.tsx
    │   │   ├── badge.tsx
    │   │   ├── dialog.tsx
    │   │   ├── input.tsx
    │   │   └── ...
    │   └── tokens.css
    ├── graphql-client/        # Apollo Client configuration
    │   └── client.ts
    └── auth/                  # Cognito auth hooks
        └── use-auth.ts
```

## Technology choices

| Choice | Rationale |
|---|---|
| **Next.js 14 (App Router)** | File-based routing, server components for initial data fetch, client components for interactivity |
| **TypeScript strict mode** | Type safety across GraphQL fragments and component props |
| **Apollo Client** | GraphQL client with normalized cache; fragments map cleanly to ontology types |
| **shadcn/ui** | Accessible, composable primitives; no vendor lock-in; design tokens via CSS variables |
| **Nx monorepo** | Shared libraries, consistent tooling, incremental builds |
| **Tailwind CSS** | Utility-first styling via design tokens; no custom CSS files |

## The two-driver pattern in code

Every page in both UIs follows the same data-fetching pattern:

```typescript
// Driver 1: GraphQL provides data
const { data } = useQuery(CUSTOMER_QUERY, { variables: { uri } });

// Driver 2: Agent Registry provides capabilities
const { capabilities } = useCapabilities(personaClaim);

// The page renders data + capabilities together
return (
  <Entity360 customer={data.customer}>
    <CapabilityPalette capabilities={capabilities} />
  </Entity360>
);
```

The `useCapabilities` hook queries the registry live. When a new agent is registered, the palette updates without a redeploy.

## What each UI teaches

| UI | Thesis it demonstrates | Key teaching moment |
|---|---|---|
| **Wholesale UI** | Thesis 4 (four-layer permissions) | Same URL, different persona → different view |
| **Wealth UI** | Thesis 2 (two UIs, one backbone) | Same GraphQL schema, structurally different application |

## Phase 1 scope (this PR)

Phase 1 builds the Wholesale UI only. The Wealth UI is Phase 2. The shared libraries are built in Phase 1 because the Wholesale UI needs them, and they are designed to be reused by the Wealth UI without modification.
