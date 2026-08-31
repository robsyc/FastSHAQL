"""Derived-enum execution — SD-9 serialization and filter row selection.

Execution tier: the two behaviours that only surface through GraphQL
execution — ``where``-filters actually selecting entities by their
*derived* enum value, and values outside ``sh:in`` dying at serialization
(SD-9) for derived and defaulted enums alike.
"""

from __future__ import annotations

from graphql import graphql
from rdflib import Graph

from fastshaql.core.execution import InMemoryStore, ResolverContext
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.parse import parse_shapes
from fastshaql.core.translation import translate_query
from fastshaql.executable import build_executable_schema
from support.cases import data_graph_for, registry_for
from support.graphql_utils import root_field_node


async def test_derived_enum_filter_executes_against_derived_binding() -> None:
    """Execution-level counterpart of the render test in
    ``integration/translation/test_derived_enum.py``: the rendered
    ``FILTER`` actually selects the entities whose *derived* enum value
    matches — v1/v3/v5 (review + reviewedTag → ``curated``), excluding
    v7 (unreviewed despite its stale ``reviewedTag``) and v6
    (reviewed but tagless → ``confirmed``)."""
    registry = registry_for("node_expr")
    shape = registry.by_type_name["Variant"]
    result = translate_query(
        shape,
        root_field_node("{ variants(where: {curationStatus: {eq: CURATED}}) { iri } }"),
        registry,
    )
    store = InMemoryStore(data_graph_for("node_expr"))
    rows = await store.query(result.query.render())
    iris = {str(row["iri"]) for row in rows}
    assert iris == {
        "http://example.org/genomics/v1",
        "http://example.org/genomics/v3",
        "http://example.org/genomics/v5",
    }


SHAPES = """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:ThingShape a sh:NodeShape ;
    sh:codeIdentifier "Thing" ;
    sh:targetClass ex:Thing ;
    sh:property [
        sh:path ex:status ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:in ( "ok" "broken" ) ;
        sh:values [ shnex:pathValues ex:rawStatus ] ;
    ] ;
    sh:property [
        sh:path ex:grade ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:in ( "a" "b" ) ;
        sh:defaultValue "unlisted" ;
    ] .
"""

DATA = """
@prefix ex: <http://example.org/> .
ex:t1 a ex:Thing ; ex:rawStatus "ok" ; ex:grade "a" .
ex:t2 a ex:Thing ; ex:rawStatus "undefined-in-shacl-in" .
"""


async def test_derived_enum_value_outside_sh_in_dies_at_serialization() -> None:
    """A derived value outside ``sh:in`` has no enum NAME — serialization
    raises a ``GraphQLError`` naming the value (SD-9), rather than silently
    passing an unlisted term through."""
    registry = parse_shapes(load_shapes(SHAPES))
    schema = build_executable_schema(registry)
    store = InMemoryStore(Graph().parse(data=DATA, format="turtle"))
    ctx = ResolverContext(store=store)
    result = await graphql(schema, "{ thing { status } }", context_value=ctx)
    assert result.errors is not None
    assert any("undefined-in-shacl-in" in e.message for e in result.errors)


async def test_defaulted_enum_value_outside_sh_in_dies_at_serialization() -> None:
    """A defaulted enum carries the same stance (ADR-0015):
    the fallback flows through NAME-mapping, and a default outside ``sh:in``
    dies at serialization — t2 has no asserted grade, so its serialized value
    is the unlisted default."""
    registry = parse_shapes(load_shapes(SHAPES))
    schema = build_executable_schema(registry)
    store = InMemoryStore(Graph().parse(data=DATA, format="turtle"))
    ctx = ResolverContext(store=store)
    result = await graphql(schema, "{ thing { grade } }", context_value=ctx)
    assert result.errors is not None
    assert any("unlisted" in e.message for e in result.errors)


async def test_derived_enum_in_sh_in_values_serialize() -> None:
    """The in-set control: same shape, only in-set values — no errors, NAMEs.
    Also pins the defaulted-enum happy path: t1's asserted ``grade "a"`` wins
    over the default and serializes through the NAME mapping."""
    registry = parse_shapes(load_shapes(SHAPES))
    schema = build_executable_schema(registry)
    store = InMemoryStore(
        Graph().parse(
            data='@prefix ex: <http://example.org/> .\nex:t1 a ex:Thing ; ex:rawStatus "ok" ; ex:grade "a" .',
            format="turtle",
        )
    )
    ctx = ResolverContext(store=store)
    result = await graphql(schema, "{ thing { status grade } }", context_value=ctx)
    assert result.errors is None
    assert result.data == {"thing": [{"status": "OK", "grade": "A"}]}
