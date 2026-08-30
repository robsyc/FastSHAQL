"""Parser-specific identifier derivation: SHACL ``sh:codeIdentifier`` resolution
and inline-shape IRI synthesis.

Generic IRI helpers (``local_name``) and Python-keyword escapes live in
:mod:`fastshaql.core.identifiers`; this module composes them with SHACL
semantics. All consumers are inside ``core/parser/``.
"""

from __future__ import annotations

import keyword
from typing import TYPE_CHECKING

from rdflib import URIRef

from fastshaql.core.ir.shacl_path import PredicatePath, ShaclPropertyPath
from fastshaql.core.kernel.constants import INLINE_SHAPE_PREFIX
from fastshaql.core.kernel.identifiers import local_name

if TYPE_CHECKING:
    from rdflib.term import Node

__all__ = [
    "MissingCompositePathCodeIdentifierError",
    "graphql_type_name",
    "property_graphql_field_name",
    "safe_python_identifier",
    "synthesize_inline_shape_iri",
]


class MissingCompositePathCodeIdentifierError(ValueError):
    """Raised when a composite-path property shape lacks ``sh:codeIdentifier``."""


def safe_python_identifier(name: str) -> str:
    """Escape Python keywords (e.g. ``class`` → ``class_``)."""
    return f"{name}_" if keyword.iskeyword(name) else name


def graphql_field_name(
    *,
    code_identifier: str | None,
    path_predicate: URIRef,
) -> str:
    """GraphQL field name from ``sh:codeIdentifier`` or primary predicate local name."""
    if code_identifier:
        return safe_python_identifier(code_identifier)
    return safe_python_identifier(local_name(path_predicate))


def property_graphql_field_name(
    *,
    path: ShaclPropertyPath,
    code_identifier: str | None,
    prop_shape: Node,
) -> str:
    """GraphQL field name for a property shape path.

    Simple predicate paths may fall back to the predicate local name.
    Composite paths require ``sh:codeIdentifier`` (ADR-0004).
    """
    if isinstance(path, PredicatePath):
        return graphql_field_name(
            code_identifier=code_identifier,
            path_predicate=path.iri,
        )
    if not code_identifier:
        raise MissingCompositePathCodeIdentifierError(
            f"Composite-path property shape {prop_shape} requires sh:codeIdentifier"
        )
    return safe_python_identifier(code_identifier)


def graphql_type_name(
    *,
    code_identifier: str | None,
    iri: URIRef,
) -> str:
    """GraphQL type name from ``sh:codeIdentifier`` or IRI local name."""
    if code_identifier:
        return safe_python_identifier(code_identifier)
    return safe_python_identifier(local_name(iri))


def synthesize_inline_shape_iri(
    *,
    parent_graphql_type_name: str,
    graphql_field_name: str,
) -> URIRef:
    """Stable IRI for a blank-node property shape.

    Merges parent GraphQL type name and field name,
    e.g. ``Thing`` + ``label`` → ``urn:fastshaql:inline:ThingLabel``
    """
    field_part = graphql_field_name[:1].upper() + graphql_field_name[1:]
    return URIRef(f"{INLINE_SHAPE_PREFIX}{parent_graphql_type_name}{field_part}")
