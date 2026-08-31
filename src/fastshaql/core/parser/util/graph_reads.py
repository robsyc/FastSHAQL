"""Typed reads from an RDFLib ``Graph``.

Helpers for extracting single typed values (integers, localized strings,
deactivation flags) and RDF list members from an RDF graph by subject and
predicate. Used by the SHACL shape parsers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, SH, XSD, BNode, Literal

from ..errors import UnsupportedShapeError

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node


def sole_object(
    graph: Graph, subject: Node, predicate: Node, *, what: str
) -> Node | None:
    """The single object of ``(subject, predicate, ?)`` — ``None`` when absent.

    Where the spec allows at most one value, a silent pick among several
    would be nondeterministic. *what* names the declaration in errors.

    Raises:
        UnsupportedShapeError: On multiple values.
    """
    values = list(graph.objects(subject, predicate))
    if len(values) > 1:
        raise UnsupportedShapeError(
            f"Multiple {what} values on {subject} — at most one is allowed"
        )
    return values[0] if values else None


def object_int(
    graph: Graph, subject: Node, predicate: Node, *, what: str
) -> int | None:
    """Sole object of ``(subject, predicate, ?)`` as an ``int`` (e.g. ``sh:minCount``).

    A declared cardinality that silently read as ``None`` would drop the
    field's kind to the optional-list default, so a present-but-malformed
    value rejects loudly instead (SHACL Core §7.2.1 and §7.2.2: at most one
    value, an ``xsd:integer`` literal). *what* names the declaration in
    error messages.

    Raises:
        UnsupportedShapeError: On multiple values (:func:`sole_object`), a
            non-``xsd:integer`` value, or an ill-typed lexical form.
    """
    value = sole_object(graph, subject, predicate, what=what)
    if value is None:
        return None
    if not isinstance(value, Literal) or value.datatype != XSD.integer:
        raise UnsupportedShapeError(
            f"{what} on {subject} must be an xsd:integer literal (SHACL §7.2), got {value!r}"
        )
    try:
        return int(str(value))
    except ValueError:
        raise UnsupportedShapeError(
            f"{what} on {subject} must be an xsd:integer literal (SHACL §7.2), got {value!r}"
        ) from None


def is_deactivated(graph: Graph, subject: Node) -> bool:
    """Whether ``sh:deactivated`` is ``true`` on *subject* (SHACL Core §3.1.6).

    Only a boolean ``true`` deactivates; ``false``, other values, and
    absence leave the shape active. At most one value (§3.1.6) — multiple
    values reject instead of arbitrarily flipping the shape's visibility.
    """
    value = sole_object(graph, subject, SH.deactivated, what="sh:deactivated")
    return value == Literal(True)


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


def strict_rdf_list(graph: Graph, head: Node, *, what: str) -> tuple[Node, ...]:
    """Members of a well-formed SHACL list at *head* (Core §1.1).

    Every cons cell must be a blank node carrying exactly one ``rdf:first``
    and one ``rdf:rest``, the chain must terminate at ``rdf:nil``, and
    cycles reject (rdflib's ``Collection`` walk hangs on cycles and silently
    picks one of multiple ``rdf:first`` values). *what* names the
    declaration in error messages.

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
