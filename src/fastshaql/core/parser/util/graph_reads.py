"""Typed reads from an RDFLib ``Graph``.

Helpers for extracting single values (URI, int, string) and list members
from an RDF graph by subject and predicate. Used by the SHACL shape parsers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, SH, XSD, BNode, Literal, URIRef
from rdflib.collection import Collection

from ..errors import UnsupportedShapeError

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node


def object_uri(graph: Graph, subject: Node, predicate: Node) -> URIRef | None:
    """First object of ``(subject, predicate, ?)`` when it is a ``URIRef``."""
    o = graph.value(subject, predicate)
    return o if isinstance(o, URIRef) else None


def object_int(graph: Graph, subject: Node, predicate: Node) -> int | None:
    """First object when it is an ``xsd:integer`` ``Literal`` (e.g. ``sh:minCount``)."""
    o = graph.value(subject, predicate)
    if isinstance(o, Literal) and o.datatype == XSD.integer:
        return int(o)
    return None


def object_str(graph: Graph, subject: Node, predicate: Node) -> str | None:
    """String form of the first object, if any (e.g. ``sh:codeIdentifier``)."""
    o = graph.value(subject, predicate)
    return str(o) if o is not None else None


def is_deactivated(graph: Graph, subject: Node) -> bool:
    """Whether ``sh:deactivated`` is ``true`` on *subject* (SHACL Core §3.1.6).

    Only a boolean ``true`` deactivates; ``false``,
    other values, and absence leave the shape active.
    """
    return graph.value(subject, SH.deactivated) == Literal(True)


def _lang_matches(tag: str | None, preferred: str) -> bool:
    """RFC 4647 basic filtering — ``preferred`` matches ``tag`` as a case-insensitive subtag prefix."""
    if tag is None:
        return False
    t, p = tag.lower(), preferred.lower()
    return t == p or t.startswith(p + "-")


def _pick_localized_literal(literals: list[Literal], lang: str) -> str | None:
    """Select lexical form: preferred language, then untagged, then any (deterministic)."""
    if not literals:
        return None
    ordered = sorted(literals, key=lambda lit: (lit.language or "", str(lit)))
    for lit in ordered:
        if _lang_matches(lit.language, lang):
            return str(lit)
    for lit in ordered:
        if lit.language is None:
            return str(lit)
    return str(ordered[0])


def first_localized_str(
    graph: Graph,
    subject: Node,
    *predicates: Node,
    lang: str = "en",
) -> str | None:
    """First localized string among *predicates* using language preference.

    Within each predicate, selects among all objects in order:
    preferred *lang* (RFC 4647 basic filtering), untagged ``xsd:string``,
    then any other language. Falls through to the next predicate only when
    the current one has no usable value.
    """
    for predicate in predicates:
        literals = [
            o for o in graph.objects(subject, predicate) if isinstance(o, Literal)
        ]
        if (value := _pick_localized_literal(literals, lang)) is not None:
            return value
    return None


def rdf_list(graph: Graph, head: Node) -> list[Node]:
    """Elements of an RDF collection at *head* (``rdf:first``/``rdf:rest`` walk)."""
    return list(Collection(graph, head))


def strict_rdf_list(graph: Graph, head: Node, *, what: str) -> tuple[Node, ...]:
    """Members of a well-formed SHACL list at *head* (Core §1.1).

    Unlike the lenient :func:`rdf_list` (rdflib ``Collection`` — hangs on
    cycles, silently picks one of multiple ``rdf:first`` values), every cons
    cell must be a blank node carrying exactly one ``rdf:first`` and one
    ``rdf:rest``, the chain must terminate at ``rdf:nil``, and cycles reject.
    *what* names the declaration in error messages.

    Raises:
        UnsupportedShapeError: On malformation, naming *what*.
    """
    members: list[Node] = []
    visited: set[Node] = set()
    current: Node = head
    while current != RDF.nil:
        if current in visited:
            raise UnsupportedShapeError(
                f"{what} is not a well-formed SHACL list (cyclic rdf:rest chain)"
            )
        visited.add(current)
        if not isinstance(current, BNode):
            raise UnsupportedShapeError(
                f"{what} is not a well-formed SHACL list "
                f"(rdf:rest target {current} is neither rdf:nil nor a blank node)"
            )
        firsts = list(graph.objects(current, RDF.first))
        rests = list(graph.objects(current, RDF.rest))
        if len(firsts) != 1 or len(rests) != 1:
            raise UnsupportedShapeError(
                f"{what} is not a well-formed SHACL list "
                "(every member needs exactly one rdf:first and one rdf:rest)"
            )
        members.append(firsts[0])
        (current,) = rests
    return tuple(members)
