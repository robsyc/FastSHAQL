"""Identifier-derivation helpers — ``core/kernel/identifiers.py`` and
``core/parser/util/identifiers.py``.

Unit tier: ``local_name`` extraction for schemes without ``#`` or ``/``,
``enum_member_names`` collision suffixing, and parse-time ``sh:codeIdentifier``
validation (SHACL 1.2 §8.4).

Order: local_name → enum member names → sh:codeIdentifier validation.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef
from rdflib.term import Literal, Node

from fastshaql.core.kernel.identifiers import enum_member_names, local_name
from fastshaql.core.parser.errors import UnsupportedShapeError
from fastshaql.core.parser.util import InvalidCodeIdentifierError, read_code_identifier

SUBJECT = URIRef("http://example.org/ThingShape")


@pytest.mark.parametrize(
    "iri",
    ["urn:uuid:abc123", "mailto:user@example.org"],
    ids=["urn", "mailto"],
)
def test_local_name_non_split_returns_full_string(iri: str) -> None:
    """An IRI without ``#`` or ``/`` — ``local_name`` returns the full string."""
    assert local_name(URIRef(iri)) == iri


def test_enum_member_names_no_collision_matches_mangling() -> None:
    """Without collisions each name is exactly the per-member mangling, in order."""
    terms: tuple[Node, ...] = (Literal("active"), Literal("entered-in-error"))
    assert enum_member_names(terms) == ["ACTIVE", "ENTERED_IN_ERROR"]


def test_enum_member_names_collision_suffixes_in_member_order() -> None:
    """FHIR Quantity comparators all mangle to ``_`` — later members get ``_2``, ``_3``, ``_4``."""
    terms: tuple[Node, ...] = tuple(
        Literal(comparator) for comparator in ("<", "<=", ">=", ">")
    )
    assert enum_member_names(terms) == ["_", "_2", "_3", "_4"]


def test_enum_member_names_suffix_skips_organically_taken_name() -> None:
    """A suffix candidate already taken by an earlier member is skipped.

    ``"2"`` mangles to ``_2``; the later ``"<="`` (base ``_``) must not reuse it.
    """
    terms: tuple[Node, ...] = (Literal("2"), Literal("<"), Literal("<="))
    assert enum_member_names(terms) == ["_2", "_", "_3"]


def test_enum_member_names_duplicate_terms_get_suffixed() -> None:
    """Duplicate terms (SHACL-legal, membership-insensitive) get distinct names
    mapping to the same internal value; serialization is first-name-wins."""
    assert enum_member_names((Literal("<"), Literal("<"))) == ["_", "_2"]


# --- sh:codeIdentifier validation (parser/util/identifiers.py) ---


def _graph_with_code_identifier(term: str) -> Graph:
    graph = Graph()
    graph.parse(
        data=f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        ex:ThingShape sh:codeIdentifier {term} .
        """,
        format="turtle",
    )
    return graph


def test_read_code_identifier_absent_returns_none() -> None:
    """Absent ``sh:codeIdentifier`` reads as ``None``."""
    assert read_code_identifier(Graph(), SUBJECT) is None


def test_read_code_identifier_valid() -> None:
    """A valid §8.4 name round-trips unchanged."""
    graph = _graph_with_code_identifier('"Person_Name1"')
    assert read_code_identifier(graph, SUBJECT) == "Person_Name1"


def test_read_code_identifier_multiple_values_reject() -> None:
    """§8.4 allows one ``sh:codeIdentifier`` — no silent arbitrary pick."""
    graph = _graph_with_code_identifier('"A", "B"')
    with pytest.raises(UnsupportedShapeError, match="Multiple sh:codeIdentifier"):
        read_code_identifier(graph, SUBJECT)


@pytest.mark.parametrize(
    ("term", "fragment"),
    [
        ('"9lives"', "does not match"),
        ('"has-space"', "does not match"),
        ('"Foo"@en', "xsd:string literal"),
        ("ex:NotALiteral", "xsd:string literal"),
    ],
    ids=["leading_digit", "dash", "lang_tagged", "iri"],
)
def test_read_code_identifier_rejects_invalid(term: str, fragment: str) -> None:
    """§8.4: an ``xsd:string`` literal matching ``^[a-zA-Z_][a-zA-Z0-9_]*$`` —
    a bad term kind and a bad lexical form are distinct errors."""
    graph = _graph_with_code_identifier(term)
    with pytest.raises(InvalidCodeIdentifierError, match=fragment):
        read_code_identifier(graph, SUBJECT)
