"""``SelectQuery`` rendering and validation — ``core/sparql/`` (ADR-0010).

Unit tier: top-level ``SELECT`` rendering, sub-query emission with modifiers
(``DISTINCT``, ``ORDER BY``, ``LIMIT``/``OFFSET``), and fail-loud validation
of negative limit/offset values.

Order: SelectQuery assembly → subquery modifiers → LIMIT/OFFSET validation.
"""

from __future__ import annotations

import pytest
from rdflib import RDF, URIRef, Variable

from fastshaql.core.sparql import GroupPattern, SelectQuery, TriplePattern
from fastshaql.core.sparql.paths import PredicatePath

EX = URIRef("http://example.org/")
PERSON = EX + "Person"


def _type_triple() -> TriplePattern:
    return TriplePattern(
        subject=Variable("iri"),
        predicate=PredicatePath(RDF.type),
        object=PERSON,
    )


def test_select_query_render_top_level_unchanged() -> None:
    query = SelectQuery(
        projection=(Variable("iri"), Variable("name")),
        where=GroupPattern(children=(_type_triple(),)),
    )
    assert query.render() == (
        """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
}"""
    )


def test_select_query_render_from_default_single_graph() -> None:
    query = SelectQuery(
        projection=(Variable("iri"),),
        where=GroupPattern(children=(_type_triple(),)),
        from_default=(URIRef("urn:ex:g"),),
    )
    assert query.render() == (
        """SELECT ?iri
FROM <urn:ex:g>
WHERE {
  ?iri a <http://example.org/Person> .
}"""
    )


def test_select_query_render_from_default_multiple_graphs() -> None:
    query = SelectQuery(
        projection=(Variable("iri"),),
        where=GroupPattern(children=(_type_triple(),)),
        from_default=(URIRef("urn:ex:g1"), URIRef("urn:ex:g2")),
    )
    assert query.render() == (
        """SELECT ?iri
FROM <urn:ex:g1>
FROM <urn:ex:g2>
WHERE {
  ?iri a <http://example.org/Person> .
}"""
    )


def test_select_query_render_from_default_empty_unchanged() -> None:
    query = SelectQuery(
        projection=(Variable("iri"),),
        where=GroupPattern(children=(_type_triple(),)),
        from_default=(),
    )
    assert query.render() == (
        """SELECT ?iri
WHERE {
  ?iri a <http://example.org/Person> .
}"""
    )


def test_select_query_render_as_subquery_with_modifiers() -> None:
    query = SelectQuery(
        projection=(Variable("iri"),),
        where=GroupPattern(children=(_type_triple(),)),
        distinct=True,
        order_by=(Variable("iri"),),
        limit=2,
        offset=1,
        as_subquery=True,
        from_default=(URIRef("urn:ex:g"),),
    )
    rendered = query.render(indent=1)
    assert "FROM" not in rendered
    assert rendered == (
        """  {
    SELECT DISTINCT ?iri
    WHERE {
      ?iri a <http://example.org/Person> .
    }
    ORDER BY ?iri
    LIMIT 2
    OFFSET 1
  }"""
    )


def test_select_query_rejects_negative_limit() -> None:
    with pytest.raises(ValueError, match="LIMIT may not be negative"):
        SelectQuery(
            projection=(Variable("iri"),),
            where=GroupPattern(children=()),
            limit=-1,
        )


def test_select_query_rejects_negative_offset() -> None:
    with pytest.raises(ValueError, match="OFFSET must be non-negative"):
        SelectQuery(
            projection=(Variable("iri"),),
            where=GroupPattern(children=()),
            offset=-1,
        )


def test_select_query_limit_zero_is_valid() -> None:
    query = SelectQuery(
        projection=(Variable("iri"),),
        where=GroupPattern(children=()),
        limit=0,
        as_subquery=True,
    )
    assert "LIMIT 0" in query.render(indent=0)
