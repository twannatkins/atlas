# atlas-fibo-mcp

The MCP server that exposes FIBO class introspection and ontology browsing. Used by UIs that need to display human-readable class labels and by `atlas-ontology-steward` personas browsing the model.

## Purpose

The GraphQL schema and the UI reference FIBO classes (`fibo:LegalPerson`, `fibo:Account`, etc.) and Workshop 1's `atlas:` extensions. Sometimes the UI needs to display these to a human — *"You're viewing a fibo:LegalPerson"* should appear as *"You're viewing a Legal Entity"*. `atlas-fibo-mcp` resolves class URIs to human-readable labels and parent class hierarchies.

## What it exposes

- `class_info(class_uri)` — label, comment, parent classes, FIBO alignment
- `list_classes(namespace_prefix)` — list all classes in a namespace
- `subclasses_of(class_uri)` — find subclasses (used by capability filtering)

## What it does not do

- Does not modify the ontology
- Does not validate (that's `atlas-shacl-mcp`)

## Dependencies

- Workshop 1's ontology TTL files loaded into Neptune
