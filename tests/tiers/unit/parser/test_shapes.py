"""SHACL shapes graph → Shape IR — ``core/parser/`` and ``core/ir/``.

Tests parse SHACL Turtle into ``NodeShapeIR`` and ``PropertyShapeIR``,
verify cardinality resolution (``FieldKind``), registry indexes, and
relationship property resolution (``sh:class``, ``sh:node``).

Order: minimal fixture baseline → cardinality → registry indexes → relationships.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import XSD

from fastshaql.core.ir import (
    FieldKind,
    NodeShapeIR,
    PropertyShapeIR,
    ValueType,
)
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.parser import parse_shapes
from support.builders import EX, scalar_property

# --- Minimal baseline ---


def test_parse_minimal_thing_shape(minimal_shapes_graph: Graph) -> None:
    registry = parse_shapes(minimal_shapes_graph)
    assert len(registry.shapes) == 1

    thing: NodeShapeIR = registry.by_type_name["Thing"]
    assert thing.graphql_type_name == "Thing"  # based on sh:codeIdentifier
    assert thing.iri == EX + "ThingShape"
    assert thing.target_class == EX + "Thing"

    assert set(thing.property_shapes) == {"label"}
    label: PropertyShapeIR = thing.property_shapes["label"]
    assert label.iri == URIRef("urn:fastshaql:inline:ThingLabel")
    assert label.graphql_field_name == "label"
    assert isinstance(label.path, PredicatePath)
    assert label.path.iri == EX + "label"
    assert label.datatype == XSD.string
    assert label.min_count == 1
    assert label.max_count == 1
    assert label.kind == FieldKind.REQUIRED_SCALAR


# --- Cardinality ---


def test_kind_absent_min_count() -> None:
    """``min_count=None`` is treated as 0 (optional), via the public ``kind``."""
    optional_scalar = scalar_property("note", min_count=None, max_count=1)
    assert optional_scalar.kind == FieldKind.OPTIONAL_SCALAR
    optional_list = scalar_property("tags", min_count=None, max_count=None)
    assert optional_list.kind == FieldKind.OPTIONAL_LIST


def test_parse_optional_scalar_when_min_count_absent(cardinality_shapes_graph) -> None:
    registry = parse_shapes(cardinality_shapes_graph)
    shape = registry.by_type_name["OptionalScalarThing"]
    note = shape.property_shapes["note"]
    assert note.min_count is None
    assert note.max_count == 1
    assert note.kind == FieldKind.OPTIONAL_SCALAR


def test_parse_optional_list_when_min_and_max_absent(cardinality_shapes_graph) -> None:
    registry = parse_shapes(cardinality_shapes_graph)
    shape = registry.by_type_name["OptionalListThing"]
    tag = shape.property_shapes["tag"]
    assert tag.min_count is None
    assert tag.max_count is None
    assert tag.kind == FieldKind.OPTIONAL_LIST


def test_parse_cardinality_thing_shape_kinds(cardinality_shapes_graph) -> None:
    registry = parse_shapes(cardinality_shapes_graph)
    thing = registry.by_type_name["Thing"]
    assert thing.property_shapes["label"].kind == FieldKind.REQUIRED_SCALAR
    assert thing.property_shapes["subtitle"].kind == FieldKind.OPTIONAL_SCALAR
    assert thing.property_shapes["tag"].kind == FieldKind.REQUIRED_LIST
    assert thing.property_shapes["altLabel"].kind == FieldKind.OPTIONAL_LIST


# --- Registry indexes ---


def test_registry_indexes(minimal_shapes_graph: Graph) -> None:
    registry = parse_shapes(minimal_shapes_graph)
    thing = registry.by_type_name["Thing"]
    assert thing.target_class == EX + "Thing"
    assert registry.by_target_class[EX + "Thing"] is thing
    assert registry.by_iri[EX + "ThingShape"] is thing


# --- Relationships ---


def test_parse_sh_class_resolves_value_shape(relationship_shapes_graph: Graph) -> None:
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    employer = person.property_shapes["employer"]

    assert employer.value_class == EX + "Company"
    assert employer.value_shape_iri == EX + "CompanyShape"
    assert registry.by_iri[EX + "CompanyShape"].graphql_type_name == "Company"
    assert employer.value_type is ValueType.RELATIONSHIP
    assert employer.datatype is None


def test_parse_sh_node_resolves_value_shape_by_iri(
    relationship_shapes_graph: Graph,
) -> None:
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    address = person.property_shapes["address"]

    assert address.value_class is None
    assert address.value_shape_iri == EX + "AddressShape"
    assert registry.by_iri[EX + "AddressShape"].graphql_type_name == "Address"


def test_parse_sh_class_creates_synthetic_shape_when_no_target(
    relationship_shapes_graph: Graph,
    caplog: pytest.LogCaptureFixture,
) -> None:
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    department = person.property_shapes["department"]

    assert department.value_class == EX + "Department"
    synthetic_iri = URIRef("urn:fastshaql:synthetic:Department")
    assert department.value_shape_iri == synthetic_iri
    synthetic = registry.by_iri[synthetic_iri]
    assert synthetic.target_class is None
    assert synthetic.property_shapes == {}
    assert registry.by_type_name["Department"] is synthetic
    assert "No shape targets class" in caplog.text


def test_parse_nested_value_shape_iri_resolves_through_registry(
    relationship_shapes_graph: Graph,
) -> None:
    """IRI indirection eliminates stale references — registry always holds resolved shapes."""
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    employer = person.property_shapes["employer"]
    assert employer.value_shape_iri is not None

    company = registry.by_iri[employer.value_shape_iri]
    located_in = company.property_shapes["locatedIn"]
    assert located_in.value_shape_iri is not None

    city = registry.by_iri[located_in.value_shape_iri]
    assert city.graphql_type_name == "City"
    assert city.iri == registry.by_type_name["City"].iri


# --- Duplicate field-name skip ---


def test_duplicate_graphql_field_name_skips_second(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two properties resolving to the same GraphQL field name: second is skipped."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:  <http://example.org/> .
        @prefix ex2: <http://other.org/> .
        @prefix sh:  <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [ sh:path ex:name  ; sh:datatype xsd:string ; sh:minCount 1 ] ;
            sh:property [ sh:path ex2:name ; sh:datatype xsd:string ; sh:minCount 1 ] .
        """,
        format="turtle",
    )
    with caplog.at_level("WARNING"):
        registry = parse_shapes(graph)
    person = registry.by_type_name["Person"]
    assert set(person.property_shapes) == {"name"}
    assert "Duplicate graphql field name" in caplog.text


# --- Blank-node NodeShape skip ---


def test_blank_node_shape_is_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A blank-node ``sh:NodeShape`` is not addressable and is skipped."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .

        [ a sh:NodeShape ;
            sh:property [ sh:path ex:label ] ] .
        """,
        format="turtle",
    )
    with caplog.at_level("WARNING"):
        registry = parse_shapes(graph)
    assert len(registry.shapes) == 0
    assert "Skipping blank-node NodeShape" in caplog.text


# --- Synthetic-shape cache ---


def test_repeated_sh_class_creates_single_synthetic_shape(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two properties referencing the same untargeted class share one synthetic."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .

        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [ sh:path ex:dept1 ; sh:class ex:Department ] ;
            sh:property [ sh:path ex:dept2 ; sh:class ex:Department ] .

        ex:OrgShape a sh:NodeShape ;
            sh:codeIdentifier "Org" ;
            sh:targetClass ex:Org ;
            sh:property [ sh:path ex:unit ; sh:class ex:Department ] .
        """,
        format="turtle",
    )
    with caplog.at_level("WARNING"):
        registry = parse_shapes(graph)
    synthetic_iri = URIRef("urn:fastshaql:synthetic:Department")
    assert synthetic_iri in registry.by_iri
    warnings = [r for r in caplog.records if "No shape targets class" in r.message]
    assert len(warnings) == 1


# --- rdfs:comment / rdfs:label description ---


def test_node_shape_description_from_rdfs_comment() -> None:
    """``rdfs:comment`` on a node shape populates ``description``."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "A thing." .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == "A thing."


def test_node_shape_description_falls_back_to_rdfs_label() -> None:
    """``rdfs:label`` is used when ``rdfs:comment`` is absent."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:label "ThingLabel" .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == "ThingLabel"


@pytest.mark.parametrize(
    ("turtle_extra", "expected"),
    [
        ('rdfs:comment "Une chose."@fr , "A thing."@en', "A thing."),
        ('rdfs:comment "Plain text." , "Autre"@fr', "Plain text."),
        ('rdfs:comment "Bonjour"@fr', "Bonjour"),
        ('rdfs:comment "US English"@en-US', "US English"),
        ('rdfs:label "Thing label"@en', "Thing label"),
    ],
    ids=[
        "preferred_lang",
        "untagged_over_foreign",
        "any_lang_fallback",
        "rfc4647_basic",
        "predicate_fallback",
    ],
)
def test_node_shape_description_language_selection_wired(
    turtle_extra: str,
    expected: str,
) -> None:
    """Language selection flows through ``parse_shapes`` (matrix in ``test_graph_reads``)."""
    graph = Graph()
    graph.parse(
        data=f"""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            {turtle_extra} .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == expected


def test_parse_shapes_description_language_parameter() -> None:
    """``description_language`` selects a non-default preferred language."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "A thing."@en , "Ein Ding."@de .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph, description_language="de")
    thing = registry.by_type_name["Thing"]
    assert thing.description == "Ein Ding."


def test_property_shape_description_language_selection() -> None:
    """Property shapes apply the same language preference to ``sh:description``."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:description "Étiquette"@fr , "Label"@en
            ] .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.property_shapes["label"].description == "Label"


def test_property_shape_description_falls_back_to_sh_name() -> None:
    """``sh:name`` supplies the property description when ``sh:description`` is absent."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:name "Display name"@en
            ] .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.property_shapes["label"].description == "Display name"


def test_node_shape_description_predicate_priority_over_language() -> None:
    """A foreign-language ``rdfs:comment`` beats a preferred-language ``rdfs:label``."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            rdfs:comment "Commentaire"@fr ;
            rdfs:label "English label"@en .
        """,
        format="turtle",
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.description == "Commentaire"


# --- Deactivated shapes (SHACL Core §3.1.6: not evaluated → no schema surface) ---


def _shapes_graph(turtle: str) -> Graph:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    return graph


def test_deactivated_node_shape_contributes_no_type() -> None:
    graph = _shapes_graph(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
            ] .
        ex:HiddenShape a sh:NodeShape ;
            sh:codeIdentifier "Hidden" ;
            sh:targetClass ex:Hidden ;
            sh:deactivated true ;
            sh:property [
                sh:path ex:secret ;
                sh:datatype xsd:string ;
            ] .
        """
    )
    registry = parse_shapes(graph)
    assert set(registry.by_type_name) == {"Thing"}


def test_deactivated_property_contributes_no_field() -> None:
    graph = _shapes_graph(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
            ] ;
            sh:property [
                sh:path ex:secret ;
                sh:datatype xsd:string ;
                sh:deactivated true ;
            ] .
        """
    )
    thing = parse_shapes(graph).by_type_name["Thing"]
    assert set(thing.property_shapes) == {"label"}


def test_deactivated_false_is_active() -> None:
    graph = _shapes_graph(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:deactivated false ;
            ] .
        """
    )
    thing = parse_shapes(graph).by_type_name["Thing"]
    assert set(thing.property_shapes) == {"label"}
