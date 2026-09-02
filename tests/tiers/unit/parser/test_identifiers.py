"""Identifier-derivation helpers — ``core/kernel/identifiers.py`` and
``core/parser/util/identifiers.py``.

Unit tier: ``local_name`` extraction for schemes without ``#`` or ``/``,
``enum_member_names`` collision suffixing, and parse-time ``sh:codeIdentifier``
validation (SHACL 1.2 §8.4).

Order: local_name → enum member names → sh:codeIdentifier validation →
reserved names → Python-keyword escapes.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef
from rdflib.term import Literal, Node

from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.kernel.identifiers import (
    enum_member_names,
    local_name,
    mangle_enum_member_name,
    raw_enum_member_name,
)
from fastshaql.core.parser.errors import UnsupportedShapeError
from fastshaql.core.parser.util import (
    InvalidCodeIdentifierError,
    ReservedGraphQLNameError,
    graphql_type_name,
    property_graphql_field_name,
    read_code_identifier,
)

SUBJECT = URIRef("http://example.org/ThingShape")


@pytest.mark.parametrize(
    "iri",
    ["urn:uuid:abc123", "mailto:user@example.org"],
    ids=["urn", "mailto"],
)
def test_local_name_non_split_returns_full_string(iri: str) -> None:
    """An IRI without ``#`` or ``/`` — ``local_name`` returns the full string."""
    assert local_name(URIRef(iri)) == iri


@pytest.mark.parametrize(
    ("iri", "expected"),
    [("#frag", "frag"), ("/root", "root")],
    ids=["fragment_at_start", "slash_at_start"],
)
def test_local_name_separator_at_position_zero(iri: str, expected: str) -> None:
    """A separator at index 0 is still a separator — the local name is the
    remainder after it, not the whole (relative) IRI."""
    assert local_name(URIRef(iri)) == expected


@pytest.mark.parametrize("raw", ["true", "false", "null"])
def test_mangle_reserved_word_gains_underscore_prefix(raw: str) -> None:
    """The reserved-word check is case-insensitive on the mangled (uppercased)
    result — ``true``/``false``/``null`` escape as ``_TRUE``/``_FALSE``/``_NULL``."""
    assert mangle_enum_member_name(raw) == f"_{raw.upper()}"


def test_raw_enum_member_name_iri_uses_local_name() -> None:
    """An IRI member's source name is its local name (literals use the lexical
    form — the split happens here, not in mangling)."""
    assert raw_enum_member_name(URIRef("http://example.org/ns#Alpha")) == "Alpha"


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


def test_enum_member_names_collision_on_plain_base_uses_underscore_joiner() -> None:
    """A colliding base without a trailing ``_`` suffixes as ``_2`` — one
    underscore; the collapsing joiner applies only to trailing-``_`` bases."""
    assert enum_member_names((Literal("A"), Literal("A"))) == ["A", "A_2"]


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


# --- Reserved GraphQL names (derivation endpoints) ---


@pytest.mark.parametrize(
    ("code_identifier", "iri"),
    [
        ("__Foo", URIRef("http://example.org/ThingShape")),
        (None, URIRef("http://example.org/__FooShape")),
    ],
    ids=["code_identifier", "iri_local_name"],
)
def test_graphql_type_name_rejects_reserved_dunder(
    code_identifier: str | None, iri: URIRef
) -> None:
    """GraphQL reserves ``__``-prefixed names — both derivation paths reject."""
    with pytest.raises(ReservedGraphQLNameError, match="__Foo"):
        graphql_type_name(code_identifier=code_identifier, iri=iri)


@pytest.mark.parametrize(
    ("code_identifier", "predicate"),
    [
        ("__secret", URIRef("http://example.org/label")),
        (None, URIRef("http://example.org/__secret")),
    ],
    ids=["code_identifier", "predicate_local_name"],
)
def test_property_field_name_rejects_reserved_dunder(
    code_identifier: str | None, predicate: URIRef
) -> None:
    """Property field names get the same reserved-name rule as type names."""
    with pytest.raises(ReservedGraphQLNameError, match="__secret"):
        property_graphql_field_name(
            path=PredicatePath(predicate),
            code_identifier=code_identifier,
            prop_shape=SUBJECT,
        )


def test_graphql_type_name_single_underscore_stays_legal() -> None:
    """``_``-prefix is GraphQL-legal — only the reserved ``__`` prefix rejects."""
    assert graphql_type_name(code_identifier="_Foo", iri=SUBJECT) == "_Foo"


# --- Python-keyword escapes (finalize_graphql_name) ---


def test_graphql_type_name_escapes_python_keyword() -> None:
    """A type name landing on a Python keyword gets the ``_`` suffix —
    GraphQL allows it, Python resolvers/serializers need the escape."""
    assert graphql_type_name(code_identifier="class", iri=SUBJECT) == "class_"


def test_property_field_name_escapes_python_keyword_from_local_name() -> None:
    """A predicate local name that is a keyword escapes the same way —
    both field-name derivation paths share the escape."""
    assert (
        property_graphql_field_name(
            path=PredicatePath(URIRef("http://example.org/class")),
            code_identifier=None,
            prop_shape=SUBJECT,
        )
        == "class_"
    )


def test_graphql_type_name_non_keyword_passes_through_unchanged() -> None:
    """Ordinary names never gain the suffix."""
    assert graphql_type_name(code_identifier="Person", iri=SUBJECT) == "Person"
