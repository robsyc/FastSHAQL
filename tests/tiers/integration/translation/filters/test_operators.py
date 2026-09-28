"""Filter operator translation — ``core/translation/filters/``.

Integration tier: scalar and IRI operator emission. Golden ``eq`` cases live in
``tests/tiers/e2e/``; this module covers remaining operators.

Order: string operators, int operators, parametrized operator goldens, empty where,
datatype operators (boolean/decimal), IRI operator edge cases.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rdflib.namespace import XSD

from fastshaql.core.translation import translate_query
from support.builders import scalar_property, shape_with
from support.graphql_utils import root_field_node
from support.sparql_goldens import PERSON_NAME_ONLY_SPARQL

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry


def _unfiltered_title_baseline(
    filter_artwork_shape, filters_registry: ShapeRegistry
) -> str:
    """Rendered SPARQL for the same selection with no ``where`` — the baseline
    no-op filter results must match (the Artwork counterpart of
    ``PERSON_NAME_ONLY_SPARQL`` for the relationships set)."""
    return translate_query(
        filter_artwork_shape,
        root_field_node("{ artwork { title } }"),
        filters_registry,
    ).query.render()


@pytest.mark.parametrize(
    ("where_fragment", "filter_clause"),
    [
        ('title: { neq: "The Starry Night" }', 'FILTER(?title != "The Starry Night")'),
        ('title: { startsWith: "The" }', 'FILTER(STRSTARTS(?title, "The"))'),
        ('title: { endsWith: "Night" }', 'FILTER(STRENDS(?title, "Night"))'),
    ],
)
def test_translate_string_operator_filters(
    filter_artwork_shape,
    filters_registry: ShapeRegistry,
    where_fragment: str,
    filter_clause: str,
) -> None:
    query = f"{{ artwork(where: {{ {where_fragment} }}) {{ title }} }}"
    result = translate_query(
        filter_artwork_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert filter_clause in rendered
    assert rendered.startswith("SELECT ")


@pytest.mark.parametrize(
    ("where_fragment", "filter_clause"),
    [
        (
            "year: { gte: 1888 }",
            'FILTER(?year >= "1888"^^<http://www.w3.org/2001/XMLSchema#integer>)',
        ),
        (
            "year: { lte: 1940 }",
            'FILTER(?year <= "1940"^^<http://www.w3.org/2001/XMLSchema#integer>)',
        ),
    ],
)
def test_translate_int_operator_filters(
    filter_artwork_shape,
    filters_registry: ShapeRegistry,
    where_fragment: str,
    filter_clause: str,
) -> None:
    query = f"{{ artwork(where: {{ {where_fragment} }}) {{ title year }} }}"
    result = translate_query(
        filter_artwork_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert filter_clause in rendered
    assert "http://www.w3.org/2001/XMLSchema#integer" in rendered


@pytest.mark.parametrize(
    ("query", "golden"),
    [
        (
            '{ persons(where: { name: { contains: "Ali" } }) { name } }',
            """SELECT ?iri ?name
WHERE {
  ?iri a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(CONTAINS(?name, "Ali"))
}""",
        ),
        (
            '{ persons(where: { name: { regex: "^A" } }) { name } }',
            """SELECT ?iri ?name
WHERE {
  ?iri a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(REGEX(?name, "^A"))
}""",
        ),
        (
            '{ persons(where: { name: { in: ["Alice", "Bob"] } }) { name } }',
            """SELECT ?iri ?name
WHERE {
  ?iri a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(?name IN ("Alice", "Bob"))
}""",
        ),
        (
            '{ persons(where: { name: { notIn: ["Alice", "Bob"] } }) { name } }',
            """SELECT ?iri ?name
WHERE {
  ?iri a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(!(?name IN ("Alice", "Bob")))
}""",
        ),
        (
            '{ persons(where: { iri: { eq: "http://example.org/alice" } }) { name } }',
            """SELECT ?iri ?name
WHERE {
  ?iri a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(?iri = <http://example.org/alice>)
}""",
        ),
        (
            '{ persons(where: { name: { eq: "A", contains: "B" } }) { name } }',
            """SELECT ?iri ?name
WHERE {
  ?iri a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(?name = "A" && CONTAINS(?name, "B"))
}""",
        ),
    ],
    ids=["contains", "regex", "in", "not_in", "iri_eq", "multiple_operators"],
)
def test_translate_scalar_filter_operators(
    person_shape,
    relationship_registry: ShapeRegistry,
    query: str,
    golden: str,
) -> None:
    result = translate_query(
        person_shape, root_field_node(query), relationship_registry
    )
    assert result.query.render() == golden


def test_translate_empty_where_is_no_op(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    for query in ("{ persons(where: {}) { name } }", "{ persons { name } }"):
        result = translate_query(
            person_shape, root_field_node(query), relationship_registry
        )
        assert result.query.render() == PERSON_NAME_ONLY_SPARQL


# ---------------------------------------------------------------------------
# Datatype operators — boolean and decimal literal emission.
# ---------------------------------------------------------------------------


def test_translate_boolean_operator_filter(
    filter_artwork_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``onLoan: { eq: true }`` emits an xsd:boolean-typed comparison
    (canonical SPARQL ``BooleanLiteral`` form)."""
    query = "{ artwork(where: { onLoan: { eq: true } }) { title onLoan } }"
    result = translate_query(
        filter_artwork_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert "FILTER(?onLoan = true)" in rendered


def test_translate_decimal_operator_filter(
    person_shape,
    relationship_registry: ShapeRegistry,
) -> None:
    """``price: { gte: 9.99 }`` emits a decimal-typed comparison."""
    person = shape_with(
        person_shape,
        price=scalar_property("price", min_count=0, max_count=1, datatype=XSD.decimal),
    )
    query = "{ persons(where: { price: { gte: 9.99 } }) { name price } }"
    result = translate_query(person, root_field_node(query), relationship_registry)
    rendered = result.query.render()
    assert (
        'FILTER(?price >= "9.99"^^<http://www.w3.org/2001/XMLSchema#decimal>)'
        in rendered
    )


# ---------------------------------------------------------------------------
# IRI operator edge cases — empty operator object and membership list.
# ---------------------------------------------------------------------------


def test_translate_empty_iri_operator_is_no_op(
    filter_artwork_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``iri: {}`` carries no operators — no FILTER, matches baseline."""
    query = "{ artwork(where: { iri: {} }) { title } }"
    result = translate_query(
        filter_artwork_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert "FILTER" not in rendered
    assert rendered == _unfiltered_title_baseline(
        filter_artwork_shape, filters_registry
    )


def test_translate_iri_membership_filter(
    filter_artwork_shape,
    filters_registry: ShapeRegistry,
) -> None:
    """``iri: { in: [...] }`` emits an IRI membership filter."""
    query = (
        "{ artwork(where: { iri: { in: "
        '["http://example.org/starry-night", "http://example.org/water-lilies"] } }) { title } }'
    )
    result = translate_query(
        filter_artwork_shape, root_field_node(query), filters_registry
    )
    rendered = result.query.render()
    assert (
        "FILTER(?iri IN (<http://example.org/starry-night>, <http://example.org/water-lilies>))"
        in rendered
    )
