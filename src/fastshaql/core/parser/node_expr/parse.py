"""Parse ``sh:values`` node expressions into :class:`NodeExprIR` (ADR-0015).

See:
- https://www.w3.org/TR/shacl12-core/#property-shapes (``sh:values`` attachment)
- https://www.w3.org/TR/shacl12-core/#value-nodes-property-shapes (value-nodes algorithm)
- https://www.w3.org/TR/shacl12-sparql/
- https://www.w3.org/TR/shacl12-node-expr/ (§3.2.1 key-parameter model)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, SH, BNode, Literal, URIRef

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
from fastshaql.core.kernel.identifiers import local_name

from ..errors import UnsupportedShapeError
from ..shacl_path import parse_shacl_path_node
from ..util import (
    SH_SPARQL_EXPR,
    SH_VALUES,
    SHNEX,
    strict_rdf_list,
)
from .filter_shape import parse_filter_shape
from .select_scan import parse_shacl_select
from .semantics import arm_label
from .shacl_prefixes import expand_sparql_prefixes, parse_shacl_prefixes

if TYPE_CHECKING:
    from collections.abc import Callable

    from rdflib import Graph
    from rdflib.term import Node

    from fastshaql.core.ir.filter_shape import FilterShapeIR

    type _KeyFunction = Callable[[Graph, BNode, Node], NodeExprIR]


_DEFERRED_KEY_PARAMS: tuple[URIRef, ...] = (
    SHNEX["var"],
    SHNEX["distinct"],
    SHNEX["intersection"],
    SHNEX["concat"],
    SHNEX["remove"],
    SHNEX["limit"],
    SHNEX["offset"],
    SHNEX["orderBy"],
    SHNEX["flatMap"],
    SHNEX["findFirst"],
    SHNEX["matchAll"],
    SHNEX["count"],
    SHNEX["min"],
    SHNEX["max"],
    SHNEX["sum"],
    SHNEX["nodesMatching"],
    SHNEX["conformsToShape"],
    SHNEX["arg"],
)
"""``shnex:`` operators recognised by name but unsupported (ADR-0015; the
inventory is listed in the node-expressions section of docs/SUPPORT.md).

Entries exist only so the rejection can name the operator. Most are node-expr
§3.2.1 key parameters; ``shnex:conformsToShape`` (§4.5.3) is a list-parameter
property, and ``shnex:arg`` (§6.3) is the key parameter of the named-parameter
``shnex:ArgExpression`` — both are listed for the same naming reason. Shared
auxiliaries (``shnex:then``/``shnex:else``/``shnex:focusNode``/``shnex:nodes``)
are deliberately absent — they identify no function. Promoting an operator =
remove its entry here + add a :data:`_FUNCTIONS` row. Item access
(``SHNEX["count"]``) sidesteps both Python-keyword (``if``) and ``Namespace``
built-in (``count``) clashes.
"""


def _sole_host_object(
    graph: Graph, prop_shape: Node, predicate: URIRef, label: str
) -> Node | None:
    """The sole object of a host predicate (SHACL Core §3.3: at most one)."""
    objs = list(graph.objects(prop_shape, predicate))
    if not objs:
        return None
    if len(objs) > 1:
        raise UnsupportedShapeError(
            f"Property shape {prop_shape} has more than one {label} (SHACL Core §3.3 requires at most one)"
        )
    return objs[0]


def parse_node_expr(graph: Graph, prop_shape: Node) -> NodeExprIR | None:
    """Parse ``sh:values`` on a property shape.

    Args:
        graph: SHACL shapes graph.
        prop_shape: Property shape resource.

    Returns:
        Parsed node expression, or ``None`` when ``sh:values`` is absent.

    Raises:
        UnsupportedShapeError: On unsupported or ill-formed node expressions,
            including more than one ``sh:values`` (SHACL Core §3.3: at most one).
    """
    obj = _sole_host_object(graph, prop_shape, SH_VALUES, "sh:values")
    return parse_expr_object(graph, obj) if obj is not None else None


def parse_default_value(graph: Graph, prop_shape: Node) -> NodeExprIR | None:
    """Parse ``sh:defaultValue`` on a property shape (SHACL Core §3.3).

    The value-nodes step-3 fallback (core §6.8.2): fires only when the path
    and ``sh:values`` yield nothing. Hosts any well-formed node expression;
    the scalar-only boundary (single value, ``sh:datatype``, no relationship
    anchor) is enforced by the caller like ``sh:values``' boundary.

    Args:
        graph: SHACL shapes graph.
        prop_shape: Property shape resource.

    Returns:
        Parsed node expression, or ``None`` when ``sh:defaultValue`` is absent.

    Raises:
        UnsupportedShapeError: On more than one ``sh:defaultValue``
            (SHACL Core §3.3: at most one) or an ill-formed node expression.
    """
    obj = _sole_host_object(graph, prop_shape, SH.defaultValue, "sh:defaultValue")
    return parse_expr_object(graph, obj) if obj is not None else None


def parse_expr_object(graph: Graph, obj: Node) -> NodeExprIR:
    """Parse an expression object: a constant term or an expression blank node.

    Uniform closed sum (ADR-0016): every :class:`NodeExprIR` arm accepted at
    ``sh:values`` is accepted at any host position (``sh:targetNode``), where
    the expression evaluates with the shape as focus node (Core §3.1.3.1).
    """
    if isinstance(obj, (URIRef, Literal)):
        return ConstantNodeExpr(obj)
    if isinstance(obj, BNode):
        return _parse_values_blank_node(graph, obj)
    raise UnsupportedShapeError(
        f"unsupported node expression object {obj!r}"
    )  # pragma: no cover — rdflib nodes are only URIRef/BNode/Literal, all handled above


def _parse_values_blank_node(graph: Graph, node: BNode) -> NodeExprIR:
    key_param, value = _sole_key_parameter(graph, node)
    _, parse_function = _FUNCTIONS[key_param]
    return parse_function(graph, node, value)


def _sole_key_parameter(graph: Graph, node: BNode) -> tuple[URIRef, Node]:
    """Enforce the key-parameter model (node-expr §3.2.1 + §4 preamble).

    §3.2.1 gives each named-parameter function one key parameter that uniquely
    identifies it; §4's preamble adds that such a blank node is well-formed
    only when it is "not the subject of any other triples" and "none of these
    properties is used more than once". Returns the key parameter and its sole
    value; deferred ``shnex:`` functions and unrecognised nodes get the
    categorised unsupported-message.
    """
    present = {
        key: objects
        for key in _FUNCTIONS
        if (objects := list(graph.objects(node, key)))
    }
    for key, values in present.items():
        if len(values) > 1:
            raise UnsupportedShapeError(
                f"node expression {node} uses key parameter {_qname(graph, key)} "
                "more than once"
            )
    if len(present) > 1:
        names = ", ".join(_qname(graph, key) for key in present)
        raise UnsupportedShapeError(
            f"node expression {node} has more than one key parameter ({names}) — "
            "exactly one function identifier is required"
        )
    if not present:
        raise UnsupportedShapeError(_unsupported_message(graph, node))

    ((key, values),) = present.items()
    declared = _FUNCTIONS[key][0] | {key}
    for predicate in (p for p in graph.predicates(node) if isinstance(p, URIRef)):
        if predicate not in declared:
            raise UnsupportedShapeError(
                f"node expression {node}: {_qname(graph, predicate)} is not a "
                f"parameter of the {_qname(graph, key)} function"
            )
        if predicate != key and len(list(graph.objects(node, predicate))) > 1:
            raise UnsupportedShapeError(
                f"node expression {node} uses parameter {_qname(graph, predicate)} "
                "more than once"
            )
    return key, values[0]


def _qname(graph: Graph, iri: URIRef) -> str:
    """Render *iri* as a prefixed name (rdflib generates ``nsN:`` otherwise)."""
    prefix, _, local = graph.compute_qname(iri)
    return f"{prefix}:{local}"


def _expanded_sparql(graph: Graph, expr_node: BNode, text: Node) -> str:
    """Author SPARQL text with the node's ``sh:prefixes`` declarations expanded."""
    return expand_sparql_prefixes(str(text), parse_shacl_prefixes(graph, expr_node))


def _parse_sparql_expr(
    graph: Graph, expr_node: BNode, expr: Node
) -> SparqlExprNodeExpr:
    """Parse ``sh:sparqlExpr`` (shacl12-sparql §6.2)."""
    return SparqlExprNodeExpr(_expanded_sparql(graph, expr_node, expr))


def _parse_select(graph: Graph, expr_node: BNode, query: Node) -> SelectNodeExpr:
    """Parse ``sh:select`` (shacl12-sparql §6.1)."""
    body, projection_var = parse_shacl_select(_expanded_sparql(graph, expr_node, query))
    return SelectNodeExpr(body=body, projection_var=projection_var)


def _parse_exists(graph: Graph, expr_node: BNode, inner_obj: Node) -> ExistsNodeExpr:
    """Parse ``shnex:exists`` (node-expr §4.1.5)."""
    del expr_node
    return ExistsNodeExpr(inner=parse_expr_object(graph, inner_obj))


def _parse_path_values(
    graph: Graph, expr_node: BNode, path_node: Node
) -> PathValuesNodeExpr:
    path = parse_shacl_path_node(graph, path_node, expr_node)
    focus = graph.value(expr_node, SHNEX["focusNode"])
    if focus is not None and not isinstance(focus, URIRef):
        raise UnsupportedShapeError(
            f"shnex:focusNode on {expr_node} must be a constant IRI "
            "(non-constant focus expressions are not supported)"
        )
    return PathValuesNodeExpr(path=path, focus_node=focus)


def _parse_filter_shape_expr(
    graph: Graph, expr_node: Node, shape_node: Node
) -> NodeExprIR:
    """Parse ``shnex:filterShape`` + ``shnex:nodes`` (node-expr §4.2.5)."""
    nodes_obj = graph.value(expr_node, SHNEX["nodes"])
    if nodes_obj is None:
        raise UnsupportedShapeError(
            f"shnex:filterShape on {expr_node} requires a shnex:nodes parameter"
        )
    return _filtered(
        parse_expr_object(graph, nodes_obj), parse_filter_shape(graph, shape_node)
    )


def _filtered(nodes: NodeExprIR, shape: FilterShapeIR) -> NodeExprIR:
    """Apply *shape* to *nodes*, distributing through ``shnex:if`` branches.

    A filter over an ``shnex:if`` is normalised to an ``if`` over two filtered
    branches: the condition never reads the candidate values, so filtering
    distributes over branch selection. This keeps the post-invariant that
    :attr:`FilterShapeNodeExpr.nodes` is never an ``shnex:if`` — the one arm
    that lowers to conditioned ``OPTIONAL``s. Without it the conjuncts would
    be emitted *after* the arms that bind the candidate variable, so a focus
    node matching neither branch would admit every candidate in the graph.
    """
    if isinstance(nodes, IfNodeExpr):
        return IfNodeExpr(
            cond=nodes.cond,
            then=None if nodes.then is None else _filtered(nodes.then, shape),
            otherwise=(
                None if nodes.otherwise is None else _filtered(nodes.otherwise, shape)
            ),
        )
    return FilterShapeNodeExpr(nodes=nodes, shape=shape)


def _parse_if(graph: Graph, expr_node: BNode, cond_obj: Node) -> IfNodeExpr:
    """Parse ``shnex:if``/``shnex:then``/``shnex:else`` (node-expr §4.1.6).

    Conditions are narrowed to statically single-valued expressions. The spec
    permits a set-valued condition — any output other than ``( true )`` takes
    the else branch — but a flat lowering binds it per row, so rows within one
    focus node would take different branches (ADR-0015).
    """
    cond = parse_expr_object(graph, cond_obj)
    if is_multivalued_capable(cond):
        raise UnsupportedShapeError(
            f"shnex:if condition on {expr_node} uses {arm_label(cond)} — conditions "
            "must be statically single-valued expressions (shnex:exists, constants, "
            "sh:sparqlExpr, nested shnex:if)"
        )
    then_obj = graph.value(expr_node, SHNEX["then"])
    else_obj = graph.value(expr_node, SHNEX["else"])
    if then_obj is None and else_obj is None:
        raise UnsupportedShapeError(
            f"shnex:if on {expr_node} requires at least one of shnex:then or shnex:else"
        )
    return IfNodeExpr(
        cond=cond,
        then=None if then_obj is None else parse_expr_object(graph, then_obj),
        otherwise=None if else_obj is None else parse_expr_object(graph, else_obj),
    )


def _parse_constant_list(
    graph: Graph, list_node: BNode, first_obj: Node
) -> ConstantListNodeExpr:
    """Parse a ``shnex:ListExpression`` — an RDF list of constant members.

    Members must be literals or IRIs (the spec table admits nothing else);
    the list itself must be well-formed (:func:`strict_rdf_list`).
    """
    del first_obj  # the walk below re-reads rdf:first per cons cell
    members = strict_rdf_list(
        graph, list_node, what=f"shnex:ListExpression on {list_node}"
    )
    constants: list[URIRef | Literal] = []
    for member in members:
        if not isinstance(member, (URIRef, Literal)):
            raise UnsupportedShapeError(
                f"shnex:ListExpression on {list_node} requires literal or IRI "
                f"members (got {member} — nested expressions in lists are "
                "not supported)"
            )
        constants.append(member)
    return ConstantListNodeExpr(tuple(constants))


def _parse_instances_of(
    graph: Graph, expr_node: BNode, value: Node
) -> InstancesOfNodeExpr:
    """Parse ``shnex:instancesOf`` (node-expr §4.5.1) — constant folding.

    The spec accepts any node expression returning the class(es); fastshaql
    folds constants only — a constant IRI or an IRI constant list — and
    rejects arbitrary class expressions loudly.
    """
    expr = parse_expr_object(graph, value)
    match expr:
        case ConstantNodeExpr(value=URIRef() as single):
            return InstancesOfNodeExpr(classes=(single,))
        case ConstantListNodeExpr(values=values) if all(
            isinstance(v, URIRef) for v in values
        ):
            return InstancesOfNodeExpr(
                classes=tuple(v for v in values if isinstance(v, URIRef))
            )
    raise UnsupportedShapeError(
        f"shnex:instancesOf on {expr_node} requires a constant class IRI or an "
        "IRI list — arbitrary class expressions are not supported"
    )


_FUNCTIONS: dict[URIRef, tuple[frozenset[URIRef], _KeyFunction]] = {
    SH_SPARQL_EXPR: (frozenset({SH.prefixes}), _parse_sparql_expr),
    SH.select: (frozenset({SH.prefixes}), _parse_select),
    SHNEX["pathValues"]: (frozenset({SHNEX["focusNode"]}), _parse_path_values),
    SHNEX["filterShape"]: (frozenset({SHNEX["nodes"]}), _parse_filter_shape_expr),
    SHNEX["if"]: (frozenset({SHNEX["then"], SHNEX["else"]}), _parse_if),
    SHNEX["exists"]: (frozenset(), _parse_exists),
    SHNEX["instancesOf"]: (frozenset(), _parse_instances_of),
    RDF.first: (frozenset({RDF.rest}), _parse_constant_list),
}
"""Supported node-expression functions: key parameter → (declared parameters, parser).

The key-parameter model (node-expr §3.2.1, §4 preamble) and the dispatch share
one table, so a supported function cannot be declared without an arm to parse
it. Promoting a deferred operator = drop its ``_DEFERRED_KEY_PARAMS`` entry and
add a row here. ``shnex:ListExpression`` names no key parameter in the spec —
fastshaql dispatches on ``rdf:first`` (bold-mandatory in the §4.1.3 table);
``rdf:rest`` is required on every cons cell by the well-formed-list
requirement (§4.1.3 + core §1.1).
"""


def _unsupported_message(graph: Graph, node: BNode) -> str:
    """Categorise an unrecognised node-expression blank node for the error.

    Names the deferred ``shnex:`` operator when one is present; a bare ``[]``
    (the spec's empty expression, node-expr §4.1.1) names itself; orphan
    ``shnex:`` auxiliaries and non-``shnex:`` blanks (``sparql:`` functions,
    custom functions) name the predicates they carry.

    The deferred scan reads *every* predicate and walks
    :data:`_DEFERRED_KEY_PARAMS` in declaration order, so the operator is named
    even when a shared auxiliary (``shnex:nodes``) sits on the same node —
    RDF predicate order is arbitrary and must not decide the message.
    """
    predicates = {p for p in graph.predicates(node) if isinstance(p, URIRef)}
    deferred = next((p for p in _DEFERRED_KEY_PARAMS if p in predicates), None)
    if deferred is not None:
        return f"shnex:{local_name(deferred)} node expressions are not supported (on {node})"
    names = ", ".join(sorted(str(p) for p in predicates))
    if not predicates:
        return f"empty node expression {node} (node-expr §4.1.1) is not supported"
    if any(p in SHNEX for p in predicates):
        return (
            f"unsupported shnex: node expression on {node} "
            f"(carries {names}; no recognised key parameter)"
        )
    return (
        f"unsupported node expression on {node} (carries {names}) — "
        "expected sh:select, sh:sparqlExpr, or a shnex: function"
    )
