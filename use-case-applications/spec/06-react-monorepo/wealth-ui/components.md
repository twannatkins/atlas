# Wealth UI components

## `capability-palette.tsx`

Shared with the Wholesale UI — same component, different results because the registry filters by persona. The Wealth Advisor sees theme-summarizer, conversational-context-manager, and behavioral-signal-agent instead of referral-orchestrator and referral-rationale-drafter.

## `coverage-strip.tsx`

**Purpose:** Shows advisory relationship status — active coverage, historical assignments, and gaps.

**Props:**
```typescript
interface CoverageStripProps {
  relationships: AdvisoryRelationship[];
}
```

**Behavior:**
- Active relationships render with green border and "Active" badge
- Historical relationships collapse into a `<details>` element
- Empty state shows "No advisory coverage — this client is unassigned" in red

## `theme-card.tsx`

**Purpose:** Renders a market or portfolio theme with relevance score.

**Props:**
```typescript
interface ThemeCardProps {
  theme: string;
  relevance?: number;
  summary?: string;
}
```

**Behavior:**
- Displays theme name, relevance percentage, and optional summary
- Always shows "probabilistic" badge (theme-summarizer output is probabilistic)
- Does not render action buttons — themes are informational only

## `conversation-panel.tsx`

**Purpose:** Multi-turn conversational surface with session-scoped memory.

**Props:**
```typescript
interface ConversationPanelProps {
  clientUri?: string;
  personaClaim: string;
}
```

**Behavior:**
- Message history renders user questions and assistant responses
- Input field with Enter-to-send
- Responses include the SPARQL that was executed (transparency)
- Session-scoped: refreshing the page starts a new session
- In production: invokes conversational-context-manager via registry
