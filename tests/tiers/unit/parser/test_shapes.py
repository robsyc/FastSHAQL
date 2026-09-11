"""SHACL shapes graph → Shape IR — ``core/parser/`` and ``core/ir/``.

Tests parse SHACL Turtle into ``NodeShapeIR`` and ``PropertyShapeIR``,
verify cardinality resolution (``FieldKind``), registry indexes, skip
behavior (duplicate field names, blank-node shapes, deactivated shapes),
unsupported counts and identifiers, zero-capacity field exclusion, and
read scoping within one shapes graph.

Order: minimal baseline → cardinality → registry indexes → field-name/blank-node/deactivated skips → unsupported counts → zero capacity → identifiers → read scoping.
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import RDF, SH, XSD

from fastshaql.core.ir import (
    FieldKind,
    NodeShapeIR,
    PropertyShapeIR,
)
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.parser import parse_shapes
from fastshaql.core.parser.errors import UnsupportedShapeError
from fastshaql.core.parser.util import InvalidCodeIdentifierError
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
    skip = [r for r in caplog.records if "Duplicate graphql field name" in r.message]
    assert len(skip) == 1
    # The warning names the field and the declaring shape; first-wins, the
    # second is skipped.
    message = skip[0].getMessage()
    assert f"Duplicate graphql field name name in {EX}PersonShape" in message


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
    skipping = [
        r for r in caplog.records if "Skipping blank-node NodeShape" in r.message
    ]
    assert len(skipping) == 1
    # The warning names the skipped node — not a bare reason string.
    bnode = next(graph.subjects(RDF.type, SH.NodeShape))
    message = skipping[0].getMessage()
    assert str(bnode) in message


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


def test_multiple_deactivated_values_reject() -> None:
    """§3.1.6 allows one ``sh:deactivated`` — a ``true , false`` pair would
    flip the shape's visibility nondeterministically."""
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
                sh:deactivated true , false ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="Multiple sh:deactivated"):
        parse_shapes(graph)


# --- Unsupported counts, zero capacity, and identifiers ---


def _person_graph(prop_body: str) -> Graph:
    """A Person shape whose single ``note`` property carries *prop_body*."""
    return _shapes_graph(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:note ;
                {prop_body}
            ] .
        """
    )


@pytest.mark.parametrize(
    "count_decl",
    [
        'sh:minCount "3" ;',
        'sh:maxCount "2.5"^^xsd:decimal ;',
        'sh:maxCount "3.0"^^xsd:integer ;',
    ],
    ids=["string_lexical", "decimal_datatype", "ill_typed_integer"],
)
def test_non_integer_count_rejects(count_decl: str) -> None:
    """§7.2.1/§7.2.2: counts are ``xsd:integer`` literals — anything else
    rejects instead of silently falling back to the optional-list defaults."""
    graph = _person_graph(count_decl)
    with pytest.raises(UnsupportedShapeError, match="xsd:integer literal"):
        parse_shapes(graph)


def test_multiple_min_count_values_reject() -> None:
    """§7.2: at most one ``sh:minCount`` — no silent arbitrary pick."""
    graph = _person_graph("sh:minCount 1 , 2 ;")
    with pytest.raises(UnsupportedShapeError, match="Multiple sh:minCount values"):
        parse_shapes(graph)


@pytest.mark.parametrize(
    ("body", "declaration_label"),
    [
        ("sh:datatype xsd:string ; sh:maxCount 0 ;", "sh:maxCount 0"),
        ("sh:datatype xsd:string ; sh:in () ;", "Empty sh:in"),
    ],
    ids=["max_count_zero", "empty_sh_in"],
)
def test_zero_capacity_property_excludes_field(
    body: str, declaration_label: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A property that can never hold values (§7.2.2, §7.9.3) generates no
    field, with a warning — the ``sh:deactivated`` reading (§3.1.6). The
    warning names the zero-capacity declaration and the property shape it
    came from, so the author can find the offending block."""
    with caplog.at_level("WARNING"):
        thing = parse_shapes(_person_graph(body)).by_type_name["Person"]
    assert "note" not in thing.property_shapes
    excluded = [r for r in caplog.records if "no field is generated" in r.message]
    assert len(excluded) == 1
    message = excluded[0].getMessage()
    assert declaration_label in message
    assert "on None" not in message  # the property shape is named, never dropped


@pytest.mark.parametrize(
    "declaration",
    [
        'sh:codeIdentifier "9Person"',
        'sh:property [ sh:path ex:note ; sh:codeIdentifier "has-dash" ]',
    ],
    ids=["node_shape", "property_shape"],
)
def test_invalid_code_identifier_rejects_at_parse(declaration: str) -> None:
    """§8.4 names must match ``^[a-zA-Z_][a-zA-Z0-9_]*$`` — validation fires
    at parse, not as a broken GraphQL schema build later."""
    graph = _shapes_graph(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:PersonShape a sh:NodeShape ;
            {declaration} ;
            sh:targetClass ex:Person .
        """
    )
    with pytest.raises(InvalidCodeIdentifierError, match="does not match"):
        parse_shapes(graph)


# --- Read scoping within one shapes graph ---


def test_property_reads_are_scoped_to_the_property() -> None:
    """One property's ``sh:description`` / ``sh:defaultValue`` never leak
    into a sibling property's read — a silent sibling stays silent."""
    graph = _shapes_graph(
        """
        @prefix ex:  <http://example.org/> .
        @prefix sh:  <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:rich ;
                sh:datatype xsd:string ;
                sh:maxCount 1 ;
                sh:description "Rich label"@en ;
                sh:defaultValue "fallback" ;
            ] ;
            sh:property [
                sh:path ex:plain ;
                sh:datatype xsd:string ;
                sh:maxCount 1 ;
            ] .
        """
    )
    plain = parse_shapes(graph).by_type_name["Person"].property_shapes["plain"]
    assert plain.description is None
    assert plain.default_expr is None


def test_node_description_read_is_scoped_to_the_shape() -> None:
    """An ``rdfs:comment`` on one shape never becomes another shape's
    description — the read is ``(shape_iri, rdfs:comment, ?)``."""
    graph = _shapes_graph(
        """
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:AlphaShape a sh:NodeShape ;
            sh:codeIdentifier "Alpha" ;
            sh:targetClass ex:Alpha ;
            rdfs:comment "Alpha comment"@en .

        ex:BetaShape a sh:NodeShape ;
            sh:codeIdentifier "Beta" ;
            sh:targetClass ex:Beta .
        """
    )
    assert parse_shapes(graph).by_type_name["Beta"].description is None


def test_shape_discovery_reads_rdf_type_only() -> None:
    """Shapes are discovered by ``(?, rdf:type, sh:NodeShape)`` — a resource
    that merely mentions ``sh:NodeShape`` as an object is nobody's shape."""
    graph = _shapes_graph(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing .

        ex:Ghost ex:mentions sh:NodeShape .
        """
    )
    assert set(parse_shapes(graph).by_type_name) == {"Thing"}


def test_property_walk_continues_past_skipped_properties(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A deactivated (§3.1.6), zero-capacity, or duplicate-name property is
    skipped alone — the walk still reaches every property after it. The
    skipped properties are declared first; ``sh:property`` objects iterate
    in document order."""
    graph = _shapes_graph(
        """
        @prefix ex:  <http://example.org/> .
        @prefix ex2: <http://other.org/> .
        @prefix sh:  <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [ sh:path ex:dead ; sh:datatype xsd:string ; sh:deactivated true ] ;
            sh:property [ sh:path ex:never ; sh:datatype xsd:string ; sh:maxCount 0 ] ;
            sh:property [ sh:path ex:name ; sh:datatype xsd:string ; sh:minCount 1 ] ;
            sh:property [ sh:path ex2:name ; sh:datatype xsd:string ; sh:minCount 1 ] ;
            sh:property [ sh:path ex:tag ; sh:datatype xsd:string ; sh:minCount 1 ] .
        """
    )
    with caplog.at_level("WARNING"):
        person = parse_shapes(graph).by_type_name["Person"]
    assert set(person.property_shapes) == {"name", "tag"}
    assert person.property_shapes["name"].min_count == 1


def test_blank_node_shape_skip_keeps_later_shapes(caplog) -> None:
    """Skipping a blank-node shape is per-shape: shapes after it in document
    order still parse (Core §3.1.6 adjacency — the skip must not end the
    pass)."""
    graph = _shapes_graph(
        """
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .

        [ a sh:NodeShape ; sh:targetClass ex:Ignored ] .
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing .
        """
    )
    assert "Thing" in parse_shapes(graph).by_type_name
    (blank_node,) = (
        s for s in graph.subjects(RDF.type, SH.NodeShape) if isinstance(s, BNode)
    )
    record = next(r for r in caplog.records if "blank-node NodeShape" in r.getMessage())
    assert record.getMessage().endswith(str(blank_node))


def test_deactivated_shape_skip_keeps_later_shapes() -> None:
    """A deactivated shape is skipped without ending the pass — shapes after
    it still parse (Core §3.1.6: not evaluated ≠ others dropped)."""
    graph = _shapes_graph(
        """
        @prefix ex:   <http://example.org/> .
        @prefix sh:   <http://www.w3.org/ns/shacl#> .

        ex:OldShape a sh:NodeShape ;
            sh:codeIdentifier "Old" ;
            sh:targetClass ex:Old ;
            sh:deactivated true .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing .
        """
    )
    registry = parse_shapes(graph).by_type_name
    assert "Old" not in registry
    assert "Thing" in registry


def test_malformed_max_count_error_names_the_declaration() -> None:
    """The count error names the offending predicate — ``sh:maxCount``, exact
    case, at the message start — so the author can find the block."""
    graph = _person_graph('sh:maxCount "2"^^xsd:decimal ;')
    with pytest.raises(
        UnsupportedShapeError,
        match=r"^sh:maxCount on .* must be an xsd:integer literal",
    ):
        parse_shapes(graph)
