"""Filter-promotion state — ``FieldBindings`` (``core/translation/field_binding.py``).

Unit tier: the state object consulted by the query pipeline, the selection
walk, and the FilterContext strategies — constructed directly, without
registry fixtures (an empty registry and inline shapes suffice).

Order: bound-ness → selected/isolated gating → promoted-bound invariant.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef, Variable

from fastshaql.core.ir.node_shape import NodeShapeIR
from fastshaql.core.registry import ShapeRegistry
from fastshaql.core.translation.field_binding import FieldBindings
from fastshaql.core.translation.scope import TranslationScope
from fastshaql.core.translation.variables import VariableAllocator, VariableMap
from support.builders import scalar_property


def _empty_scope() -> TranslationScope:
    """A root scope over an empty registry — no fixtures needed."""
    allocator = VariableAllocator()
    return TranslationScope(
        subject=allocator.allocate("iri"),
        allocator=allocator,
        registry=ShapeRegistry(()),
    )


def _shape_with_optional_name() -> NodeShapeIR:
    return NodeShapeIR(
        iri=URIRef("http://example.org/PersonShape"),
        graphql_type_name="Person",
        property_shapes={"name": scalar_property("name", min_count=0, max_count=1)},
    )


# --- Bound-ness ---


def test_required_field_bound_without_promotion() -> None:
    prop = scalar_property("name", min_count=1, max_count=1)
    assert FieldBindings().field_is_bound(prop, "name") is True


def test_promotion_binds_optional_field() -> None:
    prop = scalar_property("name", min_count=0, max_count=1)
    bindings = FieldBindings(promoted=frozenset({"name"}))
    assert bindings.field_is_bound(prop, "name") is True


def test_optional_field_unbound_without_promotion() -> None:
    prop = scalar_property("name", min_count=0, max_count=1)
    assert FieldBindings().field_is_bound(prop, "name") is False


# --- Selected/isolated gating ---


def test_note_selected_gates_reemit_only_when_isolated() -> None:
    bindings = FieldBindings(isolated=True)
    assert bindings.reemit_bind("name") is False
    bindings.note_selected("name")
    assert bindings.reemit_bind("name") is True


def test_selected_field_not_reemitted_when_flat() -> None:
    bindings = FieldBindings(isolated=False)
    bindings.note_selected("name")
    assert bindings.reemit_bind("name") is False


def test_bind_promoted_fields_skips_selected_field() -> None:
    """A promoted field the selection walk bound needs no re-emission."""
    bindings = FieldBindings(promoted=frozenset({"name"}))
    bindings.note_selected("name")
    assert (
        bindings.bind_promoted_fields(_shape_with_optional_name(), _empty_scope()) == []
    )


def test_bind_promoted_fields_emits_in_name_order() -> None:
    """Promoted-field emission is sorted by field name — deterministic
    pattern order whatever the set's iteration order (the SPARQL sequence
    is observable)."""
    shape = NodeShapeIR(
        iri=URIRef("http://example.org/PersonShape"),
        graphql_type_name="Person",
        property_shapes={
            "name": scalar_property("name", min_count=0, max_count=1),
            "age": scalar_property("age", min_count=0, max_count=1),
        },
    )
    bindings = FieldBindings(promoted=frozenset({"name", "age"}))
    rendered = "\n".join(
        pattern.render(0)
        for pattern in bindings.bind_promoted_fields(shape, _empty_scope())
    )
    assert rendered.index("<http://example.org/age>") < rendered.index(
        "<http://example.org/name>"
    )


# --- Promoted-bound invariant ---


def test_assert_promoted_bound_accepts_field_bound_by_walk() -> None:
    scope = _empty_scope()
    scope.fields["name"] = Variable("name")
    bindings = FieldBindings(promoted=frozenset({"name"}))
    bindings.note_selected("name")
    bindings.assert_promoted_bound(scope)  # no raise


def test_assert_promoted_bound_accepts_relationship_binding() -> None:
    scope = _empty_scope()
    join_var = Variable("employer_iri")
    scope.relationships["employer"] = (
        join_var,
        VariableMap(subject_var=join_var, fields={}, relationships={}),
    )
    bindings = FieldBindings(promoted=frozenset({"employer"}))
    bindings.assert_promoted_bound(scope)  # no raise


def test_assert_promoted_bound_rejects_never_bound_field() -> None:
    scope = _empty_scope()
    bindings = FieldBindings(promoted=frozenset({"name"}))
    with pytest.raises(AssertionError, match="name"):
        bindings.assert_promoted_bound(scope)
