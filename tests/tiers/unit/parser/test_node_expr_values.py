"""``sh:values`` expression arms — ``core/parser/node_expr/parse.py``.

Unit tier: the constant arm (literals/IRIs), ``shnex:pathValues``,
``shnex:instancesOf``, ``shnex:ListExpression``, the key-parameter model
(node-expr §3.2.1), and the deferred ``shnex:`` operator inventory. Sibling
files: ``test_node_expr_select.py``, ``test_node_expr_if.py``,
``test_node_expr_filter_shape.py``, ``test_node_expr_default_value.py``,
``test_node_expr_derived.py`` (boundary wiring), and
``test_node_expr_semantics.py`` (rule chaining). Mirrors ``test_shacl_in.py``
style: inline Turtle + ``caplog`` for warnings.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import RDF

from fastshaql.core.ir.node_expr import (
    ConstantListNodeExpr,
    ConstantNodeExpr,
    InstancesOfNodeExpr,
    PathValuesNodeExpr,
    is_multivalued_capable,
)
from fastshaql.core.ir.shacl_path import InversePath, PredicatePath
from fastshaql.core.kernel.identifiers import local_name
from fastshaql.core.parser.node_expr import UnsupportedShapeError, parse_node_expr
from fastshaql.core.parser.node_expr.parse import _DEFERRED_KEY_PARAMS
from fastshaql.core.parser.node_expr.semantics import arm_label
from fastshaql.core.parser.shacl_path import UnsupportedShaclPathError
from support.builders import EX, graph_with_values

# --- Constant arm ---


def test_parse_literal_constant() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values "FastshaqlEMR" .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, ConstantNodeExpr)
    assert expr.value == Literal("FastshaqlEMR")


def test_parse_iri_constant() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values ex:Tag .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, ConstantNodeExpr)
    assert expr.value == URIRef("http://example.org/Tag")


def test_absent_values_returns_none() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape .
        """
    )
    assert parse_node_expr(graph, prop) is None


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
    graph, prop = graph_with_values(
        f"""
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:pathValues ex:foo ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == PathValuesNodeExpr(path=PredicatePath(EX + "foo"), focus_node=None)


def test_shnex_path_values_single_member_list_raises() -> None:
    """The operand is a path, not a wrapping list — a one-member sequence
    list violates §4.2 (≥2 members), same as at ``sh:path``."""
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:pathValues ( ex:foo ) ] .
        """
    )
    with pytest.raises(UnsupportedShaclPathError, match="at least two members"):
        parse_node_expr(graph, prop)


def test_shnex_path_values_focus_node_constant_parses() -> None:
    graph, prop = graph_with_values(
        """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf ex:Variant ] .
        """
    )
    assert parse_node_expr(graph, prop) == InstancesOfNodeExpr(
        classes=(EX + "Variant",)
    )


def test_shnex_instances_of_iri_list_parses() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf ( ex:Substitution ex:Deletion ) ] .
        """
    )
    assert parse_node_expr(graph, prop) == InstancesOfNodeExpr(
        classes=(EX + "Substitution", EX + "Deletion")
    )


@pytest.mark.parametrize(
    "class_operand",
    ['"Variant"', "[ shnex:pathValues ex:meta ]", '( ex:Variant "Deletion" )'],
    ids=["literal", "expression", "literal_in_list"],
)
def test_shnex_instances_of_nonconstant_class_raises(class_operand: str) -> None:
    """The class operand folds constants only — a literal, an arbitrary class
    expression, or a literal inside the class list all reject loudly."""
    graph, prop = graph_with_values(
        f"""
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:instancesOf {class_operand} ] .
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
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:then "x" ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="no recognised key parameter"):
        parse_node_expr(graph, prop)


def test_empty_expression_raises() -> None:
    """A bare ``[]`` is the spec's empty expression (node-expr §4.1.1, output
    ``()``) — rejected loudly as such, not mislabelled unsupported SPARQL."""
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"empty node expression.*§4.1.1"):
        parse_node_expr(graph, prop)


def test_unrecognized_function_names_predicate() -> None:
    """``sparql:`` list-parameter functions and custom functions reject with
    the carried predicate named (ADR-0015's "rejected loudly by name")."""
    graph, prop = graph_with_values(
        """
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


# --- Key-parameter model (node-expr §3.2.1): exactly one function
# identifier, its declared parameters only ---


def test_path_values_with_filter_shape_raises() -> None:
    """Two key parameters on one expression node are ill-formed (node-expr
    §3.2.1), regardless of which pair."""
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                rdfs:label "notes" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"rdfs:label.*not a parameter"):
        parse_node_expr(graph, prop)


def test_path_values_literal_focus_node_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:pathValues ex:foo ;
                shnex:focusNode "literal" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:focusNode"):
        parse_node_expr(graph, prop)


# --- shnex:ListExpression ---


def test_shnex_list_expression_parses() -> None:
    """A ``shnex:ListExpression`` is an RDF list of constants (literals/IRIs)."""
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values () .
        """
    )
    assert parse_node_expr(graph, prop) == ConstantNodeExpr(RDF.nil)


def test_shnex_list_member_expression_raises() -> None:
    """List members must be constants — nested expressions are not part of
    the supported subset (the spec table requires literal or IRI members)."""
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values ( "sweet" [ shnex:pathValues ex:taste ] ) .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shnex:ListExpression.*literal or IRI"
    ):
        parse_node_expr(graph, prop)


def test_shnex_list_malformed_termination_raises() -> None:
    graph, prop = graph_with_values(
        """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
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
    graph, prop = graph_with_values(
        """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
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
    graph, prop = graph_with_values(
        """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:prop a sh:PropertyShape ;
            sh:values _:head .
        _:head rdf:first "sweet" ; rdf:rest _:head .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="cyclic rdf:rest"):
        parse_node_expr(graph, prop)


def test_shnex_list_duplicate_first_raises() -> None:
    """A duplicate ``rdf:first`` on a *chain* cell rejects in the list walk;
    on the head cell the key-parameter model catches it first ("more than once")."""
    graph, prop = graph_with_values(
        """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:prop a sh:PropertyShape ;
            sh:values _:head .
        _:head rdf:first "sweet" ; rdf:rest _:tail .
        _:tail rdf:first "sour" , "dry" ; rdf:rest () .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"exactly one rdf:first and one rdf:rest"
    ):
        parse_node_expr(graph, prop)
