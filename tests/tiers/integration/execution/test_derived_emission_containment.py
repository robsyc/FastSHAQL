"""Derived-emission containment regressions — the ADR-0026 fabrication
hazard, executed through the full pipeline.

A row-keeping node-expression arm can keep a solution with the child or
candidate unbound — without containment, a following guard triple re-binds
the variable freely and fabricates children, filter matches, or candidates.
Three routes run end-to-end: selection-driven, ``where``-driven, and the
in-expression ``shnex:filterShape`` conjuncts.
"""

from __future__ import annotations

from graphql import graphql

from fastshaql.core.execution import InMemoryStore, ResolverContext
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser import parse_shapes
from fastshaql.executable import build_executable_schema


async def _query(shapes: str, data: str, query: str) -> dict:
    """Run *query* through the full pipeline against *shapes* over *data*,
    asserting a clean ``data`` payload."""
    registry = parse_shapes(load_shapes(shapes))
    result = await graphql(
        build_executable_schema(registry),
        query,
        context_value=ResolverContext(store=InMemoryStore(load_shapes(data))),
    )
    assert result.errors is None, result.errors
    payload = result.formatted["data"]
    assert payload is not None
    return payload


async def test_derived_row_keeping_arm_does_not_fabricate_children() -> None:
    """The containment fix (ADR-0026 hazard): a then-only ``shnex:if``
    emission keeps the solution with the child unbound — without the
    projecting sub-SELECT, the membership guard re-binds the child freely
    and every member instance in the graph becomes this article's child."""
    shapes = """
    @prefix ex: <http://example.org/> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    ex:ParagraphShape a sh:NodeShape ; sh:codeIdentifier "Paragraph" ;
        sh:targetClass ex:Paragraph ;
        sh:property [ sh:path ex:text ; sh:datatype xsd:string ] .
    ex:ImageShape a sh:NodeShape ; sh:codeIdentifier "Image" ;
        sh:targetClass ex:Image ;
        sh:property [ sh:path ex:url ; sh:datatype xsd:string ] .
    ex:ArticleShape a sh:NodeShape ; sh:codeIdentifier "Article" ;
        sh:targetClass ex:Article ;
        sh:property [ sh:path ex:title ; sh:datatype xsd:string ] ;
        sh:property [
            sh:path ex:related ;
            sh:or ( [ sh:class ex:Paragraph ] [ sh:node ex:ImageShape ] ) ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:flag ] ] ;
                shnex:then [ shnex:pathValues ex:friend ]
            ]
        ] .
    """
    data = """
    @prefix ex: <http://example.org/> .
    ex:para-1 a ex:Paragraph ; ex:text "stray paragraph" .
    ex:img-1 a ex:Image ; ex:url "https://example.org/stray.png" .
    # No ex:flag, no ex:friend — the if yields nothing for this article.
    ex:article-1 a ex:Article ; ex:title "Empty" .
    """
    payload = await _query(
        shapes,
        data,
        "query { article { title related "
        "{ ... on Paragraph { text } ... on Image { url } } } }",
    )
    (article,) = payload["article"]
    assert article["title"] == ["Empty"]
    assert article["related"] == []


async def test_derived_filter_row_keeping_arm_does_not_fabricate_matches() -> None:
    """The filter-path containment fix (same ADR-0026 hazard, the ``where``
    route): a then-only ``shnex:if`` emission keeps the solution with the
    child unbound — without containment, the typing guard inside
    ``FILTER EXISTS`` re-binds the child freely and any Person named Alice
    fabricates Bob's friend."""
    shapes = """
    @prefix ex: <http://example.org/> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    ex:PersonShape a sh:NodeShape ; sh:codeIdentifier "Person" ;
        sh:targetClass ex:Person ;
        sh:property [ sh:path ex:name ;
            sh:datatype xsd:string ] ;
        sh:property [
            sh:path ex:friend ;
            sh:class ex:Person ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:flag ] ] ;
                shnex:then [ shnex:pathValues ex:knows ]
            ]
        ] .
    """
    data = """
    @prefix ex: <http://example.org/> .
    ex:alice a ex:Person ; ex:name "Alice" .
    # No ex:flag, no ex:knows — the if yields nothing for Bob.
    ex:bob a ex:Person ; ex:name "Bob" .
    ex:carol a ex:Person ; ex:name "Carol" ;
        ex:flag true ; ex:knows ex:alice .
    """
    payload = await _query(
        shapes,
        data,
        'query { person(where: { friend: { name: { eq: "Alice" } } }) { name } }',
    )
    names = [p["name"] for p in payload["person"]]
    assert names == [["Carol"]]


async def test_filter_shape_select_arm_does_not_fabricate_candidates() -> None:
    """The in-expression containment (same ADR-0026 hazard, the
    ``shnex:filterShape`` route): an author ``sh:select`` body may leave its
    projection unbound (an ``OPTIONAL`` — "the advisor, when present") —
    uncontained, the ``sh:class`` conjunct triple re-binds the unbound
    candidate freely and every Senior in the graph becomes the advisorless
    article's reviewer."""
    shapes = """
    @prefix ex: <http://example.org/> .
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    ex:SeniorShape a sh:NodeShape ; sh:codeIdentifier "Senior" ;
        sh:targetClass ex:Senior ;
        sh:property [ sh:path ex:name ; sh:datatype xsd:string ] .
    ex:ArticleShape a sh:NodeShape ; sh:codeIdentifier "Article" ;
        sh:targetClass ex:Article ;
        sh:property [ sh:path ex:title ; sh:datatype xsd:string ] ;
        sh:property [
            sh:path ex:reviewer ;
            sh:node ex:SeniorShape ;
            sh:values [
                shnex:filterShape [ sh:class ex:Senior ] ;
                shnex:nodes [
                    sh:select "SELECT ?reviewer WHERE { OPTIONAL { $this ex:advisor ?reviewer } }"
                ]
            ]
        ] .
    """
    data = """
    @prefix ex: <http://example.org/> .
    ex:alice a ex:Senior ; ex:name "Alice" .
    # Dan is a Senior but nobody's advisor — uncontained he would fabricate.
    ex:dan a ex:Senior ; ex:name "Dan" .
    ex:a1 a ex:Article ; ex:title "WithAdvisor" ; ex:advisor ex:alice .
    ex:a2 a ex:Article ; ex:title "NoAdvisor" .
    """
    payload = await _query(
        shapes, data, "query { article { title reviewer { name } } }"
    )
    reviewers = {
        article["title"][0]: [r["name"] for r in article["reviewer"]]
        for article in payload["article"]
    }
    assert reviewers == {"WithAdvisor": [["Alice"]], "NoAdvisor": []}
