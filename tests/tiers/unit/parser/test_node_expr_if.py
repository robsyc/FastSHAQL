"""``shnex:if`` / ``shnex:exists`` parsing — ``core/parser/node_expr``.

Unit tier: conditional expressions — the single-valuedness discipline for
conditions (``shnex:exists``, ``sh:sparqlExpr``, nested single-valued
``shnex:if``), optional branches, parameter rules, and bare ``shnex:exists``.
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from fastshaql.core.ir.node_expr import (
    ConstantNodeExpr,
    ExistsNodeExpr,
    IfNodeExpr,
    PathValuesNodeExpr,
    SparqlExprNodeExpr,
)
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.parser.node_expr import UnsupportedShapeError, parse_node_expr
from support.builders import EX, graph_with_values

# --- shnex:if / shnex:exists (ADR-0015) ---


def test_shnex_if_with_exists_condition_parses() -> None:
    """``shnex:if`` with an ``shnex:exists`` condition and constant branches —
    the spec's fill-color shape (node-expr *If Expressions* example)."""
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
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
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [ shnex:exists [ shnex:pathValues ex:child ] ] .
        """
    )
    assert parse_node_expr(graph, prop) == ExistsNodeExpr(
        inner=PathValuesNodeExpr(path=PredicatePath(EX + "child"))
    )


def test_shnex_exists_foreign_parameter_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:exists [ shnex:pathValues ex:child ] ;
                shnex:then "x" ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"shnex:then.*not a parameter"):
        parse_node_expr(graph, prop)
