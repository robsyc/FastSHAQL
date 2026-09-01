"""Bind classification and promotion — ``core/translation/field_binding.py``.

Unit tier: ``field_is_bound`` cardinality/promotion rules, and
``bind_promoted_fields`` emitting patterns for filter-promoted scalars and derived fields.

Order: bind classification → promoted-field binding.
"""

from __future__ import annotations

from rdflib import RDF, URIRef, Variable

from fastshaql.core.ir.node_expr import SelectNodeExpr
from fastshaql.core.sparql import (
    PredicatePath,
    RawGraphPattern,
    TriplePattern,
)
from fastshaql.core.translation.field_binding import (
    bind_promoted_fields,
    field_is_bound,
)
from fastshaql.core.translation.joins import relationship_join_patterns
from fastshaql.core.translation.variables import VariableMap
from support.builders import (
    derived_property,
    relationship_property,
    scalar_property,
    shape_with,
)
from support.translation import translation_scope

EX = URIRef("http://example.org/")

# --- Bind classification ---


def test_field_is_bound_when_required() -> None:
    prop = scalar_property("name", min_count=1, max_count=1)
    assert field_is_bound(prop, "name", frozenset()) is True


def test_field_is_bound_when_promoted() -> None:
    prop = scalar_property("name", min_count=0, max_count=1)
    assert field_is_bound(prop, "name", frozenset({"name"})) is True


def test_field_is_bound_optional_unpromoted() -> None:
    prop = scalar_property("name", min_count=0, max_count=1)
    assert field_is_bound(prop, "name", frozenset()) is False


# --- Promoted-field binding ---


def test_bind_promoted_fields_emits_unselected_filter_field(
    relationship_registry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    patterns = bind_promoted_fields(
        person, scope, promoted=frozenset({"name"}), selected=frozenset()
    )
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
    patterns = bind_promoted_fields(
        person, scope, promoted=frozenset({"label"}), selected=frozenset()
    )
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
    patterns = relationship_join_patterns(Variable("s"), Variable("o"), prop)
    assert patterns == [
        TriplePattern(
            subject=Variable("s"),
            predicate=PredicatePath(EX + "employer"),
            object=Variable("o"),
        )
    ]


def test_relationship_join_patterns_with_type_triple_when_requested() -> None:
    prop = relationship_property(
        "employer",
        EX + "CompanyShape",
        min_count=0,
        max_count=1,
        value_class=EX + "Company",
    )
    patterns = relationship_join_patterns(
        Variable("s"), Variable("o"), prop, emit_type_triple=True
    )
    assert patterns[1] == TriplePattern(
        subject=Variable("o"),
        predicate=PredicatePath(RDF.type),
        object=EX + "Company",
    )


def test_promoted_relationship_registers_fresh_empty_child_var_map(
    relationship_registry,
) -> None:
    """A promoted (unselected) relationship binds its join variable and
    registers an empty child variable map anchored on that variable."""
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    patterns = bind_promoted_fields(
        person, scope, promoted=frozenset({"employer"}), selected=frozenset()
    )
    child_var = patterns[0].object
    assert scope.relationships["employer"] == (
        child_var,
        VariableMap(subject_var=child_var, fields={}, relationships={}),
    )
