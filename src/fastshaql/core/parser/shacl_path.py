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
from fastshaql.core.parser.util import rdf_list

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

# sh: predicate → IR node constructor. Each modifier takes its single operand path.
_MODIFIERS = (
    (SH.zeroOrMorePath, ZeroOrMorePath),
    (SH.oneOrMorePath, OneOrMorePath),
    (SH.zeroOrOnePath, ZeroOrOnePath),
)


class UnsupportedShaclPathError(ValueError):
    """Raised when ``sh:path`` uses an unsupported form (e.g. cardinality modifiers)."""


class MissingShaclPathError(ValueError):
    """Raised when a property shape has no ``sh:path``."""


def parse_shacl_path(graph: Graph, prop_shape: Node) -> ShaclPropertyPath:
    """Extract ``sh:path`` from a property shape.

    Raises:
        MissingShaclPathError: When ``sh:path`` is absent.
        UnsupportedShaclPathError: When the path uses unsupported modifiers or malformed RDF lists.
    """
    raw = graph.value(prop_shape, SH.path)
    if raw is None:
        raise MissingShaclPathError(f"Property shape {prop_shape} has no sh:path")
    return parse_shacl_path_node(graph, raw, prop_shape)


def parse_shacl_path_node(graph: Graph, node: Node, source: Node) -> ShaclPropertyPath:
    """Parse an arbitrary node as a SHACL property path (full grammar).

    Used by ``sh:path`` on property shapes and by ``shnex:pathValues`` (the
    value is a well-formed path, not a ``sh:path`` triple).
    """
    if isinstance(node, URIRef):
        return PredicatePath(node)

    for predicate, constructor in _MODIFIERS:
        if (operand := graph.value(node, predicate)) is not None:
            return constructor(parse_shacl_path_node(graph, operand, source))

    if (inverse := graph.value(node, SH.inversePath)) is not None:
        return InversePath(parse_shacl_path_node(graph, inverse, source))

    if (alternative := graph.value(node, SH.alternativePath)) is not None:
        elements = rdf_list(graph, alternative)
        if not elements:
            raise UnsupportedShaclPathError(
                f"Empty sh:path (alternative) RDF list on {source}"
            )
        return AlternativePath(
            tuple(parse_shacl_path_node(graph, element, source) for element in elements)
        )

    if graph.value(node, RDF.first) is not None:
        elements = rdf_list(graph, node)
        if not elements:
            raise UnsupportedShaclPathError(
                f"Empty sh:path (sequence) RDF list on {source}"
            )  # pragma: no cover — rdf:first guard guarantees non-empty list
        return SequencePath(
            tuple(parse_shacl_path_node(graph, element, source) for element in elements)
        )

    raise UnsupportedShaclPathError(
        f"Unrecognized sh:path structure on {source}: {node}"
    )
