"""Parse shape target declarations — ``sh:target*`` (ADR-0016).

One target declaration per shape: ``sh:targetClass`` XOR exactly one
``sh:targetNode`` expression XOR an implicit class target (Core §3.1.3.3 — a
shape typed ``rdfs:Class``/``sh:ShapeClass`` targets the SHACL instances of
its own IRI). The spec (Core §3.1.3) unions all declarations; that union is a
named narrowing — rejected loudly, never silently ignored — with the widening
pre-staged in ADR-0015 (``UnionPattern``).

See: https://www.w3.org/TR/shacl12-core/#targets
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, RDFS, SH, URIRef

from fastshaql.core.ir.node_expr import InstancesOfNodeExpr, NodeExprIR
from fastshaql.core.kernel.identifiers import local_name

from .errors import UnsupportedShapeError
from .node_expr import parse_expr_object
from .util import SH_NS, SH_SHAPE, SH_SHAPE_CLASS, SH_TARGET_WHERE

if TYPE_CHECKING:
    from rdflib import Graph

_ONE_DECLARATION = (
    "exactly one target declaration per shape is supported "
    "(spec unions all declarations)"
)
"""The named-narrowing policy tail shared by every one-per-shape rejection."""

_UNSUPPORTED_TARGET_PREDICATES: tuple[URIRef, ...] = (
    SH.targetObjectsOf,
    SH.targetSubjectsOf,
    SH_TARGET_WHERE,
)
"""Target predicates fastshaql cannot lower (ADR-0016 decision 1)."""

_KNOWN_TARGET_PREDICATES = frozenset(
    (SH.targetClass, SH.targetNode, *_UNSUPPORTED_TARGET_PREDICATES)
)


def _unsupported_target(shape_iri: URIRef, predicate: URIRef) -> UnsupportedShapeError:
    """The shared unsupported-target rejection, naming the predicate."""
    return UnsupportedShapeError(
        f"{shape_iri} declares unsupported target {predicate} — "
        "only sh:targetClass, sh:targetNode, and implicit class "
        "targets are supported"
    )


def _reject_unsupported(graph: Graph, shape_iri: URIRef) -> None:
    """Raise naming the first unsupported or unrecognized target on *shape_iri*.

    The three spec predicates reject by name; any other ``sh:target*``
    predicate (SHACL 1.1's ``sh:target``, typos, future spec additions)
    rejects by scan — the loud-rejection stance admits no silently dropped
    target declaration.
    """
    for predicate in _UNSUPPORTED_TARGET_PREDICATES:
        if graph.value(shape_iri, predicate) is not None:
            raise _unsupported_target(shape_iri, predicate)
    if graph.value(shape_iri, SH_SHAPE) is not None:
        raise UnsupportedShapeError(
            f"{shape_iri} carries sh:shape — sh:shape targets are declared in "
            "the data graph (Core §3.1.3.7), invisible to a shapes-graph "
            "parser and not supported"
        )
    for predicate in graph.predicates(shape_iri):
        if (
            isinstance(predicate, URIRef)
            and str(predicate).startswith(SH_NS)
            and local_name(predicate).lower().startswith("target")
            and predicate not in _KNOWN_TARGET_PREDICATES
        ):
            raise _unsupported_target(shape_iri, predicate)


def _implicit_class_target(
    graph: Graph, shape_iri: URIRef
) -> InstancesOfNodeExpr | None:
    """The implicit class target (Core §3.1.3.3): a shape also typed
    ``rdfs:Class`` or ``sh:ShapeClass`` targets the SHACL instances of its
    own IRI — lowered through the ``shnex:instancesOf`` arm, subclass-closing."""
    types = set(graph.objects(shape_iri, RDF.type))
    if RDFS.Class in types or SH_SHAPE_CLASS in types:
        return InstancesOfNodeExpr(classes=(shape_iri,))
    return None


def _sole_target_class(graph: Graph, shape_iri: URIRef) -> URIRef | None:
    """The single ``sh:targetClass`` value (Core §3.1.3.2)."""
    values = list(graph.objects(shape_iri, SH.targetClass))
    if not values:
        return None
    if len(values) > 1:
        raise UnsupportedShapeError(
            f"{shape_iri} declares {len(values)} sh:targetClass values — "
            f"{_ONE_DECLARATION}"
        )
    (value,) = values
    if not isinstance(value, URIRef):
        raise UnsupportedShapeError(
            f"{shape_iri} declares sh:targetClass {value!r} — values must be IRIs"
        )
    return value


def parse_target(
    graph: Graph, shape_iri: URIRef
) -> tuple[URIRef | None, NodeExprIR | None, bool]:
    """Read the target declaration of a shape (Core §3.1.3).

    Returns:
        ``(target_class, target_expr, implicit_class)`` — at most one of the
        first two is non-``None``. An implicit class target returns
        ``target_expr = InstancesOfNodeExpr((shape_iri,))`` with
        ``implicit_class = True``.

    Raises:
        UnsupportedShapeError: On unsupported or unrecognized target predicates,
            multiple values, or mixed declaration kinds.
    """
    _reject_unsupported(graph, shape_iri)
    implicit = _implicit_class_target(graph, shape_iri)
    target_class = _sole_target_class(graph, shape_iri)
    target_nodes = list(graph.objects(shape_iri, SH.targetNode))
    declared = [
        kind
        for kind, present in (
            ("an implicit class target", implicit is not None),
            ("sh:targetClass", target_class is not None),
            ("sh:targetNode", bool(target_nodes)),
        )
        if present
    ]
    if len(declared) > 1:
        raise UnsupportedShapeError(
            f"{shape_iri} declares {', '.join(declared)} — {_ONE_DECLARATION}"
        )
    if len(target_nodes) > 1:
        raise UnsupportedShapeError(
            f"{shape_iri} declares {len(target_nodes)} sh:targetNode values — "
            f"{_ONE_DECLARATION}"
        )
    if target_nodes:
        (node,) = target_nodes
        return None, parse_expr_object(graph, node), False
    if implicit is not None:
        return None, implicit, True
    return target_class, None, False
