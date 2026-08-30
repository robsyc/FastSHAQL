"""Identifier-derivation helpers — ``core/identifiers.py``.

Unit tier: ``local_name`` extraction for schemes without ``#`` or ``/``,
and ``enum_member_names`` collision suffixing.

Order: local_name → enum member names.
"""

from __future__ import annotations

import pytest
from rdflib import URIRef
from rdflib.term import Literal, Node

from fastshaql.core.kernel.identifiers import enum_member_names, local_name


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
