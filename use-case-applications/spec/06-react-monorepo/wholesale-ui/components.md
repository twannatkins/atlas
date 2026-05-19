# Wholesale UI components

Every component in the Wholesale UI teaches as well as functions. A novice reading the component code should see *why* the structure is the way it is.

## `capability-palette.tsx`

**Purpose:** Renders the set of actions available to the current user. Populated live from the Agent Registry, never hardcoded.

**Props:**
```typescript
interface CapabilityPaletteProps {
  personaClaim: string;
  onInvoke: (capabilityName: string) => void;
}
```

**Behavior:**
- On mount, queries `atlas-registry-mcp.list_capabilities(persona_claim)`
- Renders each capability as a button with `display_icon` and `display_name`
- Groups by `capability_tag` (deterministic, human-in-loop, workflow)
- Disables capabilities that require prerequisites not yet met (e.g., "Route to advisor" disabled until rationale is approved)

**Teaching comment in code:**
```typescript
// The palette is populated from the registry, not hardcoded.
// When a new agent is registered, this palette updates automatically.
// This is Thesis 1: registry-first agent discovery.
```

## `compliance-banner.tsx`

**Purpose:** Displays the compliance status banner. Respects the tipping-off prohibition.

**Props:**
```typescript
interface ComplianceBannerProps {
  hasComplianceReview: boolean;
  personaClaim: string;
}
```

**Behavior:**
- If `!hasComplianceReview`: renders nothing
- If `personaClaim === "atlas-bsa-analyst"`: renders SAR-specific detail
- Otherwise: renders `"Active compliance review — contact BSA team before client outreach"`
- NEVER renders "SAR filed" for non-BSA personas

**Teaching comment in code:**
```typescript
// 31 U.S.C. §5318(g)(2) makes it a federal crime to disclose to anyone
// outside the BSA function that a SAR has been filed. The Consumer Banker
// is outside the BSA function. This banner tells them what they are
// allowed to know — that a review is active — without disclosing what
// kind of review it is.
```

## `signal-card.tsx`

**Purpose:** Renders a single wealth signal with its strength indicator and provenance.

**Props:**
```typescript
interface SignalCardProps {
  signalType: string;
  strength: 'strong' | 'moderate' | 'weak' | 'gap';
  signalDate?: string;
  provenance: {
    validatedBy: string;   // SHACL shape URI
    derivedFrom: string;   // R2RML mapping path
    generatedBy: string;   // Agent that produced it
  };
}
```

**Behavior:**
- Left border color from `--color-signal-{strength}` token
- Provenance badge rendered inline showing shape + mapping
- Signal type displayed as human-readable label (mapped from SKOS prefLabel)

**Teaching comment in code:**
```typescript
// Provenance is visible, not hidden. The novice should see exactly
// which SHACL shape validated this signal and which R2RML mapping
// produced the underlying triple. This is what makes ATLAS auditable.
```

## `provenance-badge.tsx`

**Purpose:** A small inline badge showing where a piece of data came from.

**Props:**
```typescript
interface ProvenanceBadgeProps {
  validatedBy?: string;
  derivedFrom?: string;
  generatedBy?: string;
}
```

**Behavior:**
- Renders as a pill-shaped badge with provenance token colors
- Tooltip on hover shows full URIs
- Compact display: `"WealthSignalTypeShape · pattern_a_iceberg"`

## `household-strip.tsx`

**Purpose:** Inline graph visualization showing 1-hop neighbors of a household.

**Props:**
```typescript
interface HouseholdStripProps {
  householdUri: string;
  personaClaim: string;
}
```

**Behavior:**
- On mount, invokes `household-traverser` agent via the registry
- Renders nodes as connected pills: `[Anjali Patel] — [Raj Patel] — [Checking 4421]`
- Each node is clickable (navigates to Entity 360 for that entity)
- Limited to 1-hop by design (deeper traversals are explicit user actions)

## `rationale-editor.tsx`

**Purpose:** Displays the drafted rationale for review and editing. The human-in-the-loop control.

**Props:**
```typescript
interface RationaleEditorProps {
  householdUri: string;
  signalUris: string[];
  personaClaim: string;
  onApprove: (approvedText: string) => void;
}
```

**Behavior:**
- "Generate draft" button invokes `referral-rationale-drafter` via registry
- Draft appears in an editable textarea
- Displays `is_probabilistic: true` and `requires_human_review: true` badges prominently
- "Approve and route" button is disabled until the banker has reviewed (textarea must be focused at least once)
- On approve, calls `onApprove` with the final text, which triggers `referral-orchestrator`

**Teaching comment in code:**
```typescript
// This is the human-in-the-loop pattern. The agent drafts; the human
// approves. The "Approve and route" button is the gate. No path exists
// to auto-route without the banker clicking this button.
// This is what makes the probabilistic agent compliant with SR 11-7.
```

## `entity-360.tsx`

**Purpose:** Page-level layout for the Customer 360 view.

**Props:**
```typescript
interface Entity360Props {
  customer: Customer;
  children: React.ReactNode; // capability palette slot
}
```

**Behavior:**
- Two-column layout: main content (signals, accounts, relationships) + sidebar (capability palette)
- Sections: Identity header, Wealth Signals, Accounts & Holdings, Household, Advisory Relationships
- Each section loads independently (suspense boundaries)
