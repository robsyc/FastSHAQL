"""Visibility resolution — ``core/registry.py``.

Unit tier: ``VisibilityMap`` totality, no-schema backward compatibility, and
resolver classification against the shared visibility fixture.

Order: no-schema default → VisibilityMap totality → resolver classification.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef

from fastshaql.core.parser import parse_shapes
from fastshaql.core.registry import ShapeRegistry, Visibility, VisibilityMap


def test_parse_shapes_without_schema_all_shapes_public(
    minimal_shapes_graph,
) -> None:
    registry = parse_shapes(minimal_shapes_graph)
    for shape in registry.shapes:
        assert registry.visibility_of(shape) is Visibility.PUBLIC


def test_visibility_map_of_unknown_iri_raises_key_error() -> None:
    """``VisibilityMap`` is total over its registry; an unknown IRI is a caller bug."""
    visibility = VisibilityMap.all_public([URIRef("http://example.org/Known")])
    with pytest.raises(KeyError, match="Unknown"):
        visibility.of(URIRef("http://example.org/Unknown"))


def test_resolve_visibility_protected_shape(visibility_registry: ShapeRegistry) -> None:
    assert (
        visibility_registry.visibility_of(visibility_registry.by_type_name["AuditLog"])
        is Visibility.PROTECTED
    )


def test_resolve_visibility_protected_class_closure(
    visibility_registry: ShapeRegistry,
) -> None:
    assert (
        visibility_registry.visibility_of(visibility_registry.by_type_name["Car"])
        is Visibility.PROTECTED
    )


def test_resolve_visibility_public_class_closure(
    visibility_registry: ShapeRegistry,
) -> None:
    assert (
        visibility_registry.visibility_of(visibility_registry.by_type_name["Dog"])
        is Visibility.PUBLIC
    )
    assert (
        visibility_registry.visibility_of(visibility_registry.by_type_name["Cat"])
        is Visibility.EXCLUDED
    )


def test_resolve_visibility_private_shape_overrides_public(
    visibility_registry: ShapeRegistry,
) -> None:
    assert (
        visibility_registry.visibility_of(visibility_registry.by_type_name["Secret"])
        is Visibility.EXCLUDED
    )


def test_resolve_visibility_public_shapes(visibility_registry: ShapeRegistry) -> None:
    assert (
        visibility_registry.visibility_of(visibility_registry.by_type_name["Person"])
        is Visibility.PUBLIC
    )
    assert (
        visibility_registry.visibility_of(visibility_registry.by_type_name["Address"])
        is Visibility.PUBLIC
    )
