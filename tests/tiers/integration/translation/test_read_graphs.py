"""Default-graph scoping via ``QueryContext.read_graphs`` (ADR-0011).

Integration tier: ``FROM`` dataset clauses on the outer ``SelectQuery`` only,
and the ``write_graph`` reservation's rejection at translation — the single
``QueryContext`` consumer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastshaql.core.kernel.context import QueryContext
from fastshaql.core.translation import translate_query
from support.graphql_utils import root_field_node

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry


def test_translate_read_graphs_emits_from_clauses(
    minimal_registry: ShapeRegistry,
) -> None:
    shape = minimal_registry.by_type_name["Thing"]
    query = "{ things { label } }"
    result = translate_query(
        shape,
        root_field_node(query),
        minimal_registry,
        query_context=QueryContext(read_graphs=("urn:ex:g1", "urn:ex:g2")),
    )
    golden = """SELECT ?iri ?label
FROM <urn:ex:g1>
FROM <urn:ex:g2>
WHERE {
  ?iri a <http://example.org/Thing> .
  ?iri <http://example.org/label> ?label .
}"""
    assert result.query.render() == golden


def test_translate_no_read_graphs_unchanged(
    minimal_registry: ShapeRegistry,
) -> None:
    shape = minimal_registry.by_type_name["Thing"]
    query = "{ things { label } }"
    result = translate_query(shape, root_field_node(query), minimal_registry)
    golden = """SELECT ?iri ?label
WHERE {
  ?iri a <http://example.org/Thing> .
  ?iri <http://example.org/label> ?label .
}"""
    assert result.query.render() == golden


def test_translate_empty_read_graphs_unchanged(
    minimal_registry: ShapeRegistry,
) -> None:
    shape = minimal_registry.by_type_name["Thing"]
    query = "{ things { label } }"
    result = translate_query(
        shape,
        root_field_node(query),
        minimal_registry,
        query_context=QueryContext(read_graphs=()),
    )
    golden = """SELECT ?iri ?label
WHERE {
  ?iri a <http://example.org/Thing> .
  ?iri <http://example.org/label> ?label .
}"""
    assert result.query.render() == golden


def test_translate_read_graphs_rejects_injection_attempt(
    minimal_registry: ShapeRegistry,
) -> None:
    shape = minimal_registry.by_type_name["Thing"]
    query = "{ things { label } }"
    result = translate_query(
        shape,
        root_field_node(query),
        minimal_registry,
        query_context=QueryContext(read_graphs=("urn:ok> } UNION",)),
    )
    with pytest.raises(Exception, match="does not look like a valid URI"):
        result.query.render()


def test_translate_write_graph_rejected(
    minimal_registry: ShapeRegistry,
) -> None:
    """The reserved write-target slot fails loudly at translation — reads
    never consume it, so a set value cannot silently masquerade as scoping."""
    shape = minimal_registry.by_type_name["Thing"]
    with pytest.raises(ValueError, match="write_graph is reserved"):
        translate_query(
            shape,
            root_field_node("{ things { label } }"),
            minimal_registry,
            query_context=QueryContext(write_graph="urn:ex:writes"),
        )
