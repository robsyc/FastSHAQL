"""Target declarations on shapes — ``sh:target*`` parsing (ADR-0016).

One target declaration per shape: ``sh:targetClass`` XOR exactly one
``sh:targetNode`` expression; unsupported target predicates, multiple values,
and mixed kinds reject loudly instead of being silently ignored. The spec
(Core §3.1.3) unions all declarations — the union widening is pre-staged, not
lowered.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from fastshaql.core.ir.node_expr import (
    ConstantNodeExpr,
    InstancesOfNodeExpr,
)
from fastshaql.core.parser import parse_shapes
from fastshaql.core.parser.errors import UnsupportedShapeError

EX = URIRef("http://example.org/")

_PREFIXES = """
@prefix ex:  <http://example.org/> .
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""


def _shapes_graph(turtle: str) -> Graph:
    graph = Graph()
    graph.parse(data=_PREFIXES + turtle, format="turtle")
    return graph


@pytest.mark.parametrize(
    ("target", "predicate_iri"),
    [
        ("sh:targetObjectsOf ex:knows", "ns/shacl#targetObjectsOf"),
        ("sh:targetSubjectsOf ex:knows", "ns/shacl#targetSubjectsOf"),
        ("sh:targetWhere [ sh:path ex:knows ]", "ns/shacl#targetWhere"),
    ],
    ids=["targetObjectsOf", "targetSubjectsOf", "targetWhere"],
)
def test_unsupported_target_predicate_rejects_loudly(
    target: str, predicate_iri: str
) -> None:
    graph = _shapes_graph(
        f"""
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            {target} .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=predicate_iri):
        parse_shapes(graph)


@pytest.mark.parametrize(
    "target",
    [
        'sh:target [ sh:select "?s WHERE { ?s ?p ?o }" ]',  # SHACL 1.1 style
        "sh:targetClasses ex:Thing",  # typo
        "sh:targetnode ex:Thing",  # case variant
    ],
    ids=["sparql-target", "typo", "case-variant"],
)
def test_unknown_target_predicate_rejects_by_scan(target: str) -> None:
    """Any ``sh:target*`` predicate outside the known inventory rejects —
    no target declaration is silently dropped."""
    graph = _shapes_graph(
        f"""
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            {target} .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="ns/shacl#target"):
        parse_shapes(graph)


def test_shapes_graph_shape_triple_rejects_with_data_graph_hint() -> None:
    """``sh:shape`` targets live in the data graph (Core §3.1.3.7); a
    shapes-graph triple is an author error and rejects as such."""
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:shape ex:OtherShape .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="data graph"):
        parse_shapes(graph)


def test_multiple_target_class_values_reject() -> None:
    """The spec unions the values (Core §3.1.3.2); v1 narrows to exactly one."""
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing , ex:Gadget .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:targetClass"):
        parse_shapes(graph)


def test_literal_target_class_value_rejects() -> None:
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass "Thing" .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:targetClass"):
        parse_shapes(graph)


def test_multiple_target_node_values_reject() -> None:
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetNode ex:Alpha , ex:Beta .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:targetNode"):
        parse_shapes(graph)


def test_target_class_and_target_node_mixed_reject() -> None:
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:targetNode ex:Alpha .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:targetNode"):
        parse_shapes(graph)


def test_unsupported_target_rejects_even_alongside_target_class() -> None:
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            sh:targetSubjectsOf ex:knows .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="ns/shacl#targetSubjectsOf"):
        parse_shapes(graph)


def test_single_target_class_still_parses() -> None:
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing .
        """
    )
    registry = parse_shapes(graph)
    assert registry.by_type_name["Thing"].target_class is not None


# --- sh:targetNode node expressions ---


def test_target_node_constant_parses() -> None:
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetNode ex:Alpha .
        """
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.target_class is None
    assert thing.target_expr == ConstantNodeExpr(EX + "Alpha")


def test_target_node_literal_parses() -> None:
    """Spec-valid (targets are RDF terms) and accepted per ADR-0016: a
    literal target lowers to ``BIND("…" AS ?iri)`` — a root field that can
    never match. The author's responsibility, not a parse error."""
    graph = _shapes_graph(
        """
        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetNode "a literal" .
        """
    )
    registry = parse_shapes(graph)
    assert registry.by_type_name["Thing"].target_expr == ConstantNodeExpr(
        Literal("a literal")
    )


def test_target_node_instances_of_parses() -> None:
    """The flagship: a subclass-closing root field (ADR-0016)."""
    graph = _shapes_graph(
        """
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .

        ex:VariantShape a sh:NodeShape ;
            sh:codeIdentifier "Variant" ;
            sh:targetNode [ shnex:instancesOf ex:Variant ] ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
            ] .
        """
    )
    registry = parse_shapes(graph)
    variant = registry.by_type_name["Variant"]
    assert variant.target_class is None
    assert variant.target_expr == InstancesOfNodeExpr(classes=(EX + "Variant",))


def test_target_node_unsupported_expression_rejects() -> None:
    """The uniform closed sum: unsupported expressions reject loudly here too."""
    graph = _shapes_graph(
        """
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .

        ex:ThingShape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetNode [ shnex:count ex:Thing ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:count"):
        parse_shapes(graph)


# --- implicit class targets (Core §3.1.3.3, ADR-0016) ---


def test_implicit_class_target_via_rdfs_class_parses() -> None:
    """A shape typed ``rdfs:Class`` targets the SHACL instances of its own
    IRI — the ``shnex:instancesOf`` lowering at the shape IRI."""
    graph = _shapes_graph(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Thing a sh:NodeShape, rdfs:Class ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
            ] .
        """
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.target_class is None
    assert thing.target_expr == InstancesOfNodeExpr(classes=(EX + "Thing",))


def test_implicit_class_target_via_shape_class_only_parses() -> None:
    """``sh:ShapeClass`` alone enumerates the shape (Core §3.1.3.3) — no
    ``sh:NodeShape`` triple needed."""
    graph = _shapes_graph(
        """
        @prefix sh: <http://www.w3.org/ns/shacl#> .

        ex:Thing a sh:ShapeClass ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
            ] .
        """
    )
    registry = parse_shapes(graph)
    thing = registry.by_type_name["Thing"]
    assert thing.target_expr == InstancesOfNodeExpr(classes=(EX + "Thing",))
    assert thing.has_target


def test_implicit_class_target_double_typed_is_one_declaration() -> None:
    """``rdfs:Class`` and ``sh:ShapeClass`` together stay one implicit target."""
    graph = _shapes_graph(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Thing a sh:NodeShape, sh:ShapeClass, rdfs:Class ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
            ] .
        """
    )
    registry = parse_shapes(graph)
    assert registry.by_type_name["Thing"].target_expr == InstancesOfNodeExpr(
        classes=(EX + "Thing",)
    )


def test_implicit_class_target_is_class_indexed() -> None:
    """The implicit-target shape indexes under its own IRI — a ``sh:class``
    reference resolves to it, no synthetic shape."""
    graph = _shapes_graph(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Thing a sh:ShapeClass ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
            ] .

        ex:HolderShape a sh:NodeShape ;
            sh:codeIdentifier "Holder" ;
            sh:targetClass ex:Holder ;
            sh:property [
                sh:path ex:thing ;
                sh:class ex:Thing ;
            ] .
        """
    )
    registry = parse_shapes(graph)
    holder = registry.by_type_name["Holder"]
    (thing_field,) = holder.property_shapes.values()
    assert thing_field.value_shape_iri == EX + "Thing"
    assert EX + "Thing" in registry.by_iri


@pytest.mark.parametrize(
    "declarations",
    [
        """
        ex:Thing a sh:ShapeClass ;
            sh:targetClass ex:Stuff .
        """,
        """
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .

        ex:Thing a sh:ShapeClass ;
            sh:targetNode [ shnex:instancesOf ex:Stuff ] .
        """,
    ],
    ids=["with-target-class", "with-target-node"],
)
def test_implicit_class_target_mixed_rejects(declarations: str) -> None:
    graph = _shapes_graph(declarations)
    with pytest.raises(UnsupportedShapeError, match="implicit class target"):
        parse_shapes(graph)
