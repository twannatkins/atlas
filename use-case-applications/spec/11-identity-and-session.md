# Spec 11 — Identity, Session, and Memory Partitioning

## Overview

ATLAS Workshop 2 needs to answer two questions before doing real work for a user: "Who is this person, and what are they allowed to do?" and "What conversation are they in the middle of?"

The first question is *identity*. The second is *session*. This document explains how ATLAS handles both, using three AWS services that work together: **Amazon Cognito** (which authenticates users and issues identity tokens), **AWS AgentCore Identity** (which validates those tokens when our agents are called), and **AgentCore Memory** (which stores conversation context keyed by who the user is and which conversation they're in).

The combined model gives us per-user, per-session isolation — a guarantee that one user's conversations cannot accidentally show up in another user's context, even when they're using the same agents at the same time.

This document is the authoritative reference for the identity and session model. UIs implementing the pattern in Phase 07, notebooks demonstrating multi-turn conversations in Phase 06, and the reference script at `use-case-applications/scripts/identity-flow-reference.py` all follow what's described here.

## What a JWT is and why we use one

Before the four-step flow, a quick definition. A **JWT** (JSON Web Token, pronounced "jot") is a signed text token that carries a user's identity claims. When Cognito authenticates a user, it produces a JWT that looks like a long string of three base64-encoded parts joined by dots:

```
eyJhbGc...HEADER...eyJzdWIiOi...PAYLOAD...sIG.SIGNATURE
```

When the payload is decoded from base64, it's a JSON object with the user's claims:

```json
{
  "sub": "a1b2c3d4-...-user-uuid",
  "email": "advisor@example.bank",
  "custom:persona": "atlas-wealth-advisor",
  "exp": 1748102400,
  "iss": "https://cognito-idp.us-east-1.amazonaws.com/..."
}
```

The `sub` field is the stable per-user UUID assigned by Cognito the first time the user signed up. The `custom:persona` field is set when the user was created in Cognito (during the workshop's setup step) — it tells our agents which persona this user has, so MCP servers can scope data access accordingly.

The signature lets AgentCore Identity verify that the token actually came from Cognito and hasn't been tampered with. This is why a stolen JWT can't be forged.

## The four-step invocation flow

Every authenticated invocation of an AgentCore Runtime follows the same four steps. The Wholesale UI, the Wealth UI, the demonstration notebooks, and the reference script all follow this pattern.

**Step 1 — Acquire a JWT from Cognito.** The UI (or script) needs to prove who the user is. It does this by exchanging the user's credentials for a JWT via the `cognito-idp.InitiateAuth` API call. Cognito returns the JWT in the response — specifically, the `IdToken` field of the `AuthenticationResult`. This is the token we'll use for every subsequent agent invocation until it expires (typically after one hour, after which a refresh token can renew it).

**Step 2 — Present the JWT to AgentCore Identity.** When the UI calls an agent, it includes the JWT in the request's `Authorization` header in the form `Bearer <jwt>`. AgentCore Runtimes are configured to use AgentCore Identity as their authorization layer. AgentCore Identity does three checks: that the signature is valid (proving it really came from Cognito), that the token hasn't expired, and that it was issued by the Cognito user pool the Runtime is configured to trust.

**Step 3 — Invoke the Runtime with validated context.** If all three checks in Step 2 pass, AgentCore extracts the validated claims from the JWT and makes them available to the agent's handler function. The handler reads two key claims: `sub` (to know who the user is) and `custom:persona` (to know what they're authorized to do). The persona claim then gets passed down to every MCP server call, so persona-scoped access enforcement happens at the data layer.

**Step 4 — Persist state keyed by sub + session_id.** Some agents (currently only `conversational-context-manager`) maintain state across multiple turns of a conversation. These agents write to AgentCore Memory using a key that combines the user's `sub` claim and a `session_id` supplied by the UI. The full key pattern is `{AGENTCORE_MEMORY_NAMESPACE}/{session_id}` — where `AGENTCORE_MEMORY_NAMESPACE` is a per-stack prefix (default `"atlas-wealth-conv"`) and `session_id` is the value the UI sends in the invocation payload.

This is how the next turn of a conversation finds the previous turns: the UI sends the same `session_id` it sent before, and the agent loads the matching session context from Memory.

## Session ID strategy: per-conversation UUID

A natural question after reading Step 4: "How does the UI choose a `session_id`?"

The workshop uses **per-conversation UUID** as its session_id strategy. When a user clicks "Start new conversation" in either the Wholesale UI or the Wealth UI, the UI generates a fresh **UUID v4** (a 128-bit random identifier in a standard format like `f47ac10b-58cc-4372-a567-0e02b2c3d479`) and uses it as the `session_id` for every turn of that conversation. The UUID is stored in the browser's localStorage, keyed by the user's Cognito `sub` so it persists across logout and across browser sessions.

When does a UUID get cleared? Two cases:

1. **The user explicitly ends the conversation** — the UI calls its "End conversation" action, which removes the stored UUID. The next conversation starts fresh with a new UUID.
2. **An inactivity timeout fires** — the default is 8 hours. After 8 hours without any turn in the conversation, the UI considers the session stale and clears the UUID. This default is configurable in Phase 04 (CDK) and Phase 07 (UI implementation) if a customer needs longer or shorter conversation lifetimes.

### Why this strategy

We picked per-conversation UUID because it matches how bankers and advisors actually work in production wealth-management and consumer-banking applications. Three workflow needs drove the choice:

1. **Parallel conversations.** A wealth advisor might be reviewing Customer A's portfolio in one conversation thread while drafting a referral rationale for Customer B in another. A per-conversation UUID lets the advisor have multiple active conversations without their contexts mixing.

2. **Cross-session resumption.** An advisor starts a conversation, logs out for lunch, logs back in, and expects to find their conversation right where they left it. A UUID stored in localStorage survives the logout/login cycle.

3. **Explicit conversation lifecycle.** The advisor knows when a conversation is done. Giving the UI an explicit "End conversation" action that clears the UUID gives the user control, gives the audit team a clear endpoint to log, and keeps the Memory store from growing forever with abandoned half-conversations.

Alternative strategies (deterministic per-user-per-day hashing, browser-tab-scoped IDs) were considered. They're simpler but limit production workflows in ways that wouldn't serve real advisors.

## Per-session-per-user partitioning

The architectural commitment: **a user's session state is isolated from every other user's session state, and a single user can have multiple concurrent sessions that do not collide with each other.**

Three things make this work:

- **session_id is supplied by the UI**, not generated by the agent. The UI generates UUIDs, persists them in localStorage, and includes them on every agent invocation for that conversation. The agent doesn't pick session_ids on its own.

- **The Cognito sub claim provides user isolation**. Even in the vanishingly unlikely case that two users somehow generate the same UUID (UUID v4 has effectively no collision risk between users), the JWT carries the sub claim, which AgentCore Identity validates. Memory access happens within the validated identity context, so user A cannot read user B's session state even with the same session_id.

- **Memory namespace is per-stack, not per-user**. The CDK stack creates one Memory store per ATLAS deployment. All users' sessions live in that one store, partitioned by their key. The `AGENTCORE_MEMORY_NAMESPACE` env var (default `"atlas-wealth-conv"`) prefixes all keys, which lets a deployment host multiple logical namespaces within one Memory store if needed (e.g., separating Wealth conversations from Wholesale conversations).

## How this aligns with the regulatory posture

This identity and session model is designed to align directionally with the postures that banks operating under SR 11-7 (model risk management) and OCC 2011-12 (model governance) work within. The workshop does not claim to satisfy those regulations — formal model risk governance is a process well outside any workshop's scope — but the architectural patterns here are consistent with how production systems in regulated banks address similar concerns:

- **Per-user audit trail.** Every Runtime invocation logs the `sub` claim from the validated JWT, so audit teams can trace any agent action back to a specific authenticated user.

- **Cross-user isolation.** Memory access is gated by the validated identity context. A misconfigured agent handler cannot accidentally surface another user's session state.

- **Token revocation.** Cognito supports revoking tokens. When a user's access is revoked (e.g., termination, role change, security incident), in-flight tokens stop validating at Step 2, so no further Runtime invocations succeed for that user.

- **Session lifecycle visibility.** The per-conversation UUID strategy means sessions have explicit starts (UUID generated) and ends (UUID cleared). Audit teams can correlate session lifetimes against user activity in their compliance reviews.

## Reference implementation

The runnable reference for this flow is at `use-case-applications/scripts/identity-flow-reference.py`. The script demonstrates each of the four steps with inline comments that cross-reference back to this document. It supports a `--dry-run` flag that prints the intended actions without actually calling AWS — useful for understanding the flow without first provisioning a test Cognito user.

## Cross-references

- `spec/01-architecture.md` — auth context within the overall ATLAS architecture
- `spec/02-prerequisites.md` — Cognito user pool and AgentCore Identity setup steps
- `spec/05-appsync-graphql/resolver-patterns.md` — AppSync GraphQL's separate JWT validation pattern
- `spec/06-react-monorepo/README.md` — UI integration of this identity flow
- `spec/07-cdk-stack/README.md` — Cognito and Identity resources deployed by the CDK stack
- `spec/04-aws-agent-registry/mcp-servers/atlas-registry-mcp.md` — how the Registry uses the sub claim for capability discovery

## What this document does NOT cover

- AppSync GraphQL JWT validation, which is a separate flow (see `spec/05-appsync-graphql/resolver-patterns.md`)
- The four-layer permission model in detail (see `spec/01-architecture.md`)
- The persona claim's role in MCP server access control beyond the brief mention here (see `spec/04-aws-agent-registry/`)
- Memory store retention and removal policy at the AWS resource level (see `spec/07-cdk-stack/README.md`)
