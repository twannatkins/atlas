# CLAUDE.md — Workshop 2 (Use Case Applications)

Build directives for Claude Code when working in `use-case-applications/`.

This file is read by both Claude Code (the AI coding agent) and human contributors. Both audiences need to understand the same thing: *what to build, what not to touch, and why each rule exists.* Imperatives without rationale produce brittle compliance; rationale paired with imperatives produces consistent, durable code.

## What this workshop is

Workshop 2 teaches a novice how to take the agentic semantic layer from Workshop 1 and build governed banking applications on top of it. The deliverable is not just working code — it is *understanding*. The notebooks teach concepts; the code embodies them.

Every artifact in this directory exists to serve one of two purposes:

1. **Teach a concept** that a novice should leave Workshop 2 understanding (the notebook companion, the spec markdown, the READMEs).
2. **Produce an artifact** that demonstrates the concept in working form (the agents, the MCP servers, the GraphQL schema, the React apps, the CDK stack).

If a piece of code does neither — if it is incidental complexity, framework boilerplate, or premature optimization — it does not belong in Workshop 2.

## What you must not touch

The single most important rule. Workshop 1 (`../agentic-semantic-layer/`) is a stable artifact that downstream workshops, customer deployments, and the FSI standards mapping all depend on. **Workshop 2 never modifies Workshop 1.**

This means:

- Never edit any file in `../agentic-semantic-layer/ontology/`. If Workshop 2 needs a new class or property, add it to `use-case-applications/ontology-extensions/` under the `atlas-part-2:` namespace.
- Never edit any file in `../agentic-semantic-layer/mappings/`. If Workshop 2 needs additional federation, add the new R2RML mapping under `use-case-applications/mappings/` and reference it from Workshop 2's Ontop configuration.
- Never edit any file in `../agentic-semantic-layer/notebooks/`. If Workshop 2 needs a helper that doesn't exist in `shared/`, add it to `use-case-applications/notebooks/shared/` instead.
- Never edit `../agentic-semantic-layer/data/synthetic/`. The substitution guide (`09-substitution-guide.md`) explains how to use real data without modifying the synthetic seed.

If you find yourself wanting to modify a Workshop 1 file, stop. The intent is almost certainly addressable as a Workshop 2 extension. If it genuinely is not — if Workshop 1 has a bug that blocks Workshop 2 — open the change as a Workshop 1 commit with a clear bug label, not as a Workshop 2 modification.

## What to build

The Workshop 2 spec in `spec/` is the source of truth. Generate artifacts from the spec sections in this order:

1. **`spec/03-data-contracts.md`** — the contract between Workshop 1 and Workshop 2. Read this before anything else. Every assertion in here is verified by the pre-flight notebook.
2. **`spec/02-prerequisites.md`** — what must be true before any code runs.
3. **`spec/04-aws-agent-registry/`** — agent and MCP server descriptors. Generate the Lambda handlers, IAM policies, and registration scripts from these.
4. **`spec/05-appsync-graphql/`** — the FIBO-shaped schema and resolver patterns. The schema is built on Workshop 1's ontology classes; the resolvers federate via Ontop and direct AWS service calls.
5. **`spec/06-react-monorepo/`** — the largest section. Both UIs, every route, every component. Written for Kiro and Claude Code to consume; use shadcn/ui primitives, design tokens from `06-react-monorepo/design-system/tokens.md`.
6. **`spec/07-cdk-stack/`** — the infrastructure. Deploys Ontop on ECS, AppSync, Cognito, Lake Formation policies, CloudFront distributions, and the MCP server Lambdas.
7. **`spec/08-notebook-companion/`** — the teaching layer. Each notebook design includes the question, concept, build cells, verification cells, and what-just-changed bridge.

Do not skip the spec sections. Each one encodes architectural decisions that propagate downstream — generating code without reading the spec produces code that almost works and has subtle architectural drift from the intent.

## How to write the notebooks

The notebooks are the primary teaching mechanism. They are not build scripts.

Every notebook follows a five-section pattern: **the question**, **the concept**, **the build**, **the verification**, **what just changed**. See `spec/08-notebook-companion.md` for the full description and examples.

When generating notebook content:

- The question is concrete and novice-natural. Not *"How do we register an MCP server?"* (that's a how-to). *"Why do agents talk to MCP servers instead of directly to AWS services?"* (that's a question a novice would ask). The question opens the teaching.
- The concept is three to six paragraphs of plain-English narrative. No code. No AWS service names unless unavoidable. The novice should be able to read this section, close the laptop, and explain the idea to a colleague.
- Build cells are small — never more than 20 lines of code per cell. Each cell has a comment explaining what it does and why.
- Verification cells are *inspectable*. They print the response, show the registered record, run a test query. Each cell includes a remediation comment for what to do if it fails.
- "What just changed" is three to five sentences. What does the novice now have that they didn't before, and what becomes possible next?

When in doubt: more explanation, less code. A notebook with 10 cells of code and 30 paragraphs of explanation is correct for this audience. A notebook with 30 cells of code and 10 lines of comments is wrong.

## How to write the React UIs

The two UIs (`apps/wholesale-ui/` and `apps/wealth-ui/`) demonstrate the two-driver architecture: GraphQL drives what data is rendered, Agent Registry drives what actions are available. Both UIs share scaffolding via an Nx monorepo.

When generating UI code:

- Components are functional, hooks-based, TypeScript strict mode
- Styling uses shadcn/ui primitives and the design tokens from `spec/06-react-monorepo/design-system/tokens.md` — do not invent a parallel design system
- GraphQL fragments are written against Workshop 1's ontology classes (`fibo:Party` → `atlas:Customer`, etc.) — do not write fragments against types that don't exist in the schema
- Capability palettes are populated from live Agent Registry queries, not hardcoded — this is the lesson the UI is teaching
- The compliance banner reads *"Active compliance review — contact BSA team before client outreach"* — never *"SAR filed"* (the 31 U.S.C. §5318(g)(2) tipping-off prohibition makes the latter a federal crime)
- Provenance is visible in the UI — signal cards show the SHACL shape that fired and the R2RML mapping that produced the underlying triple

Every UI component should teach as well as function. A novice reading the component code should see *why* the structure is the way it is, not just what it renders.

## Conventions worth preserving

- File and directory names are lowercase-hyphenated (`wealth-ui`, not `WealthUI` or `wealth_ui`)
- The `atlas-part-2:` namespace IRI is used for every Workshop 2 ontology addition — never reuse `atlas:` for new concepts
- Notebook filenames are zero-padded and snake_case (`01_why_agents.ipynb`) to match Workshop 1's convention
- Markdown files use sentence case for headings, not Title Case — matches Workshop 1
- Code comments explain *why*, not *what*. The code is the *what*.
- Regulatory references are explicit and cited (SR 11-7, OCC 2011-12, 31 U.S.C. §5318(g)(2)) — these are teaching anchors, not legal disclaimers

## When you're unsure

Read the spec. If the spec is ambiguous, the data contracts document (`spec/03-data-contracts.md`) and the notebook companion (`spec/08-notebook-companion.md`) are the two most authoritative sources for resolving the ambiguity.

If neither resolves the question, the answer is whichever option *teaches better*. Workshop 2 is a teaching workshop first and an implementation reference second. When implementation elegance and teaching clarity conflict, teaching clarity wins.

## What success looks like

A novice who completes Workshop 2 should be able to:

1. Explain why agents in regulated industries cannot rely on LLMs alone
2. Describe the four-layer permission model and which layer enforces which permission
3. Articulate the difference between LLM-as-interface and LLM-as-reasoner
4. Walk through the Rachel Kim referral scenario end-to-end without reading from notes
5. Adapt the same pattern to a new use case (commercial banking, compliance investigation, executive analytics)

If the code Claude Code generates passes every verification cell but the novice cannot do the five things above, the workshop has failed. The artifacts are evidence; the understanding is the goal.
