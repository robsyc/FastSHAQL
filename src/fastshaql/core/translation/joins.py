"""Relationship join emission for selection walk and filter EXISTS
(ADR-0015 — the join chokepoint dispatching on value source).

One chokepoint for both value sources: asserted relationships emit the path
triple; derived relationships splice the node expression binding the child
subject (ADR-0015). Callers never re-spread the source decision.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.ir import ValueSource
from fastshaql.core.sparql import Pattern, TriplePattern

from .node_expr import translate_node_expr
from .paths import SHACL_INSTANCE_PATH, map_shacl_path_to_sparql_path

if TYPE_CHECKING:
    from rdflib import Variable

    from fastshaql.core.ir import PropertyShapeIR


def relationship_join_patterns(
    parent_subject: Variable,
    child_subject: Variable,
    prop: PropertyShapeIR,
    *,
    emit_type_triple: bool = False,
) -> list[Pattern]:
    """Emit join pattern(s) from *parent_subject* to *child_subject* via *prop*.

    Asserted: the path triple. Derived: the node expression's patterns with
    *child_subject* as the value variable (replace-not-union — asserted path
    triples are dropped, ADR-0015).

    When *emit_type_triple* is true and the property carries binding
    classes, also emits their SHACL-instance typing paths via
    :func:`relationship_type_patterns`.
    """
    if prop.source is ValueSource.DERIVED:
        if prop.values_expr is None:
            raise ValueError(
                f"derived property {prop.graphql_field_name!r} lacks its sh:values node expression"
            )  # pragma: no cover — source is DERIVED iff values_expr set
        patterns = translate_node_expr(
            prop.values_expr,
            focus_term=parent_subject,
            value_var=child_subject,
        )
    else:
        patterns: list[Pattern] = [
            TriplePattern(
                subject=parent_subject,
                predicate=map_shacl_path_to_sparql_path(prop.path),
                object=child_subject,
            )
        ]
    if emit_type_triple:
        patterns.extend(relationship_type_patterns(child_subject, prop))
    return patterns


def relationship_type_patterns(
    subject: Variable,
    prop: PropertyShapeIR,
) -> list[Pattern]:
    """Emit the child's SHACL-instance typing paths for a relationship
    subject (ADR-0025): one conjunctive path per declared class — empty
    when the binding carries none."""
    return [
        TriplePattern(subject, SHACL_INSTANCE_PATH, class_iri)
        for class_iri in prop.value_classes
    ]
