# conversational-context-manager (Phase 2)

Maintains multi-turn conversation context for the Wealth UI's conversational surface using AgentCore Memory. Phase 2 only — Phase 1 has no conversational surface and does not need memory.

## Purpose

The Wealth UI lets an advisor ask follow-up questions: *"Which clients had a large wire? — Of those, which are showing engagement decay?"* The second question only makes sense if the agent remembers the first question's result set. `conversational-context-manager` is the memory layer that enables this.

## Posture

**Memory-backed, session-scoped.** Memory is per-session, not per-user-permanent. When a session ends, the memory is cleared. The agent does not retain long-term user state — that would create a privacy and audit liability.

## What it does

1. Receives a question, a session ID, and the user's persona claim.
2. Loads the session's prior context from AgentCore Memory.
3. Invokes `nl-to-sparql-agent` with the question *and the prior context* as input.
4. The selected query template can reference prior context (e.g., *"of those"* maps to a follow-up template that filters the prior result set).
5. Persists the new turn (question + result) to AgentCore Memory for the next turn.
6. Returns the result.

## What it does not do

- Does not persist beyond session. Memory clears at session end.
- Does not cross sessions. Each session is isolated; no user gets to "remember" between visits.
- Does not bypass the deterministic SPARQL layer. Memory is context for template selection, not a reasoner.

## Dependencies

- `nl-to-sparql-agent` (Phase 1) for the actual query execution
- AgentCore Memory service
