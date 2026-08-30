"""Relationship selection translation (ADR-0014).

Integration tier: imperative SPARQL golden strings for joins, nesting,
recursion, and selection errors not covered by declarative fixtures.

Order: errors → optional/required joins → nesting and recursion → additional errors & fragment rejection.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest
from rdflib import Variable

from fastshaql.core.registry import ShapeRegistry
from fastshaql.core.translation import translate_query
from support.builders import (
    EX,
    node_shape,
    relationship_property,
    scalar_property,
    shape_with,
)
from support.graphql_utils import root_field_node

if TYPE_CHECKING:
    from graphql.language.ast import FieldNode


def _root_field(query_str: str) -> FieldNode:
    return root_field_node(query_str)


# --- Errors ---


def test_translate_raises_on_shape_without_target_class(
    minimal_registry: ShapeRegistry,
) -> None:
    shape = node_shape("Orphan", target_class=None)
    field_node = _root_field("{ orphan { iri } }")
    with pytest.raises(ValueError, match="no supported target"):
        translate_query(shape, field_node, minimal_registry)


def test_translate_raises_on_unknown_field(
    minimal_registry: ShapeRegistry,
) -> None:
    thing = minimal_registry.by_type_name["Thing"]
    field_node = _root_field("{ things { nonexistent } }")
    with pytest.raises(ValueError, match="Unknown field 'nonexistent'"):
        translate_query(thing, field_node, minimal_registry)


# --- Optional and required joins ---


def test_translate_all_optional_scalars_use_optional_blocks(
    cardinality_thing_shape,
    cardinality_registry: ShapeRegistry,
) -> None:
    field_node = _root_field("{ things { iri subtitle } }")
    result = translate_query(cardinality_thing_shape, field_node, cardinality_registry)
    assert result.query.render() == (
        """SELECT ?iri ?subtitle
WHERE {
  ?iri a <http://example.org/Thing> .
  OPTIONAL {
    ?iri <http://example.org/subtitle> ?subtitle .
  }
}"""
    )


def test_translate_optional_relationship_wraps_child_subtree(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    field_node = _root_field("{ persons { name employer { name } } }")
    result = translate_query(person_shape, field_node, relationship_registry)
    assert result.query.render() == (
        """SELECT ?iri ?name ?employer_iri ?employer_name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  OPTIONAL {
    ?iri <http://example.org/employer> ?employer_iri .
    ?employer_iri a <http://example.org/Company> .
    ?employer_iri <http://example.org/name> ?employer_name .
  }
}"""
    )
    employer_iri, employer_map = result.var_map.relationships["employer"]
    assert employer_iri == Variable("employer_iri")
    assert employer_map.fields == {"name": Variable("employer_name")}


def test_translate_sh_node_relationship_omits_type_triple(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    field_node = _root_field("{ persons { address { street } } }")
    result = translate_query(person_shape, field_node, relationship_registry)
    assert result.query.render() == (
        """SELECT ?iri ?address_iri ?address_street
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/address> ?address_iri .
    ?address_iri <http://example.org/street> ?address_street .
  }
}"""
    )
    assert "a <http://example.org/Address>" not in result.query.render()


# --- Nesting and recursion ---


def test_translate_recursive_relationship_uses_distinct_subject_vars(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    field_node = _root_field("{ persons { knows { name knows { name } } } }")
    result = translate_query(person_shape, field_node, relationship_registry)
    assert result.query.render() == (
        """SELECT ?iri ?knows_iri ?knows_name ?knows_knows_iri ?knows_knows_name
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/knows> ?knows_iri .
    ?knows_iri a <http://example.org/Person> .
    ?knows_iri <http://example.org/name> ?knows_name .
    OPTIONAL {
      ?knows_iri <http://example.org/knows> ?knows_knows_iri .
      ?knows_knows_iri a <http://example.org/Person> .
      ?knows_knows_iri <http://example.org/name> ?knows_knows_name .
    }
  }
}"""
    )
    knows_iri, knows_map = result.var_map.relationships["knows"]
    nested_iri, _ = knows_map.relationships["knows"]
    assert knows_iri == Variable("knows_iri")
    assert nested_iri == Variable("knows_knows_iri")


def test_translate_required_relationship_emits_bound_join(
    relationship_registry: ShapeRegistry,
) -> None:
    company = relationship_registry.by_type_name["Company"]
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        employer=relationship_property(
            "employer",
            company.iri,
            min_count=1,
            max_count=1,
            value_class=EX + "Company",
        ),
    )
    field_node = _root_field("{ persons { name employer { name } } }")
    result = translate_query(person, field_node, relationship_registry)
    assert result.query.render() == (
        """SELECT ?iri ?name ?employer_iri ?employer_name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/employer> ?employer_iri .
  ?employer_iri a <http://example.org/Company> .
  ?employer_iri <http://example.org/name> ?employer_name .
}"""
    )
    assert "OPTIONAL" not in result.query.render()


def test_translate_required_relationship_with_optional_child_scalar(
    relationship_registry: ShapeRegistry,
) -> None:
    company = relationship_registry.by_type_name["Company"]
    company_with_tag = shape_with(
        company,
        tag=scalar_property("tag", min_count=0, max_count=1),
    )
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        employer=relationship_property(
            "employer",
            company_with_tag.iri,
            min_count=1,
            max_count=1,
            value_class=EX + "Company",
        ),
    )
    custom_registry = ShapeRegistry([company_with_tag, person])
    field_node = _root_field("{ persons { name employer { name tag } } }")
    result = translate_query(person, field_node, custom_registry)
    assert result.query.render() == (
        """SELECT ?iri ?name ?employer_iri ?employer_name ?employer_tag
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/employer> ?employer_iri .
  ?employer_iri a <http://example.org/Company> .
  ?employer_iri <http://example.org/name> ?employer_name .
  OPTIONAL {
    ?employer_iri <http://example.org/tag> ?employer_tag .
  }
}"""
    )


# --- Additional errors and fragments ---


def test_translate_raises_when_relationship_has_no_value_shape(
    relationship_registry: ShapeRegistry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    broken = shape_with(
        person,
        employer=dataclasses.replace(
            person.property_shapes["employer"],
            value_shape_iri=None,
        ),
    )
    field_node = _root_field("{ persons { employer { name } } }")
    with pytest.raises(ValueError, match="no resolved value_shape_iri"):
        translate_query(broken, field_node, relationship_registry)


def test_translate_rejects_graphql_fragments(
    minimal_registry: ShapeRegistry,
) -> None:
    thing = minimal_registry.by_type_name["Thing"]
    field_node = _root_field("{ things { ... on Thing { label } } }")
    with pytest.raises(TypeError, match="fragments are not supported"):
        translate_query(thing, field_node, minimal_registry)
