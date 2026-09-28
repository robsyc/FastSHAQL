"""Unit tests for the node-expression IR structural predicates."""

from typing import cast

import pytest
from rdflib import URIRef

from fastshaql.core.ir.filter_shape import FilterShapeIR
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
    is_row_keeping,
    is_total,
)
from fastshaql.core.ir.shacl_path import PredicatePath

EX = URIRef("http://example.org/ex")


def test_union_predicates_fail_loudly_on_unknown_arm() -> None:
    """The closed ``NodeExprIR`` union's structural predicates raise on an
    unlisted arm (docstring contract: a forgotten arm is a loud
    ``assert_never`` failure, never a silent single-valued fall-through)."""
    intruder = cast("NodeExprIR", object())
    with pytest.raises(AssertionError):
        is_multivalued_capable(intruder)
    with pytest.raises(AssertionError):
        is_total(intruder)
    with pytest.raises(AssertionError):
        is_row_keeping(intruder)


@pytest.mark.parametrize(
    ("ir", "row_keeping"),
    [
        (ConstantNodeExpr(value=EX), False),
        (ConstantListNodeExpr(values=(EX,)), False),
        (PathValuesNodeExpr(path=PredicatePath(EX)), False),
        (InstancesOfNodeExpr(classes=(EX,)), False),
        (ExistsNodeExpr(inner=PathValuesNodeExpr(path=PredicatePath(EX))), False),
        (SparqlExprNodeExpr(expr="$this"), True),
        (SelectNodeExpr(body="$this p ?v", projection_var="v"), True),
        (
            IfNodeExpr(
                cond=ExistsNodeExpr(inner=PathValuesNodeExpr(path=PredicatePath(EX))),
                then=PathValuesNodeExpr(path=PredicatePath(EX)),
                otherwise=None,
            ),
            True,
        ),
        (
            FilterShapeNodeExpr(
                nodes=PathValuesNodeExpr(path=PredicatePath(EX)),
                shape=FilterShapeIR(conjuncts=()),
            ),
            False,
        ),
        (
            FilterShapeNodeExpr(
                nodes=SelectNodeExpr(body="$this p ?v", projection_var="v"),
                shape=FilterShapeIR(conjuncts=()),
            ),
            True,
        ),
    ],
)
def test_is_row_keeping_classifies_every_arm(ir: NodeExprIR, row_keeping: bool) -> None:
    """Row-keeping arms keep a solution with the value unbound (erroring
    ``BIND`` s, unbound-projecting selects, unmatched if branches);
    ``shnex:filterShape`` inherits its ``shnex:nodes`` arm; the rest always
    bind or die with the row."""
    assert is_row_keeping(ir) is row_keeping
