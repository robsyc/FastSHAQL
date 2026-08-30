"""SHACL 1.2 node-expression IR — the value of ``sh:values`` (ADR-0015).

A closed-sum typed union mirroring :mod:`fastshaql.core.ir.shacl_path`. The
union spans the SHACL-SPARQL escape tier (``sh:select``, ``sh:sparqlExpr``,
constants) and the ``shnex:`` algebra (ADR-0015 — ``pathValues``,
``filterShape``, ``if``, ``exists``, ``ListExpression``), extended additively.
This module is inert data plus the shared structural predicate
:func:`is_multivalued_capable` (mirroring ``iter_path_predicates`` beside the
path sum); parsing lives in ``core/parser/node_expr/parse.py`` and emission in
``core/translation/node_expr.py``.

See:
- https://www.w3.org/TR/shacl12-node-expr/#ConstantNodeExpression
- https://www.w3.org/TR/shacl12-node-expr/#IfExpression
- https://www.w3.org/TR/shacl12-node-expr/#ExistsExpression
- https://www.w3.org/TR/shacl12-sparql/#SelectExpression
- https://www.w3.org/TR/shacl12-sparql/#SPARQLExprExpression
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, assert_never

if TYPE_CHECKING:
    from rdflib import Literal, URIRef

    from .filter_shape import FilterShapeIR
    from .shacl_path import ShaclPropertyPath


@dataclasses.dataclass(frozen=True)
class ConstantNodeExpr:
    """A static IRI or literal node expression (node-expr §3.1)."""

    value: URIRef | Literal
    """The constant term. §3.1's third kind, the triple term (§3.1.3), is out
    of scope — RDF 1.2 triple terms have no GraphQL projection."""


@dataclasses.dataclass(frozen=True)
class SelectNodeExpr:
    """A ``sh:select`` node expression (shacl12-sparql §6.1)."""

    body: str
    """The author's WHERE body with prefixes expanded at parse time (ADR-0015)
    and ``$this`` left intact (substituted with the focus variable at translation)."""

    projection_var: str
    """The single projected variable, extracted by string-scanning the SELECT head."""


@dataclasses.dataclass(frozen=True)
class SparqlExprNodeExpr:
    """A ``sh:sparqlExpr`` node expression (shacl12-sparql §6.2)."""

    expr: str
    """The author's SPARQL expression with ``$this`` left intact (substituted with
    the focus variable at translation). Emitted as ``BIND(expr AS ?var)`` at the
    enclosing scope — a documented deviation from the spec's ``SELECT (expr AS
    ?result) WHERE {}`` wrapper (see ADR-0015 *Emission portability*)."""


@dataclasses.dataclass(frozen=True)
class PathValuesNodeExpr:
    """A ``shnex:pathValues`` node expression (node-expr §4.1.4).

    Values of *path* evaluated at the focus node (or at the constant
    *focus_node* — constant IRIs only (ADR-0015): the
    spec's fail-on-multi-member
    focus would silently row-multiply under flat lowering)."""

    path: ShaclPropertyPath
    """Full SHACL path grammar (predicate, inverse, sequence, alternative, modifiers)."""

    focus_node: URIRef | None = None
    """Constant focus-node IRI (``shnex:focusNode``); ``None`` = the enclosing focus."""


@dataclasses.dataclass(frozen=True)
class FilterShapeNodeExpr:
    """A ``shnex:filterShape`` node expression (node-expr §4.2.5).

    The candidate values of *nodes* that conform to *shape* — lowered to the
    boolean single-value-node constraint subset (ADR-0015)."""

    nodes: NodeExprIR
    """Candidate-value expression (``shnex:nodes`` sibling parameter)."""

    shape: FilterShapeIR
    """The lowerable conjunct set; unknown constraints rejected at parse time."""


@dataclasses.dataclass(frozen=True)
class ConstantListNodeExpr:
    """A ``shnex:ListExpression`` — an RDF list of constants (node-expr §4.1.3).

    The expression *is* the list: ``rdf:first`` is the key parameter and
    ``rdf:rest`` chains to ``rdf:nil``. Members are literals or IRIs only —
    the spec table admits no nested expressions, so fastshaql matches it exactly.
    """

    values: tuple[URIRef | Literal, ...]
    """List members in declaration order (at least one — bare ``rdf:nil``
    parses as an IRI constant instead)."""


@dataclasses.dataclass(frozen=True)
class InstancesOfNodeExpr:
    """A ``shnex:instancesOf`` node expression (node-expr §4.5.1).

    The distinct SHACL instances (subclass-closing) of the given classes.
    The class parameter is parse-time constant-folded: a constant IRI or an
    IRI constant list — arbitrary class expressions reject loudly.
    """

    classes: tuple[URIRef, ...]
    """Folded class IRIs (at least one; declaration order preserved)."""


@dataclasses.dataclass(frozen=True)
class ExistsNodeExpr:
    """A ``shnex:exists`` node expression (node-expr §4.1.5).

    ``( true )`` when *nodes* evaluates to a non-empty list, else ``( false )``.
    """

    inner: NodeExprIR
    """The inner expression whose emptiness is tested (the ``shnex:exists``
    object itself — the function declares no parameters, node-expr §4.1.5)."""


@dataclasses.dataclass(frozen=True)
class IfNodeExpr:
    """An ``shnex:if`` node expression (node-expr §4.1.6).

    *then* is chosen when the condition output is exactly the list
    ``( true )``; *otherwise* covers every other output — a list identity
    test, not SPARQL truthiness. fastshaql narrows the spec by restricting
    conditions to statically single-valued expressions: the spec permits a
    set-valued condition (any non-``( true )`` output simply takes the else
    branch), but a flat lowering binds it per row, so rows within one focus
    node would take different branches (ADR-0015).
    """

    cond: NodeExprIR
    """Statically single-valued condition (``shnex:exists``, constants,
    ``sh:sparqlExpr``, nested ``shnex:if``)."""

    then: NodeExprIR | None
    """Branch evaluated when the condition output is exactly ``( true )``."""

    otherwise: NodeExprIR | None
    """Branch evaluated in all other cases (``shnex:else``). At least one of
    *then* / *otherwise* is present (spec syntax rule)."""


type NodeExprIR = (
    ConstantNodeExpr
    | ConstantListNodeExpr
    | SelectNodeExpr
    | SparqlExprNodeExpr
    | PathValuesNodeExpr
    | FilterShapeNodeExpr
    | ExistsNodeExpr
    | IfNodeExpr
    | InstancesOfNodeExpr
)
"""Closed-sum node-expression IR carried by :attr:`PropertyShapeIR.values_expr`
and :attr:`NodeShapeIR.target_expr`."""


def is_multivalued_capable(ir: NodeExprIR) -> bool:
    """Whether a node-expression arm can yield more than one value.

    Pure structural knowledge over the closed union, shared by the parser's
    list-cardinality boundary and the translator's ``shnex:if`` form choice.
    Multi-valued: ``sh:select`` (multi-row merge), ``shnex:pathValues``
    (multi-valued path), ``shnex:ListExpression`` (member list),
    ``shnex:instancesOf`` (a node set), ``shnex:filterShape`` and
    ``shnex:if`` (inherit their widest arm).
    Single-valued: constants, ``sh:sparqlExpr``, ``shnex:exists``.

    Exhaustive by construction: an unlisted arm is a loud ``assert_never``
    failure, not a silent single-valued fall-through — the closed union's
    consumers (this predicate, :func:`is_total`, ``arm_label``,
    ``reject_derived_path_targets``, the translator dispatcher) all fail
    loudly on a forgotten arm.
    """
    match ir:
        case (
            SelectNodeExpr()
            | PathValuesNodeExpr()
            | ConstantListNodeExpr()
            | InstancesOfNodeExpr()
        ):
            return True
        case FilterShapeNodeExpr(nodes=nodes):
            return is_multivalued_capable(nodes)
        case IfNodeExpr(then=then, otherwise=otherwise):
            return any(
                is_multivalued_capable(branch)
                for branch in (then, otherwise)
                if branch is not None
            )
        case ConstantNodeExpr() | SparqlExprNodeExpr() | ExistsNodeExpr():
            return False
        case _ as unreachable:
            assert_never(unreachable)  # pragma: no mutate


def is_total(ir: NodeExprIR) -> bool:
    """Whether the lowering always binds a value and never errors at
    evaluation — the ``shnex:if`` error-routing flag (ADR-0015's
    else-on-error deviation): a total condition needs no ``COALESCE`` guard.

    Only ``shnex:exists`` qualifies today (SPARQL §17.4.1.4: ``EXISTS``
    returns true or false — inner failures swallowed into that boolean);
    every value-producing arm can error (e.g. a comparison on an unbound
    variable). Unlike :func:`is_multivalued_capable` this is single-level
    knowledge: totality of an ``shnex:if`` over total operands is decided
    at its own arm, not by recursing.

    Exhaustive by construction, like the sibling predicate — a new total
    arm must be added here and in the two translator consulters
    (``_condition`` / ``_materialized_condition``) or the match fails loudly.
    """
    match ir:
        case ExistsNodeExpr():
            return True
        case (
            ConstantNodeExpr()
            | ConstantListNodeExpr()
            | SelectNodeExpr()
            | SparqlExprNodeExpr()
            | PathValuesNodeExpr()
            | FilterShapeNodeExpr()
            | InstancesOfNodeExpr()
            | IfNodeExpr()
        ):
            return False
        case _ as unreachable:
            assert_never(unreachable)  # pragma: no mutate
