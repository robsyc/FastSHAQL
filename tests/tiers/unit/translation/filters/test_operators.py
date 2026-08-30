"""Operator expression emission and folding — ``core/translation/filters/operators.py``.

Unit tier: ``combine_or`` expression folding and ``translate_scalar_ops`` /
``translate_iri_filter`` operator-input translation into the expression AST.

Order: OR folding → scalar operator translation → IRI operator translation.
"""

from __future__ import annotations

from graphql.language.ast import (
    NameNode,
    ObjectFieldNode,
    ObjectValueNode,
    StringValueNode,
)
from rdflib import Literal, Variable

from fastshaql.core.sparql import CompareExpr, FunctionCall, OrExpr, TermExpr
from fastshaql.core.translation.filters.operators import (
    combine_or,
    filter_lhs,
    translate_iri_filter,
    translate_scalar_ops,
)
from support.builders import scalar_property

# --- OR folding ---


def test_combine_or_folds_multiple_expressions() -> None:
    left = CompareExpr("=", TermExpr(Variable("a")), TermExpr(Literal("x")))
    right = CompareExpr("=", TermExpr(Variable("b")), TermExpr(Literal("y")))
    result = combine_or([left, right])
    assert isinstance(result, OrExpr)
    assert result.children == (left, right)


# --- Scalar operator translation ---


def test_translate_scalar_ops_eq() -> None:
    prop = scalar_property("name", min_count=1, max_count=1)
    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="eq"),
                value=StringValueNode(value="Alice"),
            ),
        )
    )
    expr = translate_scalar_ops(node, prop, Variable("name"))
    assert isinstance(expr, CompareExpr)
    assert expr.op == "="


def test_filter_lhs_wraps_str_for_union_properties() -> None:
    """``is_language_typed`` includes the union space — operators on union
    fields get ``STR(?var)`` (valid across both lexical forms; plain values
    pass through ``STR`` unchanged)."""
    from rdflib.namespace import RDF, XSD

    prop = scalar_property(
        "note",
        min_count=0,
        max_count=1,
        datatype=None,
        datatypes=(XSD.string, RDF.langString),
    )
    expr = filter_lhs(prop, Variable("note"))
    assert expr == FunctionCall("STR", (TermExpr(Variable("note")),))


# --- IRI operator translation ---


def test_translate_iri_filter_string_pattern() -> None:
    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="startsWith"),
                value=StringValueNode(value="http://example.org/sa"),
            ),
        )
    )
    expr = translate_iri_filter(node, Variable("iri"))
    assert isinstance(expr, FunctionCall)
    assert expr.render() == 'STRSTARTS(STR(?iri), "http://example.org/sa")'
