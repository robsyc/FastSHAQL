"""Identifier-derivation helpers shared by parser, schema, and translation.

Hosts the generic :func:`local_name` (IRI fragment / last path segment) plus
the enum-naming helpers (ADR-0006). Pure functions; no fastshaql-internal
dependencies, so safe to import from any layer.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rdflib import URIRef
from rdflib.term import Literal, Node

if TYPE_CHECKING:
    from collections.abc import Sequence

_GRAPHQL_RESERVED = frozenset({"true", "false", "null"})
_NON_ALNUM = re.compile(r"[^0-9A-Za-z]+")


def local_name(iri: URIRef) -> str:
    """Fragment or last path segment of an IRI."""
    s = str(iri)
    for sep in ("#", "/"):
        idx = s.rfind(sep)
        if idx >= 0:
            return s[idx + 1 :]
    return s


def mangle_enum_member_name(raw: str) -> str:
    """Map a lexical form or IRI local name to a valid GraphQL enum member name."""
    mangled = _NON_ALNUM.sub("_", raw).upper()
    if not mangled or mangled[0].isdigit() or mangled.lower() in _GRAPHQL_RESERVED:
        mangled = f"_{mangled}"
    return mangled


def raw_enum_member_name(term: Node) -> str:
    """Source name for an enum member before mangling — IRI local name or literal lexical form."""
    if isinstance(term, URIRef):
        return local_name(term)
    if isinstance(term, Literal):
        return str(term)
    raise TypeError(
        f"enum member must be an IRI or literal, got {type(term).__name__}"
    )  # pragma: no cover — parser rejects blank nodes in sh:in lists


def enum_member_names(terms: Sequence[Node]) -> list[str]:
    """Final GraphQL enum member names for an ordered ``sh:in`` member list.

    Mangles each term per ADR-0006; when mangled names collide, the later
    member keeps its mangling plus a numeric suffix — ``_2``, ``_3``, …
    (first free number, member order). The suffix collapses onto a trailing
    ``_`` in the base (``"<"``/``"<="`` → ``_``/``_2``, not ``__2`` — a
    ``__`` prefix is reserved by GraphQL introspection), so every result
    stays a valid ``[_A-Za-z][_0-9A-Za-z]*`` enum value name. A member whose
    name collides with nothing keeps exactly its
    :func:`mangle_enum_member_name` output.
    """
    taken: set[str] = set()
    names: list[str] = []
    for term in terms:
        base = mangle_enum_member_name(raw_enum_member_name(term))
        joiner = "" if base.endswith("_") else "_"
        name, counter = base, 1
        while name in taken:
            counter += 1
            name = f"{base}{joiner}{counter}"
        taken.add(name)
        names.append(name)
    return names


def enum_type_name(*, parent_graphql_type_name: str, graphql_field_name: str) -> str:
    """GraphQL enum type name for a property: ``{TypeName}{FieldName}``."""
    field_part = graphql_field_name[:1].upper() + graphql_field_name[1:]
    return f"{parent_graphql_type_name}{field_part}"


def enum_filter_type_name(name: str) -> str:
    """Filter input type name for an enum property."""
    return f"{name}Filter"
