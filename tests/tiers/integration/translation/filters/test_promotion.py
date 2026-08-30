"""Filter promotion and relationship-filter translation.

Integration tier: filter promotion (ADR-0009), FILTER EXISTS blocks, promotion
edge cases. Declarative golden SPARQL for full cases lives in ``tests/tiers/e2e/``.

Order: scalar promotion, relationship EXISTS, scope edge cases, errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fastshaql.core.translation import translate_query
from support.builders import registry_with, scalar_property, shape_with
from support.graphql_utils import root_field_node

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry


def test_translate_promotion_optional_field_in_filter_bound(
    cardinality_thing_shape,
    cardinality_registry: ShapeRegistry,
) -> None:
    query = (
        '{ things(where: { subtitle: { eq: "The First" } }) { iri label subtitle } }'
    )
    result = translate_query(
        cardinality_thing_shape, root_field_node(query), cardinality_registry
    )
    assert result.query.render() == (
        """SELECT ?iri ?label ?subtitle
WHERE {
  ?iri a <http://example.org/Thing> .
  ?iri <http://example.org/label> ?label .
  ?iri <http://example.org/subtitle> ?subtitle .
  FILTER(?subtitle = "The First")
}"""
    )
    assert "OPTIONAL" not in result.query.render()


def test_translate_promotion_filtered_field_not_selected(
    cardinality_thing_shape,
    cardinality_registry: ShapeRegistry,
) -> None:
    query = '{ things(where: { subtitle: { eq: "The First" } }) { iri label } }'
    result = translate_query(
        cardinality_thing_shape, root_field_node(query), cardinality_registry
    )
    assert result.query.render() == (
        """SELECT ?iri ?label
WHERE {
  ?iri a <http://example.org/Thing> .
  ?iri <http://example.org/label> ?label .
  ?iri <http://example.org/subtitle> ?subtitle .
  FILTER(?subtitle = "The First")
}"""
    )
    assert "subtitle" not in result.query.render().split("SELECT")[1].split("WHERE")[0]


def test_translate_sh_node_relationship_filter_omits_type_in_exists(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    query = '{ persons(where: { address: { street: { eq: "Main St" } } }) { name } }'
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/address> ?address_iri .
  FILTER(EXISTS {
    ?address_iri <http://example.org/street> ?_rf_address_street .
    FILTER(?_rf_address_street = "Main St")
  })
}"""
    assert result.query.render() == golden
    assert "a <http://example.org/Address>" not in result.query.render()


def test_translate_employer_name_filter_with_selection(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    query = (
        '{ persons(where: { employer: { name: { eq: "Acme" } } }) '
        "{ name employer { name } } }"
    )
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    assert result.query.render() == (
        """SELECT ?iri ?name ?employer_iri ?employer_name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/employer> ?employer_iri .
  ?employer_iri a <http://example.org/Company> .
  ?employer_iri <http://example.org/name> ?employer_name .
  FILTER(EXISTS {
    ?employer_iri a <http://example.org/Company> .
    ?employer_iri <http://example.org/name> ?_rf_employer_name .
    FILTER(?_rf_employer_name = "Acme")
  })
}"""
    )


def test_translate_root_filter_does_not_promote_optional_child_field(
    relationship_registry: ShapeRegistry,
) -> None:
    registry = registry_with(
        relationship_registry,
        shape_with(
            relationship_registry.by_type_name["Company"],
            name=scalar_property("name", min_count=0, max_count=1),
        ),
    )
    person = registry.by_type_name["Person"]
    query = '{ persons(where: { name: { eq: "X" } }) { name employer { name } } }'
    result = translate_query(person, root_field_node(query), registry)
    golden = """SELECT ?iri ?name ?employer_iri ?employer_name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  OPTIONAL {
    ?iri <http://example.org/employer> ?employer_iri .
    ?employer_iri a <http://example.org/Company> .
    OPTIONAL {
      ?employer_iri <http://example.org/name> ?employer_name .
    }
  }
  FILTER(?name = "X")
}"""
    assert result.query.render() == golden


def test_translate_raises_on_unknown_filter_field(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    query = '{ persons(where: { nonexistent: { eq: "x" } }) { name } }'
    with pytest.raises(ValueError, match="Unknown filter field 'nonexistent'"):
        translate_query(person_shape, root_field_node(query), relationship_registry)


def test_translate_empty_relationship_filter_promotes_join(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    query = "{ persons(where: { employer: {} }) { name } }"
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/employer> ?employer_iri .
}"""
    assert result.query.render() == golden
    assert "FILTER" not in result.query.render()
    assert "OPTIONAL" not in result.query.render()


def test_translate_nested_filter_does_not_promote_homonymous_root_scalar(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    query = '{ persons(where: { employer: { name: { eq: "Acme" } } }) { iri } }'
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    golden = """SELECT ?iri
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/employer> ?employer_iri .
  FILTER(EXISTS {
    ?employer_iri a <http://example.org/Company> .
    ?employer_iri <http://example.org/name> ?_rf_employer_name .
    FILTER(?_rf_employer_name = "Acme")
  })
}"""
    assert result.query.render() == golden
    assert "OPTIONAL" not in result.query.render()
