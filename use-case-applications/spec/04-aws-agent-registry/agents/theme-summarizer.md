# theme-summarizer (Phase 2)

Summarizes market and portfolio themes from source articles into short narratives shown on the Wealth UI's Themes route. Probabilistic, draft-only.

## Purpose

A Wealth Advisor's day starts with a quick read of what is happening in the market — which themes are moving, which portfolio sectors are exposed, what the relevant news headlines say. `theme-summarizer` produces these summaries from the underlying source articles.

## Posture

**Probabilistic, draft-only.** Output is informational, not action-driving. The agent has no path to commit anything to the graph or trigger downstream workflows. Output is read-only for advisor context.

## What it does

1. Receives a theme identifier and the user's persona claim.
2. Retrieves the source articles linked to the theme via `atlas-part-2:ThemeAssertion`.
3. Generates a 2-3 sentence summary via Bedrock.
4. Returns the summary with provenance: which articles informed it.

## What it does not do

- Does not recommend trades. Themes inform; advisors decide.
- Does not write to the graph. Summaries are computed on demand.
- Does not invent themes. The theme set is curated and validated upstream.

## Dependencies

- `atlas-sparql-mcp` for theme and article retrieval
- Bedrock text generation
