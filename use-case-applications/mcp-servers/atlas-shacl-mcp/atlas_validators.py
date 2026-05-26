"""
atlas_validators — SHACL and ontology validation utilities.

Wraps pyshacl for all SHACL validation in the workshop. Every call to
validate_graph() returns a ValidationResult with a conformance flag,
a violation list, and a plain-English summary suitable for inclusion
in the model-risk-review.md deliverable.

Component class: DETERMINISTIC — given the same data graph and shapes
graph, the validator always produces the same result.

pyshacl version pinned in notebooks/shared/requirements.txt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

from rdflib import Graph
import pyshacl


@dataclass
class ValidationResult:
    """Result of a SHACL validation run."""

    conforms: bool
    violations: List[str] = field(default_factory=list)
    summary: str = ""

    def assert_conforms(self) -> None:
        """Raise AssertionError with violation detail if the graph does not conform."""
        if not self.conforms:
            detail = "\n  ".join(self.violations) if self.violations else "(no detail)"
            raise AssertionError(
                f"SHACL validation failed with {len(self.violations)} violation(s):\n  {detail}"
            )

    def __repr__(self) -> str:
        status = "PASS" if self.conforms else "FAIL"
        return f"ValidationResult({status}, violations={len(self.violations)})"


def validate_graph(
    data_graph: Union[Graph, str],
    shapes_source: Union[Graph, str, Path],
    *,
    inference: str = "rdfs",
    abort_on_first: bool = False,
) -> ValidationResult:
    """Validate a data graph against a SHACL shapes graph.

    Parameters
    ----------
    data_graph:
        An rdflib Graph or a Turtle string containing the data to validate.
    shapes_source:
        An rdflib Graph, a Turtle string, or a Path to a .ttl file containing
        the SHACL shapes.
    inference:
        RDFS / OWL inference level passed to pyshacl. Default 'rdfs'.
    abort_on_first:
        Stop validation after the first violation. Useful for fast CI checks.

    Returns
    -------
    ValidationResult
    """
    # Normalise data_graph
    if isinstance(data_graph, str):
        dg = Graph()
        dg.parse(data=data_graph, format="turtle")
    else:
        dg = data_graph

    # Normalise shapes_source
    if isinstance(shapes_source, Path):
        sg = Graph()
        sg.parse(str(shapes_source), format="turtle")
    elif isinstance(shapes_source, str):
        sg = Graph()
        sg.parse(data=shapes_source, format="turtle")
    else:
        sg = shapes_source

    conforms, results_graph, results_text = pyshacl.validate(
        dg,
        shacl_graph=sg,
        inference=inference,
        abort_on_first=abort_on_first,
        serialize_report_graph=False,
    )

    # Extract violation messages from the results graph
    violations: List[str] = []
    if not conforms:
        from rdflib.namespace import SH
        for result in results_graph.subjects(
            RDF.type, SH.ValidationResult
        ):
            msg_nodes = list(results_graph.objects(result, SH.resultMessage))
            path_nodes = list(results_graph.objects(result, SH.resultPath))
            msg = str(msg_nodes[0]) if msg_nodes else "(no message)"
            path = str(path_nodes[0]) if path_nodes else "(no path)"
            violations.append(f"{path}: {msg}")

        # Fallback: use pyshacl text report if graph traversal yielded nothing
        if not violations and results_text:
            violations = [line for line in results_text.splitlines() if line.strip()]

    summary = _build_summary(conforms, violations)
    return ValidationResult(conforms=conforms, violations=violations, summary=summary)


def _build_summary(conforms: bool, violations: List[str]) -> str:
    if conforms:
        return "SHACL validation passed. The graph conforms to all shapes."
    lines = [
        f"SHACL validation failed with {len(violations)} violation(s).",
        "Each violation below identifies the shape path and the constraint message.",
        "Resolve violations before promoting data from the LGD to the SLGD.",
        "",
    ]
    for i, v in enumerate(violations, 1):
        lines.append(f"  {i}. {v}")
    return "\n".join(lines)


def validate_ontology_completeness(
    ontology_graph: Graph,
    competency_questions: List[str],
) -> ValidationResult:
    """Check that every class in the ontology has a skos:definition or rdfs:comment.

    This is Module 1's lightweight completeness check: it does not evaluate
    whether the ontology can answer competency questions (that requires a
    running graph), but it enforces that every class has a human-readable
    justification — the rationale.md requirement operationalised in code.

    Component class: DETERMINISTIC.
    """
    from rdflib.namespace import OWL, RDFS, SKOS, RDF

    violations: List[str] = []
    classes = set(ontology_graph.subjects(RDF.type, OWL.Class))
    for cls in classes:
        has_comment = (cls, RDFS.comment, None) in ontology_graph
        has_definition = (cls, SKOS.definition, None) in ontology_graph
        if not (has_comment or has_definition):
            violations.append(
                f"<{cls}> is missing rdfs:comment or skos:definition. "
                f"Every class must have a one-sentence justification keyed to "
                f"a competency question."
            )

    conforms = len(violations) == 0
    summary = _build_summary(conforms, violations)
    return ValidationResult(conforms=conforms, violations=violations, summary=summary)
