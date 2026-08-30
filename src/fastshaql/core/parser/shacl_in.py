"""Parse ``sh:in`` value lists on property shapes (SHACL §7.9.3).

See: https://www.w3.org/TR/shacl12-core/#in
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import BNode, Literal, URIRef

from .util import SH_IN, rdf_list

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

logger = logging.getLogger(__name__)


class UnsupportedShaclInError(ValueError):
    """Raised when ``sh:in`` cannot be mapped to a GraphQL enum."""


def parse_shacl_in(
    graph: Graph,
    prop_shape: Node,
) -> tuple[Node, ...] | None:
    """Parse ``sh:in`` on a property shape into raw rdflib terms.

    Args:
        graph: SHACL shapes graph.
        prop_shape: Property shape resource.

    Returns:
        Homogeneous tuple of terms when ``sh:in`` is present, else ``None``.

    Raises:
        UnsupportedShaclInError: On invalid lists (mixed kind, blank nodes,
            or duplicate ``sh:in``). Mangled-name collisions are not an error
            — they are disambiguated downstream
            (:func:`~fastshaql.core.identifiers.enum_member_names`).

    Warns:
        When the list contains duplicate terms — SHACL-legal (membership is
            duplicate-insensitive) but the generated enum will expose distinct
            names mapping to one value; serialization uses the first.
    """
    in_heads = list(graph.objects(prop_shape, SH_IN))
    if not in_heads:
        return None
    if len(in_heads) > 1:
        raise UnsupportedShaclInError(
            f"Property shape {prop_shape} has more than one sh:in"
        )

    members = rdf_list(graph, in_heads[0])
    terms: list[Node] = []
    first_kind: type[URIRef] | type[Literal] | None = None
    for term in members:
        if isinstance(term, BNode):
            raise UnsupportedShaclInError(
                f"sh:in list on {prop_shape} contains a blank node member"
            )
        if isinstance(term, (URIRef, Literal)):
            term_kind = type(term)
        else:
            raise UnsupportedShaclInError(
                f"sh:in list on {prop_shape} contains unsupported term {term!r}"
            )  # pragma: no cover — graph nodes are only URIRef/BNode/Literal
        if first_kind is None:
            first_kind = term_kind
        elif first_kind is not term_kind:
            raise UnsupportedShaclInError(
                f"sh:in list on {prop_shape} mixes literals and IRIs"
            )
        terms.append(term)

    if not terms:
        return None

    result = tuple(terms)
    seen: set[Node] = set()
    duplicates: set[str] = {
        term.n3() for term in result if term in seen or seen.add(term)
    }
    if duplicates:
        logger.warning(
            "Duplicate sh:in members on %s: %s — enum members get distinct "
            "names mapping to one value; serialization uses the first",
            prop_shape,
            ", ".join(sorted(duplicates)),
        )
    return result
