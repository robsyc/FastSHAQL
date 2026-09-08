"""Literal coercion for filter operands — ``core/translation/filters/literals.py``.

Unit tier: direct calls to ``_literal_value`` for datatype edge cases not
exercised through the integration filter tests.

Order: standard datatypes → custom datatype.
"""

from __future__ import annotations

from graphql.language.ast import (
    BooleanValueNode,
    FloatValueNode,
    IntValueNode,
    ListValueNode,
    NullValueNode,
    StringValueNode,
)
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from fastshaql.core.translation.filters.literals import (
    _literal_value,
    list_to_literals,
    value_to_literal,
)


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


# --- GraphQL value-node coercion (mutation-hardening batch) ---


def test_string_value_respects_declared_datatype() -> None:
    # A field's declared datatype must ride along on string operands —
    # collapsing it to xsd:string (or None) changes the emitted literal.
    node = StringValueNode(value="2020-01-01")
    assert value_to_literal(node, XSD.date) == Literal("2020-01-01", datatype=XSD.date)


def test_numeric_and_boolean_values_respect_declared_datatype() -> None:
    assert value_to_literal(IntValueNode(value="42"), XSD.date) == Literal(
        "42", datatype=XSD.date
    )
    assert value_to_literal(FloatValueNode(value="1.5"), XSD.date) == Literal(
        "1.5", datatype=XSD.date
    )
    assert value_to_literal(BooleanValueNode(value="true"), XSD.date) == Literal(
        "true", datatype=XSD.date
    )


def test_value_defaults_without_declared_datatype() -> None:
    assert value_to_literal(StringValueNode(value="x"), None) == Literal("x")
    assert value_to_literal(IntValueNode(value="42"), None) == Literal(
        "42", datatype=XSD.integer
    )
    assert value_to_literal(FloatValueNode(value="1.5"), None) == Literal(
        "1.5", datatype=XSD.float
    )
    assert value_to_literal(BooleanValueNode(value="true"), None) == Literal(
        "true", datatype=XSD.boolean
    )
    assert value_to_literal(NullValueNode(), XSD.date) is None


def test_list_to_literals_preserves_declared_datatype() -> None:
    node = ListValueNode(
        values=[
            StringValueNode(value="2020-01-01"),
            StringValueNode(value="2021-06-30"),
        ]
    )
    literals = list_to_literals(node, XSD.date)
    assert literals == (
        Literal("2020-01-01", datatype=XSD.date),
        Literal("2021-06-30", datatype=XSD.date),
    )
