"""Bind classification and promotion — ``core/translation/field_binding.py``.

Unit tier: ``field_is_bound`` cardinality/promotion rules, and
``bind_promoted_fields`` emitting patterns for filter-promoted scalars and derived fields.

Order: bind classification → promoted-field binding.
"""

from __future__ import annotations

from fastshaql.core.ir.node_expr import SelectNodeExpr
from fastshaql.core.sparql import RawGraphPattern, TriplePattern
from fastshaql.core.translation.field_binding import (
    bind_promoted_fields,
    field_is_bound,
)
from support.builders import derived_property, scalar_property, shape_with
from support.translation import translation_scope

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
