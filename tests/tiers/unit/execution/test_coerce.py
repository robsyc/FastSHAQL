"""Term coercion — ``coerce_value`` in ``core/execution/converter.py``.

Unit tier: RDF term → Python native value mapping that graphql-core serializes.
Covers the scalar leaf coercion shared by every converter path.
"""

from __future__ import annotations

from rdflib import BNode, Literal, URIRef
from rdflib.namespace import XSD

from fastshaql.core.execution.converter import coerce_value


def test_coerce_string_literal() -> None:
    assert coerce_value(Literal("Alpha")) == "Alpha"


def test_coerce_integer_literal() -> None:
    assert coerce_value(Literal("42", datatype=XSD.integer)) == 42


def test_coerce_boolean_literal() -> None:
    assert coerce_value(Literal("true", datatype=XSD.boolean)) is True


def test_coerce_double_literal() -> None:
    assert coerce_value(Literal("3.14", datatype=XSD.double)) == 3.14


def test_coerce_uriref() -> None:
    assert coerce_value(URIRef("http://ex/s")) == "http://ex/s"


def test_coerce_bnode() -> None:
    assert coerce_value(BNode("id1")) == str(BNode("id1"))


def test_coerce_none_returns_none() -> None:
    assert coerce_value(None) is None
