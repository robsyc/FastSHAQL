"""Language-preference chain translation (ADR-0012).

Integration tier: ``QueryContext.lang_tags``, chain lowering through
``translate_query`` — required/optional scalars (steps + ``COALESCE`` +
``BOUND``), the union terminal, nested relationship inheritance, promotion
and pagination re-emission, and ``FILTER EXISTS`` internals.

Order: langString filter ops → chain selection → union terminal → union-field filter → nested inheritance → promotion/pagination re-emission → EXISTS internals.
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from rdflib.namespace import RDF, XSD

from fastshaql.core.kernel.constants import DIR_LANG_STRING
from fastshaql.core.kernel.context import QueryContext
from fastshaql.core.translation import translate_query
from support.builders import registry_with, scalar_property, shape_with
from support.graphql_utils import root_field_node
from support.sparql_goldens import PERSON_NAME_ONLY_SPARQL

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry


def test_translate_lang_string_filter_wraps_str(
    relationship_registry: ShapeRegistry,
) -> None:
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        name=scalar_property("name", min_count=1, max_count=1, datatype=RDF.langString),
    )
    query = '{ persons(where: { name: { eq: "Alice" } }) { name } }'
    result = translate_query(person, root_field_node(query), relationship_registry)
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(STR(?name) = "Alice")
}"""
    assert result.query.render() == golden


def test_translate_dir_lang_string_filter_compares_as_plain_string(
    relationship_registry: ShapeRegistry,
) -> None:
    """``rdf:dirLangString`` compares as a plain string too — the RHS must
    be an untyped ``xsd:string`` literal against the ``STR()``-wrapped
    left-hand side, never a dirLangString-typed one."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        name=scalar_property(
            "name", min_count=1, max_count=1, datatype=DIR_LANG_STRING
        ),
    )
    query = '{ persons(where: { name: { eq: "Alice" } }) { name } }'
    result = translate_query(person, root_field_node(query), relationship_registry)
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  FILTER(STR(?name) = "Alice")
}"""
    assert result.query.render() == golden


def test_translate_required_lang_string_under_chain_steps_bind_bound(
    relationship_registry: ShapeRegistry,
) -> None:
    """S2 — a required langString under a chain lowers as steps +
    ``BIND(COALESCE)`` + ``FILTER(BOUND)``: "required" means "the chain
    resolves"; the guard sits outside any wrap."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        name=scalar_property("name", min_count=1, max_count=1, datatype=RDF.langString),
    )
    query = "{ persons { name } }"
    result = translate_query(
        person,
        root_field_node(query),
        relationship_registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/name> ?_l0_name .
    FILTER(langMatches(LANG(?_l0_name), "en"))
  }
  BIND(COALESCE(?_l0_name) AS ?name)
  FILTER(BOUND(?name))
}"""
    assert result.query.render() == golden


def test_translate_no_query_context_lang_unchanged(
    relationship_registry: ShapeRegistry,
) -> None:
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        name=scalar_property("name", min_count=1, max_count=1, datatype=RDF.langString),
    )
    query = "{ persons { name } }"
    result = translate_query(person, root_field_node(query), relationship_registry)
    assert result.query.render() == PERSON_NAME_ONLY_SPARQL


def test_translate_lang_and_where_filter_on_lang_string_separate_clauses(
    relationship_registry: ShapeRegistry,
) -> None:
    """The ``where`` operator compares the resolved (post-``BIND``)
    variable via ``STR()`` — the value the client would see."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        name=scalar_property("name", min_count=1, max_count=1, datatype=RDF.langString),
    )
    query = '{ persons(where: { name: { eq: "Alice" } }) { name } }'
    result = translate_query(
        person,
        root_field_node(query),
        relationship_registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/name> ?_l0_name .
    FILTER(langMatches(LANG(?_l0_name), "en"))
  }
  BIND(COALESCE(?_l0_name) AS ?name)
  FILTER(BOUND(?name))
  FILTER(STR(?name) = "Alice")
}"""
    assert result.query.render() == golden


def test_translate_two_entry_chain_steps_in_order(
    relationship_registry: ShapeRegistry,
) -> None:
    """A two-entry chain: steps in chain order, one ``COALESCE`` over both
    — first step with a value wins the field."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        bio=scalar_property("bio", min_count=0, max_count=1, datatype=RDF.langString),
    )
    query = "{ persons { bio } }"
    result = translate_query(
        person,
        root_field_node(query),
        relationship_registry,
        query_context=QueryContext(lang_tags=("en", "nl")),
    )
    golden = """SELECT ?iri ?bio
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/bio> ?_l0_bio .
    FILTER(langMatches(LANG(?_l0_bio), "en"))
  }
  OPTIONAL {
    ?iri <http://example.org/bio> ?_l1_bio .
    FILTER(langMatches(LANG(?_l1_bio), "nl"))
  }
  BIND(COALESCE(?_l0_bio, ?_l1_bio) AS ?bio)
}"""
    assert result.query.render() == golden


def test_translate_union_field_appends_untagged_terminal(
    relationship_registry: ShapeRegistry,
) -> None:
    """S3 — a string-union Property under ``("en",)`` gains the implicit
    untagged terminal as the last step (``LANG(?v) = ""``)."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        note=scalar_property(
            "note",
            min_count=0,
            max_count=1,
            datatype=None,
            datatypes=(XSD.string, RDF.langString),
        ),
    )
    query = "{ persons { note } }"
    result = translate_query(
        person,
        root_field_node(query),
        relationship_registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    golden = """SELECT ?iri ?note
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/note> ?_l0_note .
    FILTER(langMatches(LANG(?_l0_note), "en"))
  }
  OPTIONAL {
    ?iri <http://example.org/note> ?_l1_note .
    FILTER(LANG(?_l1_note) = "")
  }
  BIND(COALESCE(?_l0_note, ?_l1_note) AS ?note)
}"""
    assert result.query.render() == golden


def test_translate_union_field_filter_compares_resolved_value(
    relationship_registry: ShapeRegistry,
) -> None:
    """A ``where`` operator over a string-union Property compares the
    resolved value: chain + implicit untagged terminal, ``BOUND`` guard,
    then the ``STR()``-wrapped comparison — tagged or plain, the client
    compares the lexical form."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        note=scalar_property(
            "note",
            min_count=0,
            max_count=1,
            datatype=None,
            datatypes=(XSD.string, RDF.langString),
        ),
    )
    query = '{ persons(where: { note: { eq: "hi" } }) { note } }'
    result = translate_query(
        person,
        root_field_node(query),
        relationship_registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    golden = """SELECT ?iri ?note
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/note> ?_l0_note .
    FILTER(langMatches(LANG(?_l0_note), "en"))
  }
  OPTIONAL {
    ?iri <http://example.org/note> ?_l1_note .
    FILTER(LANG(?_l1_note) = "")
  }
  BIND(COALESCE(?_l0_note, ?_l1_note) AS ?note)
  FILTER(BOUND(?note))
  FILTER(STR(?note) = "hi")
}"""
    assert result.query.render() == golden


def test_translate_nested_relationship_lang_string_filter(
    relationship_registry: ShapeRegistry,
) -> None:
    """The chain inherits into relationship children (one chain, every
    nesting depth)."""
    company = shape_with(
        relationship_registry.by_type_name["Company"],
        bio=scalar_property("bio", min_count=0, max_count=1, datatype=RDF.langString),
    )
    registry = registry_with(relationship_registry, company)
    person = registry.by_type_name["Person"]
    query = "{ persons { employer { bio } } }"
    result = translate_query(
        person,
        root_field_node(query),
        registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    golden = """SELECT ?iri ?employer_iri ?employer_bio
WHERE {
  ?iri a <http://example.org/Person> .
  OPTIONAL {
    ?iri <http://example.org/employer> ?employer_iri .
    ?employer_iri a <http://example.org/Company> .
    OPTIONAL {
      ?employer_iri <http://example.org/bio> ?_l0_employer_bio .
      FILTER(langMatches(LANG(?_l0_employer_bio), "en"))
    }
    BIND(COALESCE(?_l0_employer_bio) AS ?employer_bio)
  }
}"""
    assert result.query.render() == golden


def test_translate_promoted_lang_string_list_emits_union_filter(
    relationship_registry: ShapeRegistry,
) -> None:
    """S6 — a promoted langString *list* keeps the single-variable
    union-filter form; a single-entry chain renders the identical single
    ``langMatches`` predicate as the single-tag form did."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        bio=scalar_property(
            "bio", min_count=0, max_count=None, datatype=RDF.langString
        ),
    )
    query = '{ persons(where: { bio: { eq: "Hello" } }) { name } }'
    result = translate_query(
        person,
        root_field_node(query),
        relationship_registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    golden = """SELECT ?iri ?name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/bio> ?bio .
  FILTER(langMatches(LANG(?bio), "en"))
  FILTER(STR(?bio) = "Hello")
}"""
    assert result.query.render() == golden


def test_translate_pagination_reemits_chain_and_bound_guard(
    relationship_registry: ShapeRegistry,
) -> None:
    """Pagination's inner sub-SELECT re-emits the selected field's bind as
    the full chain lowering (steps + ``BIND`` + ``BOUND``) so the filter
    constrains the paginated entity set (ADR-0010 + ADR-0012)."""
    person = shape_with(
        relationship_registry.by_type_name["Person"],
        name=scalar_property("name", min_count=1, max_count=1, datatype=RDF.langString),
    )
    query = '{ persons(where: { name: { eq: "Alice" } }, limit: 2) { name } }'
    result = translate_query(
        person,
        root_field_node(query),
        relationship_registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    chain = """  OPTIONAL {
    ?iri <http://example.org/name> ?_l0_name .
    FILTER(langMatches(LANG(?_l0_name), "en"))
  }
  BIND(COALESCE(?_l0_name) AS ?name)
  FILTER(BOUND(?name))"""
    golden = f"""SELECT ?iri ?name
WHERE {{
  {{
    SELECT DISTINCT ?iri
    WHERE {{
      ?iri a <http://example.org/Person> .
{textwrap.indent(chain, "    ")}
      FILTER(STR(?name) = "Alice")
    }}
    ORDER BY ?iri
    LIMIT 2
  }}
{chain}
}}"""
    assert result.query.render() == golden


def test_translate_filter_exists_emits_chain_on_rf_variable(
    relationship_registry: ShapeRegistry,
) -> None:
    """``FILTER EXISTS`` internals re-use the chain lowering on the fresh
    ``_rf_``-prefixed variable (steps + ``BIND`` + ``BOUND`` inside the
    exists group — a failing ``BOUND`` eliminates the exists solution)."""
    company = shape_with(
        relationship_registry.by_type_name["Company"],
        bio=scalar_property("bio", min_count=0, max_count=1, datatype=RDF.langString),
    )
    registry = registry_with(relationship_registry, company)
    person = registry.by_type_name["Person"]
    query = (
        '{ persons(where: { employer: { bio: { eq: "Hello" } } }) { name '
        "employer { name } } }"
    )
    result = translate_query(
        person,
        root_field_node(query),
        registry,
        query_context=QueryContext(lang_tags=("en",)),
    )
    golden = """SELECT ?iri ?name ?employer_iri ?employer_name
WHERE {
  ?iri a <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
  ?iri <http://example.org/employer> ?employer_iri .
  ?employer_iri a <http://example.org/Company> .
  ?employer_iri <http://example.org/name> ?employer_name .
  FILTER(EXISTS {
    ?employer_iri a <http://example.org/Company> .
    OPTIONAL {
      ?employer_iri <http://example.org/bio> ?_l0__rf_employer_bio .
      FILTER(langMatches(LANG(?_l0__rf_employer_bio), "en"))
    }
    BIND(COALESCE(?_l0__rf_employer_bio) AS ?_rf_employer_bio)
    FILTER(BOUND(?_rf_employer_bio))
    FILTER(STR(?_rf_employer_bio) = "Hello")
  })
}"""
    assert result.query.render() == golden
