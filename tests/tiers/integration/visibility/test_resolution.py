"""Visibility edge cases via programmatic graphs — ``core/registry.py``.

Integration tier: conflicts and warnings that must not pollute the shared
declarative fixture, built as inline turtle and parsed through ``parse_shapes``.

Order: private override (public + protected) → schema errors (multiple, blank-node) → closed-world target → synthetic exemption → untargeted publicShape → publicNamespace warning → declaration-read scoping.
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


# --- Declaration-read scoping (ADR-0008: declarations live on the schema) ---


def _minimal_shape(name: str, class_local: str) -> str:
    return textwrap.dedent(
        f"""
        ex:{name}Shape a sh:NodeShape ;
            sh:codeIdentifier "{name}" ;
            sh:targetClass ex:{class_local} ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .
        """
    )


_STRAY_DECLARATIONS = (
    _PREFIXES
    + textwrap.dedent(
        """
        ex:ApiSchema a graphql:Schema ;
            graphql:publicShape ex:PersonShape ;
            graphql:protectedShape ex:AuditLogShape .

        # Declarations from a non-schema resource are inert — only the
        # graphql:Schema's own edges are read.
        ex:Stray
            graphql:publicShape ex:CatShape ;
            graphql:protectedShape ex:DogShape ;
            graphql:privateShape ex:PersonShape ;
            graphql:publicClass ex:Cat ;
            graphql:protectedClass ex:Dog .
        """
    )
    + _PERSON_SHAPE
    + _minimal_shape("AuditLog", "AuditLog")
    + _minimal_shape("Cat", "Cat")
    + _minimal_shape("Dog", "Dog")
)


def test_declarations_are_read_from_the_schema_only() -> None:
    """Visibility declarations on any subject other than the schema are
    ignored; precedence (private > public > protected) holds for the
    schema's own declarations."""
    registry = parse_shapes(_graph(_STRAY_DECLARATIONS))

    assert registry.visibility_of(registry.by_type_name["Person"]) is Visibility.PUBLIC
    assert registry.visibility_of(registry.by_type_name["AuditLog"]) is (
        Visibility.PROTECTED
    )
    assert registry.visibility_of(registry.by_type_name["Cat"]) is Visibility.EXCLUDED
    assert registry.visibility_of(registry.by_type_name["Dog"]) is Visibility.EXCLUDED


_CLASS_CLOSURE_SCOPING = (
    _PREFIXES
    + textwrap.dedent(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ApiSchema a graphql:Schema ;
            graphql:publicClass ex:Animal ;
            graphql:protectedClass ex:Vehicle .

        ex:Car rdfs:subClassOf ex:Vehicle .
        """
    )
    + _minimal_shape("Animal", "Animal")
    + _minimal_shape("Car", "Car")
)


def test_class_declarations_publish_declared_class_and_protect_subclasses() -> None:
    """A ``publicClass``/``protectedClass`` declaration covers the declared
    class itself and its ``rdfs:subClassOf`` descendants — reading only
    those two predicates."""
    registry = parse_shapes(_graph(_CLASS_CLOSURE_SCOPING))

    assert registry.visibility_of(registry.by_type_name["Animal"]) is Visibility.PUBLIC
    assert registry.visibility_of(registry.by_type_name["Car"]) is (
        Visibility.PROTECTED
    )


_CLASS_CLOSURE_PREDICATE_DISCIPLINE = (
    _PREFIXES
    + textwrap.dedent(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ApiSchema a graphql:Schema ;
            graphql:publicClass ex:Animal .

        ex:Dog rdfs:subClassOf ex:Animal .
        ex:Car rdfs:subClassOf ex:Vehicle .
        ex:Cat ex:similarTo ex:Animal .
        """
    )
    + _minimal_shape("Dog", "Dog")
    + _minimal_shape("Cat", "Cat")
    + _minimal_shape("Car", "Car")
)


def test_class_closure_expands_only_subclass_edges() -> None:
    """Only ``rdfs:subClassOf`` grows a class closure: a non-subclass edge
    to the declared class excludes, and an unrelated ``subClassOf`` edge
    joins no foreign closure."""
    registry = parse_shapes(_graph(_CLASS_CLOSURE_PREDICATE_DISCIPLINE))

    assert registry.visibility_of(registry.by_type_name["Dog"]) is Visibility.PUBLIC
    assert registry.visibility_of(registry.by_type_name["Cat"]) is Visibility.EXCLUDED
    assert registry.visibility_of(registry.by_type_name["Car"]) is Visibility.EXCLUDED


_SCHEMA_HUNT_SCOPING = (
    _PREFIXES
    + textwrap.dedent(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ApiSchema a graphql:Schema ; graphql:publicShape ex:PersonShape .

        # A resource merely referencing the Schema class is not a second schema.
        ex:Note rdfs:seeAlso graphql:Schema .
        """
    )
    + _PERSON_SHAPE
)


def test_schema_hunt_reads_only_rdf_type_edges() -> None:
    """Schemas are resources typed ``graphql:Schema`` — a ``seeAlso`` link to
    the class does not multiply them."""
    registry = parse_shapes(_graph(_SCHEMA_HUNT_SCOPING))

    assert registry.visibility_of(registry.by_type_name["Person"]) is Visibility.PUBLIC


def test_public_namespace_warning_reads_only_schema_edges(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The publicNamespace warning fires on the schema's own edges only —
    neither a stray resource's declaration nor unrelated schema objects
    trigger it."""
    turtle = (
        _PREFIXES
        + textwrap.dedent(
            """
            ex:Stray graphql:publicNamespace ex:SomeNs .

            ex:ApiSchema a graphql:Schema ; graphql:publicShape ex:PersonShape .
            """
        )
        + _PERSON_SHAPE
    )
    with caplog.at_level("WARNING", logger="fastshaql.core.registry"):
        registry = parse_shapes(_graph(turtle))

    assert registry.visibility_of(registry.by_type_name["Person"]) is Visibility.PUBLIC
    assert not any("publicNamespace" in record.message for record in caplog.records)


_ALL_OBJECTS_POLLUTION = (
    _PREFIXES
    + textwrap.dedent(
        """
        # publicClass pointing at a shape IRI and privateShape pointing at a
        # class IRI: neither mis-declaration may leak the shape into the
        # protected sets via an unscoped object read.
        ex:ApiSchema a graphql:Schema ;
            graphql:publicClass ex:GhostShape ;
            graphql:privateShape ex:Widget .
        """
    )
    + _minimal_shape("Ghost", "Other")
    + _minimal_shape("Widget", "Widget")
)


def test_mis_scoped_class_and_shape_objects_stay_excluded() -> None:
    """A schema object that is a shape IRI (via ``publicClass``) or a class
    IRI (via ``privateShape``) reaches no visibility set it did not declare:
    both shapes stay excluded."""
    registry = parse_shapes(_graph(_ALL_OBJECTS_POLLUTION))

    assert registry.visibility_of(registry.by_type_name["Ghost"]) is Visibility.EXCLUDED
    assert registry.visibility_of(registry.by_type_name["Widget"]) is (
        Visibility.EXCLUDED
    )
