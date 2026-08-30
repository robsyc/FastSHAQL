"""Scalar and datatype-category mapping — ``core/schema/scalars.py``.

Unit tier: ``resolve_scalar_type`` and ``datatype_category`` for XSD and
custom datatypes, and the literal-space-aware dispatch
(``scalar_type_for_space`` / ``filter_category_for_space``).

Order: resolve_scalar_type → datatype_category → literal-space dispatch → expanded XSD types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rdflib.namespace import RDF, XSD

from fastshaql.core.kernel.constants import DIR_LANG_STRING
from fastshaql.core.schema.scalars import (
    datatype_category,
    filter_category_for_space,
    resolve_scalar_type,
    scalar_type_for_space,
)
from support.builders import EX, scalar_property

if TYPE_CHECKING:
    from rdflib import URIRef


def test_datatype_category_integer() -> None:
    assert datatype_category(XSD.integer) == "integer"


def test_datatype_category_none_falls_back_to_string() -> None:
    assert datatype_category(None) == "string"


def test_datatype_category_unknown_falls_back_to_string() -> None:
    assert datatype_category(EX + "customType") == "string"


# --- Literal-space dispatch (explicit, not datatype=None fall-through) ---


@pytest.mark.parametrize(
    ("datatypes", "expected_scalar", "expected_category"),
    [
        ((), "String", "string"),
        ((XSD.string,), "String", "string"),
        ((XSD.integer,), "Int", "integer"),
        ((EX + "customType",), "String", "string"),
        ((RDF.langString,), "String", "string"),
        ((RDF.langString, DIR_LANG_STRING), "String", "string"),
        ((XSD.string, RDF.langString), "String", "string"),
    ],
    ids=[
        "plain_empty",
        "plain_string",
        "plain_integer",
        "plain_unknown",
        "language",
        "language_set",
        "union",
    ],
)
def test_space_dispatch_across_literal_spaces(
    datatypes: tuple, expected_scalar: str, expected_category: str
) -> None:
    """All three spaces resolve explicitly — the union maps to
    ``String``/``"string"`` by declared branch, PLAIN/LANGUAGE via their
    first datatype."""
    prop = scalar_property(
        "note", min_count=0, max_count=1, datatype=None, datatypes=datatypes
    )
    assert scalar_type_for_space(prop).name == expected_scalar
    assert filter_category_for_space(prop) == expected_category


def test_resolve_scalar_type_none_falls_back_to_string() -> None:
    assert resolve_scalar_type(None).name == "String"


@pytest.mark.parametrize(
    ("datatype", "expected_scalar", "expected_category"),
    [
        (XSD.dateTimeStamp, "String", "datetime"),
        (XSD.duration, "String", "datetime"),
        (XSD.dayTimeDuration, "String", "datetime"),
        (XSD.yearMonthDuration, "String", "datetime"),
        (XSD.gYear, "String", "datetime"),
        (XSD.long, "Int", "integer"),
        (XSD.unsignedInt, "Int", "integer"),
    ],
)
def test_datatype_map_expansion(
    datatype: URIRef,
    expected_scalar: str,
    expected_category: str,
) -> None:
    assert resolve_scalar_type(datatype).name == expected_scalar
    assert datatype_category(datatype) == expected_category
