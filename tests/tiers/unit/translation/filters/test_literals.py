"""Literal coercion for filter operands — ``core/translation/filters/literals.py``.

Unit tier: direct calls to ``_literal_value`` for datatype edge cases not
exercised through the integration filter tests.

Order: standard datatypes → custom datatype.
"""

from __future__ import annotations

from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from fastshaql.core.translation.filters.literals import _literal_value


def test_literal_value_plain_string() -> None:
    result = _literal_value("hello", None)
    assert result == Literal("hello")


def test_literal_value_explicit_string_datatype() -> None:
    result = _literal_value("hello", XSD.string)
    assert result == Literal("hello")


def test_literal_value_custom_datatype_preserves_datatype() -> None:
    custom = URIRef("http://example.org/customType")
    result = _literal_value("hello", custom)
    assert result == Literal("hello", datatype=custom)
    assert result.datatype == custom
