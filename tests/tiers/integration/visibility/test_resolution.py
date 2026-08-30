"""Visibility edge cases via programmatic graphs — ``core/registry.py``.

Integration tier: conflicts and warnings that must not pollute the shared
declarative fixture, built as inline turtle and parsed through ``parse_shapes``.

Order: private override (public + protected) → schema errors (multiple, blank-node) → closed-world target → synthetic exemption → untargeted publicShape → publicNamespace warning.
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser import parse_shapes
from fastshaql.core.registry import Visibility, VisibilityError

if TYPE_CHECKING:
    from rdflib import Graph

_PREFIXES = textwrap.dedent(
    """
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix ex: <http://example.org/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix graphql: <http://datashapes.org/graphql#> .
    """
)

_PERSON_SHAPE = textwrap.dedent(
    """
    ex:PersonShape a sh:NodeShape ;
        sh:codeIdentifier "Person" ;
        sh:targetClass ex:Person ;
        sh:property [
            sh:path ex:name ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1
        ] .
    """
)


_PRIVATE_RELATIONSHIP_SHAPES = (
    _PREFIXES
    + textwrap.dedent(
        """
    ex:ApiSchema a graphql:Schema ;
        graphql:publicShape ex:PersonShape, ex:SecretShape ;
        graphql:privateShape ex:SecretShape .

    ex:SecretShape a sh:NodeShape ;
        sh:codeIdentifier "Secret" ;
        sh:targetClass ex:Secret ;
        sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1
        ] .
    """
    )
    + _PERSON_SHAPE
    + textwrap.dedent(
        """
    ex:PersonShape sh:property [
        sh:path ex:secret ;
        sh:node ex:SecretShape ;
        sh:minCount 0 ;
        sh:maxCount 1
    ] .
    """
    )
)

_PRIVATE_OVERRIDE_PROTECTED = _PREFIXES + textwrap.dedent(
    """
    ex:ApiSchema a graphql:Schema ;
        graphql:protectedShape ex:SecretShape ;
        graphql:privateShape ex:SecretShape .

    ex:SecretShape a sh:NodeShape ;
        sh:codeIdentifier "Secret" ;
        sh:targetClass ex:Secret ;
        sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1
        ] .
    """
)

_MULTIPLE_SCHEMAS = (
    _PREFIXES
    + textwrap.dedent(
        """
    ex:SchemaOne a graphql:Schema ; graphql:publicShape ex:PersonShape .
    ex:SchemaTwo a graphql:Schema ; graphql:publicShape ex:PersonShape .
    """
    )
    + _PERSON_SHAPE
)

_BLANK_NODE_SCHEMA = (
    _PREFIXES
    + textwrap.dedent(
        """
    [ a graphql:Schema ; graphql:publicShape ex:PersonShape ] .
    """
    )
    + _PERSON_SHAPE
)

_CLOSED_WORLD_UNDECLARED_TARGET = (
    _PREFIXES
    + textwrap.dedent(
        """
    ex:ApiSchema a graphql:Schema ; graphql:publicShape ex:PersonShape .

    ex:OrphanShape a sh:NodeShape ;
        sh:codeIdentifier "Orphan" ;
        sh:targetClass ex:Orphan ;
        sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1
        ] .
    """
    )
    + _PERSON_SHAPE
    + textwrap.dedent(
        """
    ex:PersonShape sh:property [
        sh:path ex:orphan ;
        sh:node ex:OrphanShape ;
        sh:minCount 0 ;
        sh:maxCount 1
    ] .
    """
    )
)

_SYNTHETIC_TARGET = (
    _PREFIXES
    + textwrap.dedent(
        """
    ex:ApiSchema a graphql:Schema ; graphql:publicShape ex:PersonShape .
    """
    )
    + _PERSON_SHAPE
    + textwrap.dedent(
        """
    ex:PersonShape sh:property [
        sh:path ex:department ;
        sh:class ex:Untargeted ;
        sh:minCount 0 ;
        sh:maxCount 1
    ] .
    """
    )
)

_UNTARGETED_PUBLIC_SHAPE = _PREFIXES + textwrap.dedent(
    """
    ex:ApiSchema a graphql:Schema ; graphql:publicShape ex:OrphanShape .

    ex:OrphanShape a sh:NodeShape ;
        sh:codeIdentifier "Orphan" ;
        sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1
        ] .
    """
)

_PUBLIC_NAMESPACE = (
    _PREFIXES
    + textwrap.dedent(
        """
    ex:ApiSchema a graphql:Schema ;
        graphql:publicShape ex:PersonShape ;
        graphql:publicNamespace ex:PublicNs .
    """
    )
    + _PERSON_SHAPE
)


def _graph(turtle: str) -> Graph:
    return load_shapes(turtle)


def test_private_shape_relationship_target_raises() -> None:
    """A public relationship to a ``privateShape`` fails closed-world at parse time."""
    with pytest.raises(VisibilityError, match=r"Person\.secret"):
        parse_shapes(_graph(_PRIVATE_RELATIONSHIP_SHAPES))


def test_private_shape_overrides_protected() -> None:
    """``privateShape`` wins over ``protectedShape`` (ADR-0008: excluded wins)."""
    registry = parse_shapes(_graph(_PRIVATE_OVERRIDE_PROTECTED))
    assert (
        registry.visibility_of(registry.by_type_name["Secret"]) is Visibility.EXCLUDED
    )


def test_multiple_schemas_raise() -> None:
    with pytest.raises(VisibilityError, match="multiple graphql:Schema"):
        parse_shapes(_graph(_MULTIPLE_SCHEMAS))


def test_blank_node_schema_raises() -> None:
    """A blank-node ``graphql:Schema`` is rejected — single-schema lookup needs an IRI."""
    with pytest.raises(VisibilityError, match="graphql:Schema resource must be an IRI"):
        parse_shapes(_graph(_BLANK_NODE_SCHEMA))


def test_closed_world_relationship_targets_excluded() -> None:
    with pytest.raises(
        VisibilityError,
        match=r"Person\.orphan.*OrphanShape",
    ):
        parse_shapes(_graph(_CLOSED_WORLD_UNDECLARED_TARGET))


def test_synthetic_target_exempt() -> None:
    registry = parse_shapes(_graph(_SYNTHETIC_TARGET))

    assert (
        registry.visibility_of(registry.by_type_name["Untargeted"])
        is Visibility.PROTECTED
    )


def test_public_shape_without_target_class_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("WARNING", logger="fastshaql.core.registry"):
        registry = parse_shapes(_graph(_UNTARGETED_PUBLIC_SHAPE))

    orphan = registry.by_type_name["Orphan"]
    assert registry.visibility_of(orphan) is Visibility.PROTECTED
    assert any(
        "publicShape" in record.message and "supported target" in record.message
        for record in caplog.records
    )


_DERIVED_TARGET_PUBLIC_SHAPE = _PREFIXES + textwrap.dedent(
    """
    @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .

    ex:ApiSchema a graphql:Schema ; graphql:publicShape ex:VariantShape .

    ex:VariantShape a sh:NodeShape ;
        sh:codeIdentifier "Variant" ;
        sh:targetNode [ shnex:instancesOf ex:Variant ] ;
        sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1
        ] .
    """
)


def test_public_shape_with_derived_target_is_rootable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A PUBLIC shape with ``sh:targetNode`` publishes — no demotion warning."""
    with caplog.at_level("WARNING", logger="fastshaql.core.registry"):
        registry = parse_shapes(_graph(_DERIVED_TARGET_PUBLIC_SHAPE))

    variant = registry.by_type_name["Variant"]
    assert registry.visibility_of(variant) is Visibility.PUBLIC
    assert variant in registry.public_root_shapes()
    assert not any("supported target" in record.message for record in caplog.records)


_PUBLIC_CLASS_IMPLICIT_TARGET = _PREFIXES + textwrap.dedent(
    """
    @prefix sh: <http://www.w3.org/ns/shacl#> .

    ex:ApiSchema a graphql:Schema ; graphql:publicClass ex:Change .

    ex:Change a sh:ShapeClass ;
        sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1
        ] .
    """
)


def test_public_class_declaration_publishes_implicit_class_shape() -> None:
    """``graphql:publicClass ex:Change`` publishes the ``sh:ShapeClass`` shape
    indexed under its own IRI (Core §3.1.3.3) — the shape is the class."""
    registry = parse_shapes(_graph(_PUBLIC_CLASS_IMPLICIT_TARGET))
    change = registry.by_type_name["Change"]
    assert registry.visibility_of(change) is Visibility.PUBLIC
    assert change in registry.public_root_shapes()


def test_public_namespace_warned_and_ignored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("WARNING", logger="fastshaql.core.registry"):
        registry = parse_shapes(_graph(_PUBLIC_NAMESPACE))

    assert registry.visibility_of(registry.by_type_name["Person"]) is Visibility.PUBLIC
    assert any(
        "graphql:publicNamespace not supported" in record.message
        for record in caplog.records
    )
