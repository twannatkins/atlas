# Workshop Authoring Directives

## Format
This is an AWS Workshop Studio site. Source files live in
content/<NN>-<slug>/index.md. Static assets live in static/.
Sidebar navigation and metadata are declared in contentspec.yaml.

## Authoring Rules

### One module page per spec module
Every module in the build spec (Section 3) corresponds to exactly
one Markdown file at content/<NN>-<slug>/index.md. Do not split
modules across files. Do not combine modules.

### Use the module page template — every page, every time
The template in spec Section 5.8.3 is normative. Headings appear
in the same order, with the same names. A page that omits a
heading or reorders headings is a bug, not a stylistic choice.

### Reference the notebook by cell number, not by reproducing code
A workshop step says "run cell 4 in notebook 03," not "paste
this code." The student is meant to open the notebook in
SageMaker. The guide is the navigation; the notebook is the
content. Reproducing notebook code in the Markdown duplicates
maintenance.

### Every visible output gets a screenshot
If a step produces a console state, a Neptune query result, a
SageMaker training metric, a SHACL validation report, or a
Streamlit UI render — there is a screenshot. No exceptions for
"obvious" outputs. The student cannot tell what is obvious.

### Screenshot filenames are lowercase, hyphenated, prefixed
Format: <NN>-step-<NN>-<slug>.png. Examples:
03-step-04-neptune-cluster-running.png,
06-step-08-shacl-validation-pass.png. The CI check enforces this.

### Image references resolve to existing files
Every ![alt](/static/images/foo.png) in any Markdown file points
at an actual file in static/images/. Placeholders are explicit
and use the exact filename that the screenshot will eventually
have, so the CI check can detect un-replaced placeholders.

### Expected output blocks are short
A code block under "Expected output" shows the first three to
five lines of what the student should see, not the full output.
The student is reading the guide on a phone or a second monitor;
the full output is in the notebook.

### Troubleshooting entries describe real failures
Three to four entries per module, each one a failure that has
actually happened during build or test. Hypothetical failures
("if Neptune is not running") do not belong here; they belong in
prerequisites or in the runbook.

### Cross-references use module slugs
A reference to another module looks like
"see [Module 6 — SHACL boundary](../06-shacl-boundary/)," not
"see Module 6" or "see the SHACL section." This makes the
generated site navigable.

### No screenshots of internal tools
The repo is public. No screenshots from internal Amazon UIs, no
internal account IDs, no internal email addresses, no
references to specific customers. The deny-list CI check from
the top-level CLAUDE.md applies to every Markdown file in
workshop/ as well.

## What This File is Not
This file does not specify the architecture, the ontology, the
data sources, or the build order. Those are in the build spec
(atlas-spec-v2.docx) and the top-level CLAUDE.md. This file is
narrowly about how to author the workshop guide so it stays in
lockstep with the code.
