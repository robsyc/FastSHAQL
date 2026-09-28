"""Visibility resolution — ``core/registry.py``.

Unit tier: ``VisibilityMap`` totality, no-schema backward compatibility, and
resolver classification against the shared visibility fixture.

Order: no-schema default → VisibilityMap totality → resolver classification →
schema description.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef

from fastshaql.core.parser import parse_shapes
from fastshaql.core.registry import ShapeRegistry, Visibility, VisibilityMap

SCHEMA_DESCRIPTION_SHAPES = """
@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix ex:      <http://example.org/> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix graphql: <http://datashapes.org/graphql#> .

ex:Api a graphql:Schema ;
    rdfs:comment "The demo API view." ;
    graphql:publicShape ex:ThingShape .

ex:ThingShape a sh:NodeShape ;
    sh:codeIdentifier "Thing" ;
    sh:targetClass ex:Thing ;
    sh:property [
        sh:path ex:name ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        sh:maxCount 1
    ] .
"""


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


# --- Schema description ---


def test_schema_description_served_from_rdfs_comment() -> None:
    """The ``graphql:Schema`` resource's ``rdfs:comment`` lands on the registry."""
    graph = Graph().parse(data=SCHEMA_DESCRIPTION_SHAPES, format="turtle")
    registry = parse_shapes(graph)
    assert registry.schema_description == "The demo API view."


def test_schema_description_absent_without_schema(minimal_shapes_graph) -> None:
    registry = parse_shapes(minimal_shapes_graph)
    assert registry.schema_description is None
