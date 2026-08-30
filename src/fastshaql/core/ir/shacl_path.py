"""SHACL property paths (§4) — Shape IR input, not SPARQL emission.

See: https://www.w3.org/TR/shacl12-core/#property-paths
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rdflib import URIRef


@dataclasses.dataclass(frozen=True)
class PredicatePath:
    """``sh:path <IRI>`` — SHACL §4.1. Parser: object of ``sh:path`` when IRI.
    Example:
    ```ttl
    # SPARQL Property path: ex:parent
    ex:SomeClass-predicateExample
        sh:path ex:parent .
    ```
    """

    iri: URIRef
    """The predicate IRI. Parser: object of ``sh:path`` when IRI."""


@dataclasses.dataclass(frozen=True)
class InversePath:
    """``sh:inversePath`` — SHACL §4.4.
    Example:
    ```ttl
    # SPARQL Property path: ^ex:parent
    ex:SomeClass-inversePathExample
        sh:path [
            sh:inversePath ex:parent
        ] .
    ```
    """

    path: ShaclPropertyPath
    """Nested path. Parser: object of ``sh:inversePath``."""


@dataclasses.dataclass(frozen=True)
class SequencePath:
    """RDF-list sequence path — SHACL §4.2.
    Example:
    ```ttl
    # SPARQL Property path: ex:parent/ex:firstName
    ex:SomeClass-sequencePathExample
        sh:path (
            ex:parent
            ex:firstName
        ) .
    ```
    """

    elements: tuple[ShaclPropertyPath, ...]
    """Ordered path elements. Parser: RDF list under ``sh:path``."""


@dataclasses.dataclass(frozen=True)
class AlternativePath:
    """``sh:alternativePath`` — SHACL §4.3.
    Example:
    ```ttl
    # SPARQL Property path: ex:father|ex:mother
    ex:SomeClass-alternativePathExample
        sh:path [
            sh:alternativePath ( ex:father ex:mother  )
        ] .
    ```
    """

    alternatives: tuple[ShaclPropertyPath, ...]
    """Branch paths. Parser: RDF list under ``sh:alternativePath``."""


@dataclasses.dataclass(frozen=True)
class ZeroOrMorePath:
    """``sh:zeroOrMorePath`` — SHACL §4.5. SPARQL property path: ``*``."""

    path: ShaclPropertyPath
    """Operand path. Parser: object of ``sh:zeroOrMorePath``."""


@dataclasses.dataclass(frozen=True)
class OneOrMorePath:
    """``sh:oneOrMorePath`` — SHACL §4.6. SPARQL property path: ``+``."""

    path: ShaclPropertyPath
    """Operand path. Parser: object of ``sh:oneOrMorePath``."""


@dataclasses.dataclass(frozen=True)
class ZeroOrOnePath:
    """``sh:zeroOrOnePath`` — SHACL §4.7. SPARQL property path: ``?``."""

    path: ShaclPropertyPath
    """Operand path. Parser: object of ``sh:zeroOrOnePath``."""


type ShaclPropertyPath = (
    PredicatePath
    | InversePath
    | SequencePath
    | AlternativePath
    | ZeroOrMorePath
    | OneOrMorePath
    | ZeroOrOnePath
)


def iter_path_predicates(path: ShaclPropertyPath) -> Iterator[URIRef]:
    """Yield every predicate IRI inside a (possibly composite) path."""
    match path:
        case PredicatePath(iri=iri):
            yield iri
        case (
            InversePath(path=inner)
            | ZeroOrMorePath(path=inner)
            | OneOrMorePath(path=inner)
            | ZeroOrOnePath(path=inner)
        ):
            yield from iter_path_predicates(inner)
        # ``case`` fall-through below the last arm is unreachable: the
        # ShaclPropertyPath union is closed (no wildcard arm, no fourth kind).
        case (
            SequencePath(elements=elements) | AlternativePath(alternatives=elements)
        ):  # pragma: no branch — closed path union: no fall-through
            for element in elements:
                yield from iter_path_predicates(element)
