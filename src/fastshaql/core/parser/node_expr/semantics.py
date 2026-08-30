"""Node-expression semantics: labelling and rule-chaining checks.

Union knowledge about :class:`NodeExprIR` that the property-shape boundary
needs before accepting a parsed expression: what to call an arm in error
messages, and whether any path it reads targets another derived property
(rule chaining, rejected per ADR-0015). The structural capability predicate
:func:`is_multivalued_capable` lives beside the IR union it dispatches on
(``core/ir/node_expr.py``) — import it from there directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, assert_never

from rdflib import SH

from fastshaql.core.ir.filter_shape import FilterProperty, FilterShapeIR
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
)
from fastshaql.core.ir.shacl_path import ShaclPropertyPath, iter_path_predicates

from ..errors import UnsupportedShapeError
from ..util import SH_VALUES

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

__all__ = [
    "arm_label",
    "reject_derived_path_targets",
]


def arm_label(ir: NodeExprIR) -> str:
    """The spec term for *ir*, for boundary error messages."""
    label: str
    match ir:
        case ConstantNodeExpr():
            label = "constant"
        case ConstantListNodeExpr():
            label = "shnex:ListExpression"
        case SparqlExprNodeExpr():
            label = "sh:sparqlExpr"
        case SelectNodeExpr():
            label = "sh:select"
        case PathValuesNodeExpr():
            label = "shnex:pathValues"
        case FilterShapeNodeExpr(nodes=nodes):
            return f"shnex:filterShape over {arm_label(nodes)}"
        case ExistsNodeExpr():
            label = "shnex:exists"
        case IfNodeExpr():
            label = "shnex:if"
        case InstancesOfNodeExpr():
            label = "shnex:instancesOf"
        case _ as unreachable:  # pragma: no cover — unreachable: closed union
            assert_never(unreachable)
    return label


def reject_derived_path_targets(
    graph: Graph, ir: NodeExprIR, shape_iri: Node, field_name: str
) -> None:
    """Reject expressions reading another derived property (ADR-0015).

    Spec-permitted rule chaining (node-expr §4.1.4,
    non-normative note): a path may hit a property whose values are themselves
    derived. The lowering reads asserted triples at that position, but a
    derived property's asserted triples are ignored under replace-not-union —
    so chaining would silently produce empty or stale reads. Checked
    recursively through ``shnex:filterShape`` nodes arms and conjunct paths,
    ``shnex:exists`` inner expressions, and ``shnex:if`` conditions/branches.
    """
    match ir:
        case PathValuesNodeExpr(path=path):
            _reject_derived_predicates(graph, path, shape_iri, field_name)
        case FilterShapeNodeExpr(nodes=nodes, shape=shape):
            reject_derived_path_targets(graph, nodes, shape_iri, field_name)
            _reject_derived_conjuncts(graph, shape, shape_iri, field_name)
        case ExistsNodeExpr(inner=inner):
            reject_derived_path_targets(graph, inner, shape_iri, field_name)
        case IfNodeExpr(cond=cond, then=then, otherwise=otherwise):
            reject_derived_path_targets(graph, cond, shape_iri, field_name)
            for branch in (then, otherwise):
                if branch is not None:
                    reject_derived_path_targets(graph, branch, shape_iri, field_name)
        case (
            ConstantNodeExpr()
            | ConstantListNodeExpr()
            | SparqlExprNodeExpr()
            | SelectNodeExpr()
            | InstancesOfNodeExpr()
        ):
            pass  # no IR paths to walk (sh:select is trusted author SPARQL)
        case _ as unreachable:  # pragma: no cover — unreachable: closed union
            assert_never(unreachable)


def _reject_derived_conjuncts(
    graph: Graph, shape: FilterShapeIR, shape_iri: Node, field_name: str
) -> None:
    for conjunct in shape.conjuncts:
        if isinstance(conjunct, FilterProperty):
            _reject_derived_predicates(graph, conjunct.path, shape_iri, field_name)
            _reject_derived_conjuncts(graph, conjunct.nested, shape_iri, field_name)


def _reject_derived_predicates(
    graph: Graph, path: ShaclPropertyPath, shape_iri: Node, field_name: str
) -> None:
    for predicate in iter_path_predicates(path):
        for candidate in graph.subjects(SH.path, predicate):
            if graph.value(candidate, SH_VALUES) is not None:
                raise UnsupportedShapeError(
                    f"derived field {field_name!r} on {shape_iri} reads derived "
                    f"property {predicate} — rule chaining is not supported"
                )
