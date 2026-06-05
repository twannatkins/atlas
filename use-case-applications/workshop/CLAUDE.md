# Workshop 2 Authoring Directives

## Format

This is an AWS Workshop Studio site for Workshop 2 (Use Case Applications).
Source files live in `content/<NN>-<slug>/index.md`. Static assets live in `static/`.
Sidebar navigation and metadata are declared in `contentspec.yaml`.

The master spec for all notebook content is `../spec/08-notebook-companion.md`.
The prerequisites spec is `../spec/02-prerequisites.md`.
The data contracts are in `../spec/03-data-contracts.md`.

## Authoring Rules

### One module page per notebook

Each Workshop 2 notebook maps to exactly one Markdown file at
`content/<NN>-<slug>/index.md`. Do not split notebooks across files.
Do not combine notebooks.

| Module directory | Notebook |
|---|---|
| `01-preflight/` | `phase-1-referral/00_preflight.ipynb` |
| `02-why-agents/` | `phase-1-referral/01_why_agents.ipynb` |
| `03-mcp-servers/` | `phase-1-referral/02_mcp_servers.ipynb` |
| `04-agent-registry/` | `phase-1-referral/03_agent_registry.ipynb` |
| `05-graphql-federation/` | `phase-1-referral/04_graphql_federation.ipynb` |
| `06-wholesale-ui/` | `phase-1-referral/06_wholesale_ui.ipynb` |
| `07-phase-1-acceptance/` | `phase-1-referral/07_phase_1_acceptance.ipynb` |
| `08-phase-2-agents/` | `phase-2-advisor/01_phase_2_agents.ipynb` |
| `09-agentcore-memory/` | `phase-2-advisor/02_agentcore_memory.ipynb` |
| `10-wealth-ui/` | `phase-2-advisor/03_wealth_ui.ipynb` |
| `11-jwt-auth/` | `phase-2-advisor/04_jwt_auth.ipynb` |
| `12-end-to-end/` | `phase-2-advisor/05_end_to_end.ipynb` |
| `13-phase-2-acceptance/` | `phase-2-advisor/06_phase_2_acceptance.ipynb` |

### Use the module page template — every page, every time

Page structure (same order, every page, no omissions):

1. YAML frontmatter (`title`, `weight`)
2. H1 matching `title`
3. `## Learning Objectives`
4. `## Time Estimate`
5. `## Prerequisites`
6. `## What You Will Build`
7. `## Steps` (numbered H3 sub-sections, with expected output blocks)
8. `## Expected Outputs`
9. `## Troubleshooting` (three to five entries)
10. `## What's Next`

### Reference the notebook by cell, not by reproducing code

Workshop steps say "run cell 4 in `02_mcp_servers.ipynb`," not "paste this code."
The attendee opens the notebook in SageMaker. The guide is navigation; the notebook is content.

### Every visible output gets a screenshot placeholder

Every step that produces console state, a query result, a registered record, or a
UI render includes an image reference. Placeholders use the eventual filename so the
CI check can detect un-replaced files.

Screenshot filename format: `<NN>-step-<NN>-<slug>.png`
Example: `03-step-04-mcp-sparql-response.png`

### Expected output blocks are short

Code blocks under "Expected output" show three to five lines — not the full output.
The full output is in the notebook; the guide gives a landmark the attendee can match.

### Troubleshooting entries describe real failures

Three to five entries per module. Hypothetical failures belong in prerequisites.

### Cross-references use module slugs

`[Module 3 — MCP Servers](../03-mcp-servers/)` not "Module 3" or "the MCP section."

### Module 3 must include the AgentCore/"Why MCP" summary

The `03-mcp-servers/index.md` page must contain a one-to-two paragraph summary of
why ATLAS uses MCP specifically — covering AgentCore Runtimes as the production
deployment target and the indirection value. This content was authored in
`02_mcp_servers.ipynb` cell `cell-02-concept` during Phase 06 and must be surfaced
in the workshop guide so attendees encounter it before they open the notebook.

### No screenshots of internal tools

No internal Amazon UIs, no internal account IDs, no internal email addresses.
