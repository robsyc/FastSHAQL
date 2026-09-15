"""Relationship join emission for selection walk and filter EXISTS
(ADR-0015 — the join chokepoint dispatching on value source).

One chokepoint for both value sources: asserted relationships emit the path
triple; derived relationships splice the node expression binding the child
subject (ADR-0015). Callers never re-spread the source decision. Derived
emissions followed by a typing or membership guard are contained in a
projecting sub-SELECT — the guard must never see an unbound child.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rdflib import URIRef, Variable

from fastshaql.core.ir import ValueSource
from fastshaql.core.sparql import (
    GroupPattern,
    OptionalPattern,
    Pattern,
    TriplePattern,
    ValuesPattern,
    contain_row_keeping,
)

from .node_expr import translate_node_expr
from .paths import SHACL_INSTANCE_PATH, map_shacl_path_to_sparql_path

if TYPE_CHECKING:
    from fastshaql.core.ir import PropertyShapeIR

    from .variables import VariableAllocator


def relationship_join_patterns(
    parent_subject: Variable,
    child_subject: Variable,
    prop: PropertyShapeIR,
    *,
    allocator: VariableAllocator,
    emit_type_triple: bool = False,
) -> list[Pattern]:
    """Emit join pattern(s) from *parent_subject* to *child_subject* via *prop*.

    The link emission (:func:`relationship_link_patterns`; a derived
    emission replaces the path triple, ADR-0015) plus, when
    *emit_type_triple* is true, the child's typing paths via
    :func:`relationship_type_patterns`.
    """
    guarded = emit_type_triple and bool(prop.value_classes or prop.union_members)
    patterns = relationship_link_patterns(
        parent_subject, child_subject, prop, guarded=guarded
    )
    if emit_type_triple:
        patterns.extend(
            relationship_type_patterns(child_subject, prop, allocator=allocator)
        )
    return patterns


def relationship_link_patterns(
    parent_subject: Variable,
    child_subject: Variable,
    prop: PropertyShapeIR,
    *,
    guarded: bool,
) -> list[Pattern]:
    """The link emission alone (ADR-0015): the asserted path triple, or the
    derived node expression binding *child_subject* — contained when a
    typing or membership guard follows and the binding carries classes
    (*guarded*): the guard re-binds an unbound child freely, fabricating
    children (ADR-0026 hazard); field-absent semantics survive via the
    caller's OPTIONAL wrap.
    """
    if prop.source is not ValueSource.DERIVED:
        return [
            TriplePattern(
                subject=parent_subject,
                predicate=map_shacl_path_to_sparql_path(prop.path),
                object=child_subject,
            )
        ]
    if prop.values_expr is None:
        raise ValueError(
            f"derived property {prop.graphql_field_name!r} lacks its sh:values node expression"
        )  # pragma: no cover — source is DERIVED iff values_expr set
    patterns = translate_node_expr(
        prop.values_expr,
        focus_term=parent_subject,
        value_var=child_subject,
    )
    if guarded:
        patterns = contain_row_keeping(
            patterns, (parent_subject, child_subject), child_subject
        )
    return patterns


def relationship_type_patterns(
    subject: Variable,
    prop: PropertyShapeIR,
    *,
    allocator: VariableAllocator | None = None,
) -> list[Pattern]:
    """Emit the child's SHACL-instance typing for a relationship subject
    (ADR-0025): one conjunctive path per declared class — empty when the
    binding carries none. The binding-union row (``sh:class`` list beside
    ``sh:node``) swaps the conjunction for one membership guard; its
    variable is name-derived and unprojected — a single target, nothing
    to stamp. Reserved in *allocator* when given; the EXISTS lane omits
    it (its ``_rf_`` namespacing owns uniqueness there, ADR-0009)."""
    if prop.union_members:
        guard_var = Variable(f"{subject}__member")
        if allocator is not None:
            allocator.reserve(str(guard_var))
        return membership_guard(subject, guard_var, prop)
    return [
        TriplePattern(subject, SHACL_INSTANCE_PATH, class_iri)
        for class_iri in prop.value_classes
    ]


def membership_guard(
    subject: Variable,
    guard_var: Variable,
    prop: PropertyShapeIR,
) -> list[Pattern]:
    """The membership guard (ADR-0025 row 5, ADR-0026): the ``VALUES``
    domain restriction over the declared member classes plus the
    SHACL-instance path binding *guard_var*. Non-member children drop;
    overlap children bind one row per matching member, merged by the
    converter's group-by-child with member-order priority."""
    return [
        ValuesPattern(
            guard_var,
            tuple(cast(URIRef, member.class_iri) for member in prop.union_members),
        ),
        TriplePattern(subject, SHACL_INSTANCE_PATH, guard_var),
    ]


def member_lane_patterns(
    child_subject: Variable,
    member_class: URIRef,
    branch: list[Pattern],
) -> Pattern:
    """One member's OPTIONAL lane (ADR-0026): the SHACL-instance type guard
    plus the member fragment's branch field patterns."""
    guard = TriplePattern(child_subject, SHACL_INSTANCE_PATH, member_class)
    return OptionalPattern(GroupPattern((guard, *branch)))
