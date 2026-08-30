"""SPARQL-results+json wire decoding — ``decode_sparql_results``.

Unit tier: the orjson-backed decode seam that turns
``application/sparql-results+json`` bytes into rdflib-typed rows. Shared by
``InMemoryStore`` parity tests and the shipped HTTP store
(``fastshaql.stores.http``), so every HTTP-backed store decodes identically.
"""

from __future__ import annotations

import orjson
import pytest
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import XSD

from fastshaql.core.execution.store import decode_sparql_results


def _results(*bindings: dict) -> bytes:
    """Build a SPARQL-results+json body from raw binding dicts."""
    return orjson.dumps({"results": {"bindings": list(bindings)}})


def test_decode_uri_binding() -> None:
    raw = _results({"s": {"type": "uri", "value": "http://ex/s"}})
    assert decode_sparql_results(raw) == [{"s": URIRef("http://ex/s")}]


def test_decode_plain_literal_binding() -> None:
    raw = _results({"label": {"type": "literal", "value": "Alpha"}})
    assert decode_sparql_results(raw) == [{"label": Literal("Alpha")}]


def test_decode_typed_literal_binding() -> None:
    raw = _results(
        {
            "n": {
                "type": "literal",
                "value": "42",
                "datatype": str(XSD.integer),
            }
        }
    )
    term = decode_sparql_results(raw)[0]["n"]
    assert term == Literal("42", datatype=XSD.integer)
    assert term.toPython() == 42  # type: ignore[union-attr]


def test_decode_lang_literal_binding() -> None:
    raw = _results({"label": {"type": "literal", "value": "Bonjour", "xml:lang": "fr"}})
    assert decode_sparql_results(raw) == [{"label": Literal("Bonjour", lang="fr")}]


def test_decode_bnode_binding() -> None:
    raw = _results({"b": {"type": "bnode", "value": "id1"}})
    assert decode_sparql_results(raw) == [{"b": BNode("id1")}]


def test_decode_multiple_rows_and_vars() -> None:
    raw = _results(
        {
            "s": {"type": "uri", "value": "http://ex/a"},
            "label": {"type": "literal", "value": "A"},
        },
        {
            "s": {"type": "uri", "value": "http://ex/b"},
            "label": {"type": "literal", "value": "B"},
        },
    )
    rows = decode_sparql_results(raw)
    assert len(rows) == 2
    assert rows[0] == {"s": URIRef("http://ex/a"), "label": Literal("A")}
    assert rows[1]["label"] == Literal("B")


def test_decode_empty_bindings() -> None:
    assert decode_sparql_results(_results()) == []


def test_decode_unbound_var_omits_key() -> None:
    # A binding carrying only ``s`` means ``o`` is unbound -> key absent.
    raw = _results({"s": {"type": "uri", "value": "http://ex/s"}})
    rows = decode_sparql_results(raw)
    assert "o" not in rows[0]


def test_decode_malformed_json_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unexpected character"):
        decode_sparql_results(b"{not valid json")
