"""Bind primitives and promotion emission — ``core/translation/field_binding.py``.

Unit tier: ``bind_scalar_field``/relationship join emission and
``FieldBindings.bind_promoted_fields`` registering promoted fields on the
scope (see ``filters/test_field_bindings.py`` for the state object itself).

Order: promoted-field binding → relationship join emission and registration.
"""

from __future__ import annotations

import dataclasses
from typing import cast

from rdflib import RDF, RDFS, URIRef, Variable

from fastshaql.core.ir import UnionMember
from fastshaql.core.ir.node_expr import SelectNodeExpr
from fastshaql.core.sparql import (
    FilterPattern,
    FunctionCall,
    PredicatePath,
    RawGraphPattern,
    SelectQuery,
    SequencePath,
    TriplePattern,
    ValuesPattern,
    ZeroOrMorePath,
)
from fastshaql.core.translation.field_binding import FieldBindings
from fastshaql.core.translation.joins import (
    relationship_join_patterns,
    relationship_type_patterns,
)
from fastshaql.core.translation.variables import (
    MemberBinding,
    RelationshipBinding,
    VariableAllocator,
    VariableMap,
)
from support.builders import (
    derived_property,
    relationship_property,
    shape_with,
)
from support.translation import translation_scope

EX = URIRef("http://example.org/")

# --- Promoted-field binding ---


def test_bind_promoted_fields_emits_unselected_filter_field(
    relationship_registry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    bindings = FieldBindings(promoted=frozenset({"name"}))
    patterns = bindings.bind_promoted_fields(person, scope)
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)
    assert "name" in scope.fields


def test_bind_promoted_fields_emits_unselected_derived_field(
    relationship_registry,
) -> None:
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        label=derived_property(
            "label",
            values_expr=SelectNodeExpr(
                body="$this <http://example.org/name> ?v", projection_var="v"
            ),
            min_count=1,
            max_count=1,
        ),
    )
    scope = translation_scope(relationship_registry)
    bindings = FieldBindings(promoted=frozenset({"label"}))
    patterns = bindings.bind_promoted_fields(person, scope)
    assert any(isinstance(p, RawGraphPattern) for p in patterns)
    assert not any(isinstance(p, TriplePattern) for p in patterns)
    assert "label" in scope.fields


# --- relationship join emission and promotion registration (hardening) ---


def test_relationship_join_patterns_omit_type_triple_by_default() -> None:
    """The join chokepoint's default is the plain path triple — the child
    ``rdf:type`` constraint is opt-in per call site."""
    prop = relationship_property(
        "employer",
        EX + "CompanyShape",
        min_count=0,
        max_count=1,
        value_class=EX + "Company",
    )
    patterns = relationship_join_patterns(
        Variable("s"), Variable("o"), prop, allocator=VariableAllocator()
    )
    assert patterns == [
        TriplePattern(
            subject=Variable("s"),
            predicate=PredicatePath(EX + "employer"),
            object=Variable("o"),
        )
    ]


def test_relationship_join_patterns_with_type_triple_when_requested() -> None:
    """The opt-in typing emission is the SHACL-instance path
    ``rdf:type/rdfs:subClassOf*`` (ADR-0025), not a plain type triple."""
    prop = relationship_property(
        "employer",
        EX + "CompanyShape",
        min_count=0,
        max_count=1,
        value_class=EX + "Company",
    )
    patterns = relationship_join_patterns(
        Variable("s"),
        Variable("o"),
        prop,
        allocator=VariableAllocator(),
        emit_type_triple=True,
    )
    assert patterns[1] == TriplePattern(
        subject=Variable("o"),
        predicate=SequencePath(
            (PredicatePath(RDF.type), ZeroOrMorePath(PredicatePath(RDFS.subClassOf)))
        ),
        object=EX + "Company",
    )


def test_relationship_join_patterns_derived_without_typing_stay_uncontained() -> None:
    """A derived link no guard follows (class-less target — the ADR-0025
    row-1 exemption) emits the bare node expression: containment exists
    only for emissions a typing or membership guard would re-bind
    (ADR-0026)."""
    prop = derived_property(
        "note",
        values_expr=SelectNodeExpr(
            body="$this <http://example.org/note> ?v", projection_var="v"
        ),
        min_count=0,
        max_count=1,
    )
    patterns = relationship_join_patterns(
        Variable("s"), Variable("o"), prop, allocator=VariableAllocator()
    )
    assert any(isinstance(p, RawGraphPattern) for p in patterns)
    assert not any(isinstance(p, SelectQuery) for p in patterns)


def test_relationship_join_patterns_classless_derived_selection_stays_uncontained() -> (
    None
):
    """The selection entry point (``emit_type_triple=True``) still skips
    containment for a class-less derived link — no typing guard follows to
    re-bind the child, so the wrap would be pure noise
    (ADR-0025 row 1 and ADR-0026)."""
    prop = derived_property(
        "note",
        values_expr=SelectNodeExpr(
            body="$this <http://example.org/note> ?v", projection_var="v"
        ),
        min_count=0,
        max_count=1,
    )
    patterns = relationship_join_patterns(
        Variable("s"),
        Variable("o"),
        prop,
        allocator=VariableAllocator(),
        emit_type_triple=True,
    )
    assert any(isinstance(p, RawGraphPattern) for p in patterns)
    assert not any(isinstance(p, SelectQuery) for p in patterns)


def test_relationship_type_patterns_binding_union_without_allocator() -> None:
    """The EXISTS lane calls without an allocator — its ``_rf_``
    namespacing owns uniqueness there, so the row-5 guard mints
    unreserved (ADR-0009; reservation is the selection walk's concern)."""
    prop = dataclasses.replace(
        relationship_property("asset", EX + "AssetShape", min_count=0, max_count=None),
        union_members=(
            UnionMember(shape_iri=EX + "AssetShape", class_iri=EX + "Machine"),
        ),
    )
    patterns = relationship_type_patterns(Variable("_rf_asset"), prop)
    assert isinstance(patterns[0], ValuesPattern)
    guard = TriplePattern(
        subject=Variable("_rf_asset"),
        predicate=SequencePath(
            (PredicatePath(RDF.type), ZeroOrMorePath(PredicatePath(RDFS.subClassOf)))
        ),
        object=Variable("_rf_asset__member"),
    )
    assert patterns[1] == guard


def test_promoted_relationship_registers_fresh_empty_child_var_map(
    relationship_registry,
) -> None:
    """A promoted (unselected) relationship binds its join variable and
    registers an empty child variable map anchored on that variable."""
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    bindings = FieldBindings(promoted=frozenset({"employer"}))
    patterns = bindings.bind_promoted_fields(person, scope)
    first = patterns[0]
    assert isinstance(first, TriplePattern)
    child_var = cast("Variable", first.object)
    assert scope.relationships["employer"] == RelationshipBinding(
        subject_var=child_var,
        members=(
            MemberBinding(
                None, VariableMap(subject_var=child_var, fields={}, relationships={})
            ),
        ),
    )


def test_promoted_derived_relationship_link_is_contained(
    relationship_registry,
) -> None:
    """A promoted derived relationship emits the contained link emission —
    the filter's EXISTS typing guard must never re-bind an unbound child
    (ADR-0026)."""
    person = relationship_registry.by_type_name["Person"]
    friend = dataclasses.replace(
        relationship_property(
            "friend",
            person.iri,
            min_count=0,
            max_count=None,
            value_class=person.target_class,
        ),
        values_expr=SelectNodeExpr(
            body="$this <http://example.org/knows> ?v", projection_var="v"
        ),
    )
    scope = translation_scope(relationship_registry)
    bindings = FieldBindings(promoted=frozenset({"friend"}))
    patterns = bindings.bind_promoted_fields(shape_with(person, friend=friend), scope)
    child_var = scope.relationships["friend"].subject_var
    assert len(patterns) == 1
    contained = patterns[0]
    assert isinstance(contained, SelectQuery)
    assert contained.projection == (scope.subject, child_var)
    assert contained.as_subquery is True
    bound_filters = [
        child
        for child in contained.where.children
        if isinstance(child, FilterPattern)
        and isinstance(child.expression, FunctionCall)
        and child.expression.name == "BOUND"
    ]
    assert len(bound_filters) == 1
