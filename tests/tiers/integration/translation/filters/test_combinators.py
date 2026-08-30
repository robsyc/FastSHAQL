"""Filter combinator translation — AND / OR / NOT.

Integration tier: composable filter input combinators (ADR-0009).

Order: implicit AND → explicit AND → OR → NOT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib.namespace import XSD

from fastshaql.core.translation import translate_query
from support.builders import scalar_property, shape_with
from support.graphql_utils import root_field_node

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry


def test_translate_implicit_and_multiple_scalars(
    relationship_registry: ShapeRegistry,
) -> None:
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        age=scalar_property("age", min_count=0, max_count=1, datatype=XSD.integer),
    )
    query = (
        '{ persons(where: { name: { eq: "Alice" }, age: { gt: 25 } }) { name age } }'
    )
    result = translate_query(person, root_field_node(query), relationship_registry)
    golden = """SELECT ?iri ?name ?age
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/age> ?age .
  FILTER(?name = "Alice" && ?age > "25"^^<http://www.w3.org/2001/XMLSchema#integer>)
}"""
    assert result.query.render() == golden


def test_translate_explicit_and_combinator(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    query = (
        '{ persons(where: { AND: [{ name: { eq: "Alice" } }, '
        '{ name: { contains: "lic" } }] }) { name } }'
    )
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(?name = "Alice" && CONTAINS(?name, "lic"))
}"""
    assert result.query.render() == golden


def test_translate_explicit_not_combinator(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    query = '{ persons(where: { NOT: { name: { eq: "Alice" } } }) { name } }'
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(!(?name = "Alice"))
}"""
    assert result.query.render() == golden
