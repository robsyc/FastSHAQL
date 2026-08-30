"""Node shape inheritance via ``sh:node`` — ``core/parser/parse.py`` (ADR-0005).

Unit tier: flatten merge, collision/cycle rules, provenance, backward compatibility.

Order: fixture-backed happy paths → provenance → collisions → cycles → errors → compat.
"""

from __future__ import annotations

import textwrap

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import XSD

from fastshaql.core.ir.property_shape import ValueType
from fastshaql.core.ir.shacl_path import SequencePath
from fastshaql.core.parser import parse_shapes

_PREFIXES = textwrap.dedent(
    """
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix ex: <http://example.org/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    """
)


def _graph(turtle_body: str) -> Graph:
    graph = Graph()
    graph.parse(data=_PREFIXES + turtle_body, format="turtle")
    return graph


def test_single_parent_inherits_scalar(inheritance_registry) -> None:
    child = inheritance_registry.by_type_name["SingleChild"]
    assert "baseTag" in child.property_shapes
    assert "childTag" in child.property_shapes


def test_multi_parent_union(inheritance_registry) -> None:
    child = inheritance_registry.by_type_name["MultiChild"]
    assert set(child.property_shapes) == {"oneTag", "twoTag", "childOnly"}


def test_transitive_chain(inheritance_registry) -> None:
    leaf = inheritance_registry.by_type_name["TransLeaf"]
    assert set(leaf.property_shapes) == {"rootTag", "midTag", "leafTag"}


def test_shared_grandparent_diamond_does_not_raise(inheritance_registry) -> None:
    child = inheritance_registry.by_type_name["DiamondChild"]
    assert set(child.property_shapes) == {"diamondTag", "midATag", "midBTag", "rootTag"}


def test_inherited_composite_path_is_preserved(inheritance_registry) -> None:
    child = inheritance_registry.by_type_name["SeqChild"]
    prop = child.property_shapes["employeeName"]
    assert isinstance(prop.path, SequencePath)


def test_inherited_shape_iris_provenance(inheritance_registry) -> None:
    child = inheritance_registry.by_type_name["MultiChild"]
    base = inheritance_registry.by_type_name["SingleBase"]
    assert child.inherited_shape_iris == (
        URIRef("http://example.org/ParentOneShape"),
        URIRef("http://example.org/ParentTwoShape"),
    )
    assert base.inherited_shape_iris == ()


def test_child_own_field_overrides_inherited(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Own-beats-inherited (ADR-0005): the child's declaration wins,
    wholesale, with a warning naming the route (child, field, both property
    shapes, and the parent shape the field came through)."""
    turtle = textwrap.dedent(
        """
        ex:BaseShape a sh:NodeShape ;
            sh:codeIdentifier "Base" ;
            sh:property [
                sh:path ex:tag ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .

        ex:ChildShape a sh:NodeShape ;
            sh:codeIdentifier "Child" ;
            sh:node ex:BaseShape ;
            sh:property [
                sh:path ex:tag ;
                sh:datatype xsd:integer ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .
        """
    )
    with caplog.at_level("WARNING"):
        registry = parse_shapes(_graph(turtle))
    child = registry.by_type_name["Child"]
    assert child.property_shapes["tag"].datatype == XSD.integer
    overrides = [r for r in caplog.records if "override" in r.message]
    assert len(overrides) == 1
    message = overrides[0].getMessage()
    assert "Child" in message
    assert "'tag'" in message
    assert str(URIRef("http://example.org/BaseShape")) in message
    assert (
        "urn:fastshaql:inline:" in message
    )  # both property-shape IRIs are synthesized


def test_override_kind_change_allowed() -> None:
    """An override may change the field's kind — the child's declaration is the
    API contract (wholesale; compatibility policing is validator thinking)."""
    turtle = textwrap.dedent(
        """
        ex:BaseShape a sh:NodeShape ;
            sh:codeIdentifier "Base" ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .

        ex:ChildShape a sh:NodeShape ;
            sh:codeIdentifier "Child" ;
            sh:node ex:BaseShape ;
            sh:property [
                sh:path ex:label ;
                sh:class ex:Thing ;
                sh:minCount 0 ;
                sh:maxCount 1
            ] .
        """
    )
    registry = parse_shapes(_graph(turtle))
    child = registry.by_type_name["Child"]
    assert child.property_shapes["label"].value_type is ValueType.RELATIONSHIP
    assert child.property_shapes["label"].datatype is None


def test_transitive_nearest_definition_wins() -> None:
    """Root's tag overridden by Mid's own tag reaches the Leaf as Mid's — the
    nearest declaration on the inheritance path wins."""
    turtle = textwrap.dedent(
        """
        ex:RootShape a sh:NodeShape ;
            sh:codeIdentifier "Root" ;
            sh:property [
                sh:path ex:tag ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .

        ex:MidShape a sh:NodeShape ;
            sh:codeIdentifier "Mid" ;
            sh:node ex:RootShape ;
            sh:property [
                sh:path ex:tag ;
                sh:datatype xsd:integer ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .

        ex:LeafShape a sh:NodeShape ;
            sh:codeIdentifier "Leaf" ;
            sh:node ex:MidShape .
        """
    )
    registry = parse_shapes(_graph(turtle))
    leaf = registry.by_type_name["Leaf"]
    assert leaf.property_shapes["tag"].datatype == XSD.integer


def test_collision_two_parents_same_name_different_fields_raises() -> None:
    turtle = textwrap.dedent(
        """
        ex:LeftShape a sh:NodeShape ;
            sh:property [
                sh:path ex:shared ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .

        ex:RightShape a sh:NodeShape ;
            sh:property [
                sh:path ex:shared ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .

        ex:ChildShape a sh:NodeShape ;
            sh:node ex:LeftShape, ex:RightShape .
        """
    )
    with pytest.raises(ValueError, match=r"Field name collision"):
        parse_shapes(_graph(turtle))


@pytest.mark.parametrize(
    ("turtle", "path_fragment"),
    [
        (
            textwrap.dedent(
                """
                ex:AShape a sh:NodeShape ; sh:node ex:BShape .
                ex:BShape a sh:NodeShape ; sh:node ex:AShape .
                """
            ),
            "AShape -> BShape -> AShape",
        ),
        (
            textwrap.dedent(
                """
                ex:LoopShape a sh:NodeShape ; sh:node ex:LoopShape .
                """
            ),
            "LoopShape -> LoopShape",
        ),
    ],
    ids=["mutual", "self"],
)
def test_inheritance_cycle_raises(turtle: str, path_fragment: str) -> None:
    with pytest.raises(ValueError, match="Inheritance cycle") as exc_info:
        parse_shapes(_graph(turtle))
    message = str(exc_info.value)
    for segment in path_fragment.split(" -> "):
        assert segment in message


def test_blank_node_sh_node_raises() -> None:
    turtle = textwrap.dedent(
        """
        ex:ChildShape a sh:NodeShape ;
            sh:node [ a sh:NodeShape ] .
        """
    )
    with pytest.raises(NotImplementedError, match="Blank-node sh:node"):
        parse_shapes(_graph(turtle))


def test_sh_node_to_bare_class_raises_unknown_shape() -> None:
    turtle = textwrap.dedent(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

        ex:Person a rdfs:Class .

        ex:ChildShape a sh:NodeShape ;
            sh:node ex:Person .
        """
    )
    with pytest.raises(ValueError, match="Unknown inherited shape"):
        parse_shapes(_graph(turtle))


def test_backward_compat_no_sh_node(minimal_registry) -> None:
    for shape in minimal_registry.shapes:
        assert shape.inherited_shape_iris == ()
