"""Parse ``sh:path`` on property shapes into :class:`ShaclPropertyPath` variants.

See: https://www.w3.org/TR/shacl12-core/#property-paths

Supports predicate, inverse, sequence, alternative paths, and the three
cardinality modifiers (``sh:zeroOrMorePath`` / ``sh:oneOrMorePath`` / ``sh:zeroOrOnePath``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, SH, URIRef

from fastshaql.core.ir.shacl_path import (
    AlternativePath,
    InversePath,
    OneOrMorePath,
    PredicatePath,
    SequencePath,
    ShaclPropertyPath,
    ZeroOrMorePath,
    ZeroOrOnePath,
)
from fastshaql.core.parser.util import sole_object, strict_rdf_list

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

# sh: name → predicate → IR constructor. Each modifier takes its single operand path.
_MODIFIERS = (
    ("sh:zeroOrMorePath", SH.zeroOrMorePath, ZeroOrMorePath),
    ("sh:oneOrMorePath", SH.oneOrMorePath, OneOrMorePath),
    ("sh:zeroOrOnePath", SH.zeroOrOnePath, ZeroOrOnePath),
)

# §4 syntax predicates beyond the predicate-path form (IRIs take that branch).
_PATH_PREDICATES = (
    SH.inversePath,
    SH.alternativePath,
    RDF.first,
    *(predicate for _, predicate, _ in _MODIFIERS),
)

# §4.2/§4.3: sequence and alternative path lists carry at least two members.
_MIN_PATH_LIST_MEMBERS = 2


class UnsupportedShaclPathError(ValueError):
    """Raised when ``sh:path`` uses an unsupported form (e.g. cardinality modifiers)."""


class MissingShaclPathError(ValueError):
    """Raised when a property shape has no ``sh:path``."""


def _strict_path_list(
    graph: Graph,
    head: Node,
    *,
    what: str,
    section: str,
    source: Node,
    nested: frozenset[Node],
) -> tuple[ShaclPropertyPath, ...]:
    """The path list at *head*, members parsed as paths — strict walk,
    at least two members.

    *what* names the list and *section* the spec rule (§4.2/§4.3) in errors;
    *source* is the declaring property shape and *nested* the cycle guard.
    """
    elements = strict_rdf_list(graph, head, what=f"{what} on {source}")
    if len(elements) < _MIN_PATH_LIST_MEMBERS:
        raise UnsupportedShaclPathError(
            f"{what} on {source} needs at least two members "
            f"(SHACL {section}), got {len(elements)}"
        )
    return tuple(
        parse_shacl_path_node(graph, element, source, ancestors=nested)
        for element in elements
    )


def parse_shacl_path(graph: Graph, prop_shape: Node) -> ShaclPropertyPath:
    """Extract ``sh:path`` from a property shape.

    Raises:
        MissingShaclPathError: When ``sh:path`` is absent.
        UnsupportedShapeError: When the shape carries more than one
            ``sh:path`` (§3.3 allows at most one).
        UnsupportedShaclPathError: When the path uses unsupported modifiers or malformed RDF lists.
    """
    path_node = sole_object(graph, prop_shape, SH.path, what="sh:path")
    if path_node is None:
        raise MissingShaclPathError(f"Property shape {prop_shape} has no sh:path")
    return parse_shacl_path_node(graph, path_node, prop_shape)


def parse_shacl_path_node(
    graph: Graph,
    node: Node,
    source: Node,
    *,
    ancestors: frozenset[Node] = frozenset(),
) -> ShaclPropertyPath:
    """Parse an arbitrary node as a SHACL property path (full grammar).

    Used by ``sh:path`` on property shapes and by ``shnex:pathValues`` (the
    value is a well-formed path, not a ``sh:path`` triple). *ancestors*
    carries the blank-node path mappings being expanded — a path that
    references itself is ill-formed (§4) and rejects here instead of
    recursing to a ``RecursionError``.

    Raises:
        UnsupportedShaclPathError: On an empty list, a cyclic path, a
            sequence/alternative list with fewer than two members (§4.2/§4.3),
            a node carrying several path predicates (§4's exactly-one rule),
            or an unrecognized structure.
        UnsupportedShapeError: On a malformed RDF list (strict walk) or
            several values of one wrapper predicate.
    """
    if node in ancestors:
        raise UnsupportedShaclPathError(
            f"Cyclic property path on {source}: {node} is its own path "
            "operand (SHACL §4 requires acyclic paths)"
        )
    if node == RDF.nil:
        # An empty list *is* rdf:nil, an IRI — without this check the
        # predicate branch would win and silently parse a `nil` field.
        raise UnsupportedShaclPathError(
            f"Empty sh:path (sequence) RDF list on {source}"
        )
    if isinstance(node, URIRef):
        return PredicatePath(node)

    present = [p for p in _PATH_PREDICATES if graph.value(node, p) is not None]
    if len(present) > 1:
        raise UnsupportedShaclPathError(
            f"Path node {node} on {source} carries several §4 path "
            "predicates — exactly one syntax rule must apply"
        )

    nested = ancestors | {node}
    for name, predicate, constructor in _MODIFIERS:
        if (operand := sole_object(graph, node, predicate, what=name)) is not None:
            return constructor(
                parse_shacl_path_node(graph, operand, source, ancestors=nested)
            )

    if (
        inverse := sole_object(graph, node, SH.inversePath, what="sh:inversePath")
    ) is not None:
        return InversePath(
            parse_shacl_path_node(graph, inverse, source, ancestors=nested)
        )

    if (
        alternative := sole_object(
            graph, node, SH.alternativePath, what="sh:alternativePath"
        )
    ) is not None:
        return AlternativePath(
            _strict_path_list(
                graph,
                alternative,
                what="sh:alternativePath list",
                section="§4.3",
                source=source,
                nested=nested,
            )
        )

    if graph.value(node, RDF.first) is not None:
        return SequencePath(
            _strict_path_list(
                graph,
                node,
                what="sh:path sequence list",
                section="§4.2",
                source=source,
                nested=nested,
            )
        )

    raise UnsupportedShaclPathError(
        f"Unrecognized sh:path structure on {source}: {node}"
    )
