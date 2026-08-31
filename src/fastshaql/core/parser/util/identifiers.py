"""Parser-specific identifier derivation: SHACL ``sh:codeIdentifier`` resolution
and inline-shape IRI synthesis.

Generic IRI helpers (``local_name``) and Python-keyword escapes live in
:mod:`fastshaql.core.identifiers`; this module composes them with SHACL
semantics. All consumers are inside ``core/parser/``.
"""

from __future__ import annotations

import keyword
import re
from typing import TYPE_CHECKING

from rdflib import URIRef
from rdflib.namespace import XSD
from rdflib.term import Literal

from fastshaql.core.ir.shacl_path import PredicatePath, ShaclPropertyPath
from fastshaql.core.kernel.constants import INLINE_SHAPE_PREFIX
from fastshaql.core.kernel.identifiers import local_name

from .graph_reads import sole_object
from .namespaces import SH_CODE_IDENTIFIER

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

__all__ = [
    "InvalidCodeIdentifierError",
    "MissingCompositePathCodeIdentifierError",
    "ReservedGraphQLNameError",
    "finalize_graphql_name",
    "graphql_type_name",
    "property_graphql_field_name",
    "read_code_identifier",
    "synthesize_inline_shape_iri",
]


class InvalidCodeIdentifierError(ValueError):
    """Raised when ``sh:codeIdentifier`` violates the SHACL 1.2 §8.4 syntax."""


class ReservedGraphQLNameError(ValueError):
    """Raised when a derived GraphQL name starts with the reserved ``__`` prefix."""


class MissingCompositePathCodeIdentifierError(ValueError):
    """Raised when a composite-path property shape lacks ``sh:codeIdentifier``."""


_CODE_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def read_code_identifier(graph: Graph, subject: Node) -> str | None:
    """``sh:codeIdentifier`` on *subject*, validated at parse time (§8.4).

    The value must be an ``xsd:string`` literal matching
    ``^[a-zA-Z_][a-zA-Z0-9_]*$`` — the same grammar GraphQL names follow,
    so an invalid one would otherwise surface far from its source, as a
    broken schema build.

    Raises:
        InvalidCodeIdentifierError: On a non-literal or non-``xsd:string``
            value, or a lexical form outside the §8.4 grammar.
        UnsupportedShapeError: On multiple values (§8.4 allows one).
    """
    term = sole_object(graph, subject, SH_CODE_IDENTIFIER, what="sh:codeIdentifier")
    if term is None:
        return None
    if not isinstance(term, Literal) or (
        term.language is not None or term.datatype not in (None, XSD.string)
    ):
        raise InvalidCodeIdentifierError(
            f"sh:codeIdentifier on {subject} must be an xsd:string literal "
            f"matching ^[a-zA-Z_][a-zA-Z0-9_]*$ (SHACL 1.2 §8.4), got {term!r}"
        )
    value = str(term)
    if _CODE_IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise InvalidCodeIdentifierError(
            f"sh:codeIdentifier {value!r} on {subject} does not match "
            "^[a-zA-Z_][a-zA-Z0-9_]*$ (SHACL 1.2 §8.4)"
        )
    return value


def finalize_graphql_name(name: str) -> str:
    """Finalize a GraphQL type/field name: reject the reserved ``__`` prefix
    (GraphQL October2021 §Names), then escape Python keywords (``class`` → ``class_``)."""
    if name.startswith("__"):
        raise ReservedGraphQLNameError(
            f"{name!r} starts with the GraphQL-reserved '__' prefix — choose a "
            "different sh:codeIdentifier or IRI local name"
        )
    return f"{name}_" if keyword.iskeyword(name) else name


def graphql_field_name(
    *,
    code_identifier: str | None,
    path_predicate: URIRef,
) -> str:
    """GraphQL field name from ``sh:codeIdentifier`` or primary predicate local name."""
    if code_identifier:
        return finalize_graphql_name(code_identifier)
    return finalize_graphql_name(local_name(path_predicate))


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
    return finalize_graphql_name(code_identifier)


def graphql_type_name(
    *,
    code_identifier: str | None,
    iri: URIRef,
) -> str:
    """GraphQL type name from ``sh:codeIdentifier`` or IRI local name."""
    if code_identifier:
        return finalize_graphql_name(code_identifier)
    return finalize_graphql_name(local_name(iri))


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
