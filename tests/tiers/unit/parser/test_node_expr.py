"""``sh:values`` node-expression parsing — ``core/parser/node_expr/parse.py``.

Unit tier: the constant arm, the derived-field boundary rules, the
``shnex:`` arms (``pathValues``/``filterShape``/``if``/``exists``/
``ListExpression``), and the ``sh:defaultValue`` host predicate.
Prefix resolution and expansion live in ``test_shacl_prefixes.py``;
select-body surgery in ``test_select_scan.py``. Mirrors ``test_shacl_in.py``
style: inline Turtle + ``caplog`` for warnings.
"""

from __future__ import annotations

import logging

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from fastshaql.core.ir.filter_shape import (
    FilterClass,
    FilterCompare,
    FilterConstraintIR,
    FilterDatatype,
    FilterHasValue,
    FilterMinCountOne,
    FilterProperty,
    FilterRegex,
    FilterRootClass,
    FilterShapeIR,
)
from fastshaql.core.ir.node_expr import (
    ConstantListNodeExpr,
    ConstantNodeExpr,
    ExistsNodeExpr,
    FilterShapeNodeExpr,
    IfNodeExpr,
    InstancesOfNodeExpr,
    NodeExprIR,
    PathValuesNodeExpr,
    SelectNodeExpr,
    SparqlExprNodeExpr,
    is_multivalued_capable,
)
from fastshaql.core.ir.property_shape import ValueSource, ValueType
from fastshaql.core.ir.shacl_path import InversePath, PredicatePath
from fastshaql.core.kernel.identifiers import local_name
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.node_expr import UnsupportedShapeError, parse_node_expr
from fastshaql.core.parser.node_expr.parse import _DEFERRED_KEY_PARAMS
from fastshaql.core.parser.node_expr.semantics import arm_label
from fastshaql.core.parser.parse import parse_shapes
from fastshaql.core.parser.shacl_path import UnsupportedShaclPathError

EX = URIRef("http://example.org/")


def _graph_with_values(turtle: str) -> tuple[Graph, URIRef]:
    return load_shapes(turtle), URIRef("http://example.org/prop")


def _thing_shape(properties: str) -> str:
    """Turtle for one ``Thing``-targeting node shape wrapping *properties*
    (one or more ``sh:property […]`` blocks, each ending ``] ;`` or ``] .``)."""
    return f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:Shape a sh:NodeShape ;
            sh:codeIdentifier "Thing" ;
            sh:targetClass ex:Thing ;
            {properties}
    """


# --- Constant arm ---


def test_parse_literal_constant() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values "FastshaqlEMR" .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, ConstantNodeExpr)
    assert expr.value == Literal("FastshaqlEMR")


def test_parse_iri_constant() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values ex:Tag .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, ConstantNodeExpr)
    assert expr.value == URIRef("http://example.org/Tag")


def test_absent_values_returns_none() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape .
        """
    )
    assert parse_node_expr(graph, prop) is None


# --- Boundary raises (property_shape wiring) ---


def test_multiple_values_raises() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:values "FastshaqlEMR" ;
            sh:values "OtherEMR" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="more than one sh:values"):
        parse_shapes(load_shapes(turtle))


def test_derived_without_datatype_raises() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="sh:datatype"):
        parse_shapes(load_shapes(turtle))


@pytest.mark.parametrize("anchor", ["sh:class ex:Other", "sh:node ex:OtherShape"])
def test_derived_plus_relationship_anchor_is_derived_relationship(
    anchor: str,
) -> None:
    """``sh:values`` + ``sh:class``/``sh:node`` is a derived relationship —
    supported (ADR-0015); (RELATIONSHIP, DERIVED)."""
    turtle = _thing_shape(
        f"""sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            {anchor} ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.value_type is ValueType.RELATIONSHIP
    assert prop.source is ValueSource.DERIVED


def test_derived_sparql_expr_list_raises() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:tags ;
            sh:datatype xsd:string ;
            sh:values [ sh:sparqlExpr "STRLEN(STR($this))" ] ;
        ] ."""
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"uses sh:sparqlExpr.*multi-valued arm"
    ):
        parse_shapes(load_shapes(turtle))


def test_derived_constant_list_raises() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:tags ;
            sh:datatype xsd:string ;
            sh:values "only-one" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"uses constant.*multi-valued arm"):
        parse_shapes(load_shapes(turtle))


def test_derived_select_list_parses() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:tags ;
            sh:datatype xsd:string ;
            sh:minCount 0 ;
            sh:values [
                sh:select \"\"\"
                    SELECT ?tag
                    WHERE { $this ex:tag ?tag }
                \"\"\";
            ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["tags"]
    assert isinstance(prop.values_expr, SelectNodeExpr)
    assert prop.kind.is_list


@pytest.mark.parametrize("host_predicate", ["sh:values", "sh:defaultValue"])
def test_composite_path_plus_host_predicate_raises(host_predicate: str) -> None:
    """SHACL Core §3.3: values for ``sh:values``/``sh:defaultValue`` require a
    predicate ``sh:path``."""
    turtle = _thing_shape(
        f"""sh:property [
            sh:path ( ex:first ex:last ) ;
            sh:codeIdentifier "fullName" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            {host_predicate} "FastshaqlEMR" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="predicate"):
        parse_shapes(load_shapes(turtle))


def test_derived_with_datatype_parses_values_expr() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    shape = registry.by_type_name["Thing"]
    prop = shape.property_shapes["recordSource"]
    assert isinstance(prop.values_expr, ConstantNodeExpr)
    assert prop.values_expr.value == Literal("FastshaqlEMR")


# --- Boundary warnings ---


def test_derived_plus_in_is_derived_enum() -> None:
    """``sh:values`` + ``sh:in`` is a derived enum — (ENUM, DERIVED) — no
    read-ignored warning (ADR-0015)."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:in ( "a" "b" ) ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.value_type is ValueType.ENUM
    assert prop.source is ValueSource.DERIVED


def test_derived_min_count_warns(caplog: pytest.LogCaptureFixture) -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1 ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    with caplog.at_level(logging.WARNING):
        registry = parse_shapes(load_shapes(turtle))
    assert any("minCount" in r.message for r in caplog.records)
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.min_count == 1


# --- Unsupported forms ---


DEFERRED_SHNEX_OPERATORS = (
    "var",
    "distinct",
    "intersection",
    "concat",
    "remove",
    "limit",
    "offset",
    "orderBy",
    "flatMap",
    "findFirst",
    "matchAll",
    "count",
    "min",
    "max",
    "sum",
    "nodesMatching",
    "conformsToShape",
    "arg",
)
"""Every deferred ``shnex:`` operator (ADR-0015; inventory in the
node-expressions section of docs/SUPPORT.md — Sub-SELECT tier and named rejects).

The promotion protocol (``parse.py``): delete the ``_DEFERRED_KEY_PARAMS``
entry, add a ``_FUNCTIONS`` row, then flip the corresponding param here to a
happy-path test. :func:`test_deferred_inventory_matches_parser` keeps this
list and the parser's in lock-step so neither direction drifts silently.
``shnex:instancesOf`` is the first promoted operator (ADR-0016)."""


@pytest.mark.parametrize("op", DEFERRED_SHNEX_OPERATORS)
def test_deferred_shnex_operator_rejects_by_name(op: str) -> None:
    graph, prop = _graph_with_values(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:{op} ex:thing ] .
        """
    )
    # The categorised message guards a half-promotion: an op that gained a
    # _FUNCTIONS row but stayed in both lists would fail with a *different*
    # error class here, not the deferred "not supported" rejection.
    with pytest.raises(UnsupportedShapeError, match=f"shnex:{op}.*not supported"):
        parse_node_expr(graph, prop)


def test_deferred_inventory_matches_parser() -> None:
    assert {local_name(p) for p in _DEFERRED_KEY_PARAMS} == set(
        DEFERRED_SHNEX_OPERATORS
    )


def test_shnex_key_param_named_not_auxiliary() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:distinct [ shnex:pathValues ex:flag ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:distinct") as exc_info:
        parse_node_expr(graph, prop)
    assert "pathValues" not in str(exc_info.value)


def test_shnex_key_param_named_alongside_shared_auxiliary() -> None:
    """The deferred operator is named even when a shared auxiliary sits on the
    same node — the message must not depend on RDF predicate ordering."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:remove [ shnex:pathValues ex:excluded ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:remove"):
        parse_node_expr(graph, prop)


def test_shnex_path_values_parses() -> None:
    """``shnex:pathValues`` with a predicate path is supported (ADR-0015)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:pathValues ex:foo ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == PathValuesNodeExpr(path=PredicatePath(EX + "foo"), focus_node=None)


def test_shnex_path_values_single_member_list_raises() -> None:
    """The operand is a path, not a wrapping list — a one-member sequence
    list violates §4.2 (≥2 members), same as at ``sh:path``."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:pathValues ( ex:foo ) ] .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="at least two members"):
        parse_node_expr(graph, prop)


def test_shnex_path_values_focus_node_constant_parses() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues [ sh:inversePath rdf:type ] ;
                shnex:focusNode ex:Concept ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == PathValuesNodeExpr(
        path=InversePath(PredicatePath(RDF.type)), focus_node=EX + "Concept"
    )


def test_shnex_path_values_nonconstant_focus_node_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                shnex:focusNode [ shnex:pathValues ex:bar ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:focusNode"):
        parse_node_expr(graph, prop)


# --- shnex:instancesOf (node-expr §4.5.1, promoted by ADR-0016) ---


def test_shnex_instances_of_constant_iri_parses() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf ex:Variant ] .
        """
    )
    assert parse_node_expr(graph, prop) == InstancesOfNodeExpr(
        classes=(EX + "Variant",)
    )


def test_shnex_instances_of_iri_list_parses() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf ( ex:Substitution ex:Deletion ) ] .
        """
    )
    assert parse_node_expr(graph, prop) == InstancesOfNodeExpr(
        classes=(EX + "Substitution", EX + "Deletion")
    )


def test_shnex_instances_of_literal_class_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf "Variant" ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:instancesOf.*constant class"
    ):
        parse_node_expr(graph, prop)


def test_shnex_instances_of_expression_class_raises() -> None:
    """Arbitrary class expressions reject loudly — constants fold only."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf [ shnex:pathValues ex:meta ] ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:instancesOf.*constant class"
    ):
        parse_node_expr(graph, prop)


def test_shnex_instances_of_literal_in_list_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf ( ex:Variant "Deletion" ) ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:instancesOf.*constant class"
    ):
        parse_node_expr(graph, prop)


def test_shnex_instances_of_is_multivalued_capable() -> None:
    """Instances are a node set — list-typed derived fields accept the arm."""
    assert is_multivalued_capable(InstancesOfNodeExpr(classes=(EX + "Variant",)))


def test_shnex_instances_of_arm_label() -> None:
    assert arm_label(InstancesOfNodeExpr(classes=(EX + "Variant",))) == (
        "shnex:instancesOf"
    )


def test_shnex_orphan_auxiliary_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:then "x" ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="no recognised key parameter"):
        parse_node_expr(graph, prop)


def test_empty_expression_raises() -> None:
    """A bare ``[]`` is the spec's empty expression (node-expr §4.1.1, output
    ``()``) — rejected loudly as such, not mislabelled unsupported SPARQL."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"empty node expression.*§4.1.1"):
        parse_node_expr(graph, prop)


def test_unrecognized_function_names_predicate() -> None:
    """``sparql:`` list-parameter functions and custom functions reject with
    the carried predicate named (ADR-0015's "rejected loudly by name")."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix sparql: <http://www.w3.org/ns/shacl-sparql#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ sparql:concat ( "a" "b" ) ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError,
        match=r"carries http://www.w3.org/ns/shacl-sparql#concat",
    ):
        parse_node_expr(graph, prop)


# --- Key-parameter model (node-expr §3.2.1): exactly one function identifier,
# its declared parameters only ---


def test_path_values_with_filter_shape_raises() -> None:
    """Two key parameters on one expression node are ill-formed (node-expr
    §3.2.1), regardless of which pair."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                shnex:filterShape [ sh:class ex:C ] ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match="more than one key parameter"
    ) as exc_info:
        parse_node_expr(graph, prop)
    assert "shnex:pathValues" in str(exc_info.value)
    assert "shnex:filterShape" in str(exc_info.value)


def test_duplicate_path_values_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                shnex:pathValues ex:bar ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="more than once"):
        parse_node_expr(graph, prop)


def test_path_values_with_nodes_parameter_raises() -> None:
    """``shnex:nodes`` belongs to ``shnex:filterShape``, not ``pathValues``."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                shnex:nodes ex:bar ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"shnex:nodes.*not a parameter"):
        parse_node_expr(graph, prop)


def test_filter_shape_with_focus_node_parameter_raises() -> None:
    """``shnex:focusNode`` belongs to ``shnex:pathValues``, not ``filterShape``."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:class ex:C ] ;
                shnex:focusNode ex:Root ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:focusNode.*not a parameter"
    ):
        parse_node_expr(graph, prop)


def test_path_values_with_foreign_predicate_raises() -> None:
    """Any predicate beyond the function's key + parameters is ill-formed."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                rdfs:label "notes" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"rdfs:label.*not a parameter"):
        parse_node_expr(graph, prop)


def test_parse_sparql_expr() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ sh:sparqlExpr "STRLEN(STR($this))" ] .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, SparqlExprNodeExpr)
    assert expr.expr == "STRLEN(STR($this))"


def test_parse_sparql_expr_expands_prefixes() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                sh:prefixes [
                    sh:declare [
                        sh:prefix "demo" ;
                        sh:namespace "http://example.org/demo/" ;
                    ] ;
                ] ;
                sh:sparqlExpr "EXISTS { $this demo:hasGoal ?g }" ;
            ] .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, SparqlExprNodeExpr)
    assert expr.expr == "EXISTS { $this <http://example.org/demo/hasGoal> ?g }"


def test_derived_sparql_expr_parses_end_to_end() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:uriLength ;
            sh:datatype xsd:integer ;
            sh:maxCount 1 ;
            sh:values [ sh:sparqlExpr "STRLEN(STR($this))" ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    shape = registry.by_type_name["Thing"]
    prop = shape.property_shapes["uriLength"]

    assert isinstance(prop.values_expr, SparqlExprNodeExpr)
    assert prop.values_expr.expr == "STRLEN(STR($this))"


def test_parse_select_end_to_end() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:values [
                sh:prefixes ex:prefixes ;
                sh:select \"\"\"
                    SELECT ?label
                    WHERE {
                        $this ex:givenName ?given .
                        $this ex:familyName ?family .
                        BIND(CONCAT(?given, ' ', ?family) AS ?label)
                    }\"\"\" ;
            ] ;
        ] .
        ex:prefixes a sh:ShapesGraph ;
        sh:declare [ sh:prefix "ex" ; sh:namespace "http://example.org/" ] .    """
    )
    registry = parse_shapes(load_shapes(turtle))
    shape = registry.by_type_name["Thing"]
    prop = shape.property_shapes["label"]

    assert isinstance(prop.values_expr, SelectNodeExpr)
    assert prop.values_expr.projection_var == "label"
    assert "BIND(CONCAT(?given" in prop.values_expr.body
    assert "$this" in prop.values_expr.body
    # Prefixes are expanded at parse time (ADR-0015): ex:givenName -> full IRI.
    assert "<http://example.org/givenName>" in prop.values_expr.body


# --- sh:defaultValue (value-nodes step 3, ADR-0015) ---


def test_default_value_constant_parses() -> None:
    """``sh:defaultValue`` alone: asserted path + step-3 fallback — the IR
    carries ``default_expr`` beside ``values_expr=None`` (ADR-0015)."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue "fallback" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.values_expr is None
    assert prop.default_expr == ConstantNodeExpr(Literal("fallback"))


def test_default_value_with_values_parses_both() -> None:
    """``sh:values`` + ``sh:defaultValue``: the fallback sits behind the
    derived values (value-nodes steps 2 then 3)."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue "fallback" ;
            sh:values [ shnex:pathValues ex:source ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert isinstance(prop.values_expr, PathValuesNodeExpr)
    assert prop.default_expr == ConstantNodeExpr(Literal("fallback"))


@pytest.mark.parametrize(
    ("default_body", "expected"),
    [
        ('"fallback"', ConstantNodeExpr(Literal("fallback"))),
        (
            "[ sh:sparqlExpr \"CONCAT('ref-', STR($this))\" ]",
            SparqlExprNodeExpr("CONCAT('ref-', STR($this))"),
        ),
        (
            "[ shnex:exists [ shnex:pathValues ex:flag ] ]",
            ExistsNodeExpr(PathValuesNodeExpr(path=PredicatePath(EX + "flag"))),
        ),
        (
            (
                "[ shnex:if [ shnex:exists [ shnex:pathValues ex:flag ] ] ;"
                ' shnex:then "flagged" ; shnex:else "plain" ]'
            ),
            IfNodeExpr(
                cond=ExistsNodeExpr(
                    PathValuesNodeExpr(path=PredicatePath(EX + "flag"))
                ),
                then=ConstantNodeExpr(Literal("flagged")),
                otherwise=ConstantNodeExpr(Literal("plain")),
            ),
        ),
    ],
    ids=["constant", "sparql-expr", "exists", "nested-if"],
)
def test_default_value_expression_parses(
    default_body: str, expected: NodeExprIR
) -> None:
    """The default is a node expression — every statically single-valued
    arm (constants, ``sh:sparqlExpr``, ``shnex:exists``, nested
    single-valued ``shnex:if``) parses."""
    turtle = _thing_shape(
        f"""sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue {default_body} ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.default_expr == expected


def test_default_value_twice_raises() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue "a" ;
            sh:defaultValue "b" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="more than one sh:defaultValue"):
        parse_shapes(load_shapes(turtle))


def test_default_value_relationship_raises() -> None:
    """Scalar-only (ADR-0015): a defaulted relationship would need
    per-entity set-emptiness over join rows — not flat-expressible."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:parent ;
            sh:class ex:Thing ;
            sh:maxCount 1 ;
            sh:defaultValue ex:someThing ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="scalar"):
        parse_shapes(load_shapes(turtle))


def test_default_value_without_datatype_raises() -> None:
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:maxCount 1 ;
            sh:defaultValue "fallback" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="sh:datatype"):
        parse_shapes(load_shapes(turtle))


@pytest.mark.parametrize(
    "max_count_clause", ["", " ; sh:maxCount 2"], ids=["no_max_count", "max_count_2"]
)
def test_default_value_list_cardinality_raises(max_count_clause: str) -> None:
    """List cardinality + default = multi-valued fallback — rejected, both
    when ``sh:maxCount`` is absent and when it exceeds 1."""
    turtle = _thing_shape(
        f"""sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:defaultValue "fallback"{max_count_clause} ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"maxCount 1"):
        parse_shapes(load_shapes(turtle))


def test_default_value_multivalued_arm_raises() -> None:
    """A multi-valued default expression cannot honour the single-value
    fallback — same single-valued discipline as ``shnex:if`` branches."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue [ shnex:pathValues ex:source ] ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"defaultValue.*single-valued"):
        parse_shapes(load_shapes(turtle))


# --- shnex:filterShape (ADR-0015) ---


def test_filter_shape_pattern_parses_at_node_level() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:pattern "^http://example.org/variant/" ;
                ] ;
            ] .
        """
    )
    assert parse_node_expr(graph, prop) == FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(
            conjuncts=(FilterRegex(pattern=Literal("^http://example.org/variant/")),)
        ),
    )


def test_filter_shape_pattern_with_flags_parses_at_property_level() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:code ;
                        sh:pattern "^A" ;
                        sh:flags "i" ;
                    ] ;
                ] ;
            ] .
        """
    )
    assert parse_node_expr(graph, prop) == FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(
            conjuncts=(
                FilterProperty(
                    path=PredicatePath(EX + "code"),
                    nested=FilterShapeIR(
                        conjuncts=(FilterRegex(Literal("^A"), Literal("i")),)
                    ),
                ),
            )
        ),
    )


@pytest.mark.parametrize(
    "constraint",
    [
        'sh:pattern "x" ; sh:pattern ex:NotALiteral',
        'sh:pattern "x" ; sh:flags ex:NotALiteral',
        'sh:pattern "x" ; sh:flags "i" ; sh:flags "s"',
    ],
    ids=["non-literal-pattern", "non-literal-flags", "multiple-flags"],
)
def test_filter_shape_pattern_malformed_values_raise(constraint: str) -> None:
    graph, prop = _graph_with_values(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [ {constraint} ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:filterShape"):
        parse_node_expr(graph, prop)


def test_filter_shape_has_value_property_parses() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:gender ;
                        sh:hasValue "male" ;
                    ] ;
                ] ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(
            conjuncts=(
                FilterProperty(
                    path=PredicatePath(EX + "gender"),
                    nested=FilterShapeIR(conjuncts=(FilterHasValue(Literal("male")),)),
                ),
            )
        ),
    )


def test_filter_shape_over_if_distributes_into_branches() -> None:
    """``filterShape`` over an ``shnex:if`` normalises to an ``if`` over two
    filter shapes — the condition never reads the candidate values, so the
    filter distributes over branch selection and each branch keeps its own
    conjuncts (they would otherwise outlive the arm that binds them)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [
                    shnex:if [ shnex:exists [ shnex:pathValues ex:review ] ] ;
                    shnex:then [ shnex:pathValues ex:reviewedTag ] ;
                    shnex:else [ shnex:pathValues ex:provisionalTag ] ;
                ] ;
                shnex:filterShape [ sh:class ex:Tag ] ;
            ] .
        """
    )
    shape = FilterShapeIR(conjuncts=(FilterClass((EX + "Tag",)),))
    assert parse_node_expr(graph, prop) == IfNodeExpr(
        cond=ExistsNodeExpr(
            inner=PathValuesNodeExpr(path=PredicatePath(EX + "review"))
        ),
        then=FilterShapeNodeExpr(
            nodes=PathValuesNodeExpr(path=PredicatePath(EX + "reviewedTag")),
            shape=shape,
        ),
        otherwise=FilterShapeNodeExpr(
            nodes=PathValuesNodeExpr(path=PredicatePath(EX + "provisionalTag")),
            shape=shape,
        ),
    )


def test_filter_shape_without_nodes_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:hasValue ex:x ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:nodes"):
        parse_node_expr(graph, prop)


def test_filter_shape_unknown_constraint_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:minLength 8 ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"shacl#minLength"):
        parse_node_expr(graph, prop)


def test_filter_shape_has_value_blank_node_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:hasValue [ ] ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:hasValue"):
        parse_node_expr(graph, prop)


def test_filter_shape_max_count_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:gender ;
                        sh:maxCount 1 ;
                    ] ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:maxCount"):
        parse_node_expr(graph, prop)


def test_filter_shape_nonliteral_range_bound_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:minInclusive ex:NotALiteral ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"minInclusive.*not a literal"):
        parse_node_expr(graph, prop)


def test_filter_shape_deactivated_conjunct_raises() -> None:
    """``sh:deactivated`` inside a filter shape would be silently ignored —
    the conjunct would apply anyway, opposite of the declared intent."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [
                    sh:deactivated true ;
                    sh:hasValue "x" ;
                ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shacl#deactivated.*not supported"
    ):
        parse_node_expr(graph, prop)


def test_filter_shape_min_count_two_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:gender ;
                        sh:minCount 2 ;
                    ] ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:minCount 2"):
        parse_node_expr(graph, prop)


def test_filter_shape_min_count_one_parses() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:review ;
                        sh:minCount 1 ;
                    ] ;
                ] ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert isinstance(ir, FilterShapeNodeExpr)
    assert ir.shape.conjuncts == (
        FilterProperty(
            path=PredicatePath(EX + "review"),
            nested=FilterShapeIR(conjuncts=(FilterMinCountOne(),)),
        ),
    )


_DERIVED_FLAG_PROPERTY = """
    sh:property [
        sh:path ex:derivedFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values "constant" ;
    ] ;
"""


@pytest.mark.parametrize(
    ("test_id", "consumer_property"),
    [
        (
            "path_values",
            """
    sh:property [
        sh:path ex:chained ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues ex:derivedFlag ] ;
    ] .
""",
        ),
        (
            "filter_shape_conjunct",
            """
    sh:property [
        sh:path ex:conjunct ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [
                sh:property [
                    sh:path ex:derivedFlag ;
                    sh:hasValue "keep" ;
                ] ;
            ] ;
            shnex:nodes [ shnex:pathValues ex:thing ] ;
        ] ;
    ] .
""",
        ),
        (
            "filter_shape_nodes_arm",
            """
    sh:property [
        sh:path ex:filtered ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [ sh:hasValue "x" ] ;
            shnex:nodes [ shnex:pathValues ex:derivedFlag ] ;
        ] ;
    ] .
""",
        ),
        (
            "if_branch",
            """
    sh:property [
        sh:path ex:chosen ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
            shnex:then [ shnex:pathValues ex:derivedFlag ] ;
            shnex:else "none" ;
        ] ;
    ] .
""",
        ),
        (
            "if_exists_condition",
            """
    sh:property [
        sh:path ex:chosen ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:if [ shnex:exists [ shnex:pathValues ex:derivedFlag ] ] ;
            shnex:then "yes" ;
            shnex:else "no" ;
        ] ;
    ] .
""",
        ),
        (
            "bare_exists",
            """
    sh:property [
        sh:path ex:hasFlag ;
        sh:datatype xsd:boolean ;
        sh:maxCount 1 ;
        sh:values [ shnex:exists [ shnex:pathValues ex:derivedFlag ] ] ;
    ] .
""",
        ),
    ],
)
def test_expression_targeting_derived_property_raises(
    test_id: str,  # noqa: ARG001 — naming-only parameter
    consumer_property: str,
) -> None:
    """Rule chaining (ADR-0015 deviation 5a): any node-expression position
    reading a predicate carried by another derived property shape rejects
    loudly — a derived property's asserted triples are ignored under
    replace-not-union, so the read would be silently empty or stale.
    Parametrized over every walkable position: ``pathValues`` paths,
    ``filterShape`` conjunct paths and ``nodes`` arms, ``shnex:if``
    branches and conditions, and bare ``shnex:exists`` values."""
    turtle = _thing_shape(
        f"""{_DERIVED_FLAG_PROPERTY}
            {consumer_property}"""
    )
    with pytest.raises(UnsupportedShapeError, match="rule chaining"):
        parse_shapes(load_shapes(turtle))


@pytest.mark.parametrize(
    ("test_id", "consumer_property"),
    [
        (
            "inverse_path",
            """
    sh:property [
        sh:path ex:inverseFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:inversePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "zero_or_more_path",
            """
    sh:property [
        sh:path ex:closureFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:zeroOrMorePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "one_or_more_path",
            """
    sh:property [
        sh:path ex:plusFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:oneOrMorePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "zero_or_one_path",
            """
    sh:property [
        sh:path ex:optionalFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:zeroOrOnePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "nested_modifier_path",
            """
    sh:property [
        sh:path ex:nestedFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:pathValues [ sh:zeroOrMorePath [ sh:inversePath ex:derivedFlag ] ]
        ] ;
    ] .
    """,
        ),
        (
            "sequence_path",
            """
    sh:property [
        sh:path ex:sequenceFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues ( ex:reviewed ex:derivedFlag ) ] ;
    ] .
    """,
        ),
        (
            "alternative_path",
            """
    sh:property [
        sh:path ex:eitherFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:pathValues [ sh:alternativePath ( ex:reviewed ex:derivedFlag ) ]
        ] ;
    ] .
    """,
        ),
        (
            "filter_shape_conjunct_inverse",
            """
    sh:property [
        sh:path ex:conjunctInverse ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [
                sh:property [
                    sh:path [ sh:inversePath ex:derivedFlag ] ;
                    sh:hasValue "keep" ;
                ] ;
            ] ;
            shnex:nodes [ shnex:pathValues ex:thing ] ;
        ] ;
    ] .
    """,
        ),
        (
            "filter_shape_conjunct_sequence",
            """
    sh:property [
        sh:path ex:conjunctSequence ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [
                sh:property [
                    sh:path ( ex:reviewed ex:derivedFlag ) ;
                    sh:hasValue "keep" ;
                ] ;
            ] ;
            shnex:nodes [ shnex:pathValues ex:thing ] ;
        ] ;
    ] .
    """,
        ),
    ],
)
def test_composite_path_targeting_derived_property_raises(
    test_id: str,  # noqa: ARG001 — naming-only parameter
    consumer_property: str,
) -> None:
    """The rule-chaining walk must descend into composite paths (SHACL §4):
    unary modifiers, sequences, and alternatives yield their inner
    predicates to :func:`iter_path_predicates`, so a derived predicate
    anywhere inside a composite path rejects just like a bare one —
    at ``shnex:pathValues`` positions and in ``filterShape`` conjuncts."""
    turtle = _thing_shape(
        f"""{_DERIVED_FLAG_PROPERTY}
            {consumer_property}"""
    )
    with pytest.raises(UnsupportedShapeError, match="rule chaining"):
        parse_shapes(load_shapes(turtle))


def test_if_without_then_walk_skips_absent_branch() -> None:
    """``shnex:if`` requires only one of ``shnex:then``/``shnex:else`` — the
    rule-chaining walk must skip the absent arm (no paths to walk) and still
    walk the present one."""
    turtle = _thing_shape(
        """
        sh:property [
            sh:path ex:chosen ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
                shnex:else "none" ;
            ] ;
        ] .
    """
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["chosen"]
    assert prop.values_expr == IfNodeExpr(
        cond=ExistsNodeExpr(
            inner=PathValuesNodeExpr(path=PredicatePath(EX + "reviewed"))
        ),
        then=None,
        otherwise=ConstantNodeExpr(Literal("none")),
    )


# --- Filter-shape conjunct coverage: term constraints and range bounds ---


@pytest.mark.parametrize(
    ("predicate", "value", "expected"),
    [
        ("sh:class", EX + "Class", FilterClass((EX + "Class",))),
        ("sh:datatype", EX + "DT", FilterDatatype(EX + "DT")),
    ],
)
def test_filter_shape_term_constraint_parses(predicate, value, expected) -> None:
    graph, prop = _graph_with_values(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ {predicate} {value.n3()} ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == FilterShapeNodeExpr(
        nodes=ConstantNodeExpr(EX + "thing"),
        shape=FilterShapeIR(conjuncts=(expected,)),
    )


def _filter_shape_conjuncts(turtle: str) -> tuple[FilterConstraintIR, ...]:
    graph, prop = _graph_with_values(turtle)
    ir = parse_node_expr(graph, prop)
    assert isinstance(ir, FilterShapeNodeExpr)
    return ir.shape.conjuncts


def test_filter_shape_class_list_parses_as_union() -> None:
    """``sh:class ( A B )`` — one conjunct holding the list: union within one
    value (Core §7.1.1 "use lists for union semantics")."""
    assert _filter_shape_conjuncts(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:class ( ex:Cat ex:Dog ) ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (FilterClass((EX + "Cat", EX + "Dog")),)


def test_filter_shape_class_nil_parses_as_empty_union() -> None:
    """``sh:class rdf:nil`` — the empty list is a legal single value (the
    class constraint matching nothing), distinct from a malformed list."""
    assert _filter_shape_conjuncts(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:class rdf:nil ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (FilterClass(()),)


def test_filter_shape_repeated_class_parses_as_conjunction() -> None:
    """Multiple ``sh:class`` triples — one conjunct each, AND-composed by the
    translator (Core §7.1.1: "multiple values ... are a conjunction")."""
    assert _filter_shape_conjuncts(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [
                    sh:class ex:Cat ;
                    sh:class ( ex:Dog ex:Owl ) ;
                ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (
        FilterClass((EX + "Cat",)),
        FilterClass((EX + "Dog", EX + "Owl")),
    )


def test_filter_shape_class_list_with_literal_member_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="not an IRI"):
        _filter_shape_conjuncts(
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:class ( ex:Cat "Dog" ) ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


def test_filter_shape_class_list_malformed_rest_raises() -> None:
    """Class lists share the strict list walk — a rest chain ending anywhere
    but ``rdf:nil`` rejects loudly."""
    with pytest.raises(UnsupportedShapeError, match=r"well-formed.*neither rdf:nil"):
        _filter_shape_conjuncts(
            """
            @prefix ex: <http://example.org/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [
                        sh:class [
                            rdf:first ex:Cat ;
                            rdf:rest ex:notANode ;
                        ] ;
                    ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


def test_filter_shape_class_literal_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="not an IRI or SHACL list of IRIs"):
        _filter_shape_conjuncts(
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:class "Cat" ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


def test_filter_shape_datatype_literal_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="must be IRIs"):
        _filter_shape_conjuncts(
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:datatype "string" ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


@pytest.mark.parametrize(
    "value",
    ["ex:Animal", "( ex:Animal ex:Plant )"],
)
def test_filter_shape_root_class_parses(value: str) -> None:
    """``sh:rootClass`` (Core §7.9.4) — same IRI-or-list syntax as sh:class."""
    expected = {
        "ex:Animal": FilterRootClass((EX + "Animal",)),
        "( ex:Animal ex:Plant )": FilterRootClass((EX + "Animal", EX + "Plant")),
    }[value]
    assert _filter_shape_conjuncts(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:rootClass {value} ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (expected,)


def test_filter_shape_root_class_literal_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="not an IRI or SHACL list of IRIs"):
        _filter_shape_conjuncts(
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:rootClass "Animal" ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


@pytest.mark.parametrize(
    ("predicate", "op"),
    [
        ("sh:minInclusive", ">="),
        ("sh:maxInclusive", "<="),
        ("sh:minExclusive", ">"),
        ("sh:maxExclusive", "<"),
    ],
)
def test_filter_shape_range_bound_parses(predicate, op) -> None:
    graph, prop = _graph_with_values(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ {predicate} 10 ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == FilterShapeNodeExpr(
        nodes=ConstantNodeExpr(EX + "thing"),
        shape=FilterShapeIR(conjuncts=(FilterCompare(op, Literal(10)),)),
    )


# --- Filter-shape malformed-input rejections ---


def test_filter_shape_named_shape_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape ex:NamedShape ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="blank-node shape"):
        parse_node_expr(graph, prop)


def test_filter_shape_property_without_path_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:property [ sh:hasValue "x" ] ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="without sh:path"):
        parse_node_expr(graph, prop)


def test_filter_shape_property_with_multiple_paths_raises() -> None:
    """A filter conjunct follows §3.3 too — no silent pick among paths."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [
                    sh:property [
                        sh:path ex:label , ex:name ;
                        sh:hasValue "x" ;
                    ] ;
                ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="Multiple sh:path values"):
        parse_node_expr(graph, prop)


def test_filter_shape_node_level_min_count_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:minCount 1 ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="only supported inside"):
        parse_node_expr(graph, prop)


def test_path_values_literal_focus_node_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                shnex:focusNode "literal" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:focusNode"):
        parse_node_expr(graph, prop)


def test_derived_list_field_filter_shape_over_constant_raises() -> None:
    """A single-valued ``shnex:nodes`` arm cannot honour list cardinality —
    the error names the composite arm."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:filtered ;
            sh:datatype xsd:string ;
            sh:values [
                shnex:filterShape [ sh:hasValue "x" ] ;
                shnex:nodes ex:thing ;
            ] ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"filterShape over constant"):
        parse_shapes(load_shapes(turtle))


def test_filter_shape_non_blank_property_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:property ex:NamedProperty ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="must be a blank node"):
        parse_node_expr(graph, prop)


# --- shnex:if / shnex:exists / shnex:ListExpression (ADR-0015) ---


def test_shnex_if_with_exists_condition_parses() -> None:
    """``shnex:if`` with an ``shnex:exists`` condition and constant branches —
    the spec's fill-color shape (node-expr *If Expressions* example)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [
                    shnex:exists [ shnex:pathValues ex:capitalOf ] ;
                ] ;
                shnex:then "blue" ;
                shnex:else "red" ;
            ] .
        """
    )
    assert parse_node_expr(graph, prop) == IfNodeExpr(
        cond=ExistsNodeExpr(
            inner=PathValuesNodeExpr(path=PredicatePath(EX + "capitalOf"))
        ),
        then=ConstantNodeExpr(Literal("blue")),
        otherwise=ConstantNodeExpr(Literal("red")),
    )


def test_shnex_if_nested_if_condition_parses() -> None:
    """A nested ``shnex:if`` over single-valued branches is a statically
    single-valued condition (ADR-0015)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [
                    shnex:if [ shnex:exists [ shnex:pathValues ex:a ] ] ;
                    shnex:then true ;
                    shnex:else false ;
                ] ;
                shnex:then "yes" ;
            ] .
        """
    )
    assert parse_node_expr(graph, prop) == IfNodeExpr(
        cond=IfNodeExpr(
            cond=ExistsNodeExpr(inner=PathValuesNodeExpr(path=PredicatePath(EX + "a"))),
            then=ConstantNodeExpr(Literal(True)),
            otherwise=ConstantNodeExpr(Literal(False)),
        ),
        then=ConstantNodeExpr(Literal("yes")),
        otherwise=None,
    )


def test_shnex_if_nested_multivalued_condition_raises() -> None:
    """A nested ``shnex:if`` over a multi-valued branch is itself
    multi-valued — rejected as a condition like any other set-valued arm."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [
                    shnex:if [ shnex:exists [ shnex:pathValues ex:a ] ] ;
                    shnex:then ( "x" "y" ) ;
                    shnex:else ( "z" ) ;
                ] ;
                shnex:then "yes" ;
                shnex:else "no" ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"condition.*shnex:if.*single-valued"
    ):
        parse_node_expr(graph, prop)


def test_shnex_if_sparql_expr_condition_parses() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [ sh:sparqlExpr "BOUND($this)" ] ;
                shnex:else "none" ;
            ] .
        """
    )
    assert parse_node_expr(graph, prop) == IfNodeExpr(
        cond=SparqlExprNodeExpr("BOUND($this)"),
        then=None,
        otherwise=ConstantNodeExpr(Literal("none")),
    )


def test_shnex_if_without_branches_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:a ] ] ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match="at least one of shnex:then or shnex:else"
    ):
        parse_node_expr(graph, prop)


def test_shnex_if_set_valued_path_values_condition_raises() -> None:
    """A set-valued condition can bind differently per row in the flat
    lowering — rows would take different branches within one entity, which the
    spec forbids (the condition is evaluated once per focus node)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [ shnex:pathValues ex:flag ] ;
                shnex:then "yes" ;
                shnex:else "no" ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:pathValues.*single-valued"
    ) as exc_info:
        parse_node_expr(graph, prop)
    assert "shnex:if" in str(exc_info.value)


def test_shnex_if_set_valued_select_condition_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [
                    sh:select "SELECT ?f WHERE { $this ex:flag ?f }" ;
                ] ;
                shnex:then "yes" ;
                shnex:else "no" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"sh:select.*single-valued"):
        parse_node_expr(graph, prop)


def test_shnex_if_set_valued_list_condition_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if ( true false ) ;
                shnex:then "yes" ;
                shnex:else "no" ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:ListExpression.*single-valued"
    ):
        parse_node_expr(graph, prop)


def test_shnex_if_then_twice_raises() -> None:
    """Parameters are used at most once (node-expr §3 syntax rule)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:a ] ] ;
                shnex:then "yes" ;
                shnex:then "no" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:then"):
        parse_node_expr(graph, prop)


def test_shnex_if_foreign_parameter_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:a ] ] ;
                shnex:then "yes" ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"shnex:nodes.*not a parameter"):
        parse_node_expr(graph, prop)


def test_shnex_exists_parses() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:exists [ shnex:pathValues ex:child ] ] .
        """
    )
    assert parse_node_expr(graph, prop) == ExistsNodeExpr(
        inner=PathValuesNodeExpr(path=PredicatePath(EX + "child"))
    )


def test_shnex_exists_foreign_parameter_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:exists [ shnex:pathValues ex:child ] ;
                shnex:then "x" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"shnex:then.*not a parameter"):
        parse_node_expr(graph, prop)


def test_shnex_list_expression_parses() -> None:
    """A ``shnex:ListExpression`` is an RDF list of constants (literals/IRIs)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values ( "sweet" ex:Umami "sour" ) .
        """
    )
    assert parse_node_expr(graph, prop) == ConstantListNodeExpr(
        (Literal("sweet"), EX + "Umami", Literal("sour"))
    )


def test_shnex_empty_list_parses_as_constant_nil() -> None:
    """Bare ``rdf:nil`` as the ``sh:values`` object is an IRI expression, not
    an empty ``shnex:ListExpression`` (node-expr §4.1.3 note) — all
    well-formed list expressions have at least one member."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values () .
        """
    )
    assert parse_node_expr(graph, prop) == ConstantNodeExpr(RDF.nil)


def test_shnex_list_member_expression_raises() -> None:
    """List members must be constants — nested expressions are not part of
    the supported subset (the spec table requires literal or IRI members)."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values ( "sweet" [ shnex:pathValues ex:taste ] ) .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:ListExpression.*literal or IRI"
    ):
        parse_node_expr(graph, prop)


def test_shnex_list_malformed_termination_raises() -> None:
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [ rdf:first "sweet" ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:ListExpression.*well-formed"
    ):
        parse_node_expr(graph, prop)


def test_shnex_list_iri_rest_target_raises() -> None:
    """A rest chain ending anywhere but ``rdf:nil`` is malformed."""
    graph, prop = _graph_with_values(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                rdf:first "sweet" ;
                rdf:rest ex:notANode ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"neither rdf:nil nor a blank node"
    ):
        parse_node_expr(graph, prop)


def test_shnex_list_cyclic_rest_raises() -> None:
    graph = load_shapes(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values _:head .
        _:head rdf:first "sweet" ; rdf:rest _:head .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="cyclic rdf:rest"):
        parse_node_expr(graph, URIRef("http://example.org/prop"))


def test_shnex_list_duplicate_first_raises() -> None:
    """A duplicate ``rdf:first`` on a *chain* cell rejects in the list walk;
    on the head cell the key-parameter model catches it first ("more than once")."""
    graph = load_shapes(
        """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:prop a sh:PropertyShape ;
            sh:values _:head .
        _:head rdf:first "sweet" ; rdf:rest _:tail .
        _:tail rdf:first "sour" , "dry" ; rdf:rest () .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"exactly one rdf:first and one rdf:rest"
    ):
        parse_node_expr(graph, URIRef("http://example.org/prop"))


def test_derived_list_field_with_list_expression_parses() -> None:
    """A ListExpression honours list cardinality (multi-valued capable)."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:flavors ;
            sh:datatype xsd:string ;
            sh:values ( "sweet" "umami" ) ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["flavors"]
    assert isinstance(prop.values_expr, ConstantListNodeExpr)
    assert prop.kind.is_list


def test_derived_list_field_if_over_multi_valued_branch_parses() -> None:
    """An ``shnex:if`` with any multi-valued branch honours list cardinality."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:links ;
            sh:datatype xsd:string ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
                shnex:then [ shnex:pathValues ex:reviewedLink ] ;
                shnex:else [ shnex:pathValues ex:provisionalLink ] ;
            ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["links"]
    assert isinstance(prop.values_expr, IfNodeExpr)
    assert prop.kind.is_list


def test_derived_list_field_if_over_constants_raises() -> None:
    """An ``shnex:if`` over only single-valued branches cannot honour list
    cardinality — the error names the arm."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:statuses ;
            sh:datatype xsd:string ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
                shnex:then "reviewed" ;
                shnex:else "provisional" ;
            ] ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"uses shnex:if"):
        parse_shapes(load_shapes(turtle))


def test_derived_list_field_bare_exists_raises() -> None:
    """A bare ``shnex:exists`` is single-valued (total boolean) — the list
    cardinality error names the arm."""
    turtle = _thing_shape(
        """sh:property [
            sh:path ex:flags ;
            sh:datatype xsd:boolean ;
            sh:values [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"uses shnex:exists"):
        parse_shapes(load_shapes(turtle))
