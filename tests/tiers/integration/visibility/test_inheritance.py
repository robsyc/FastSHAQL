"""Node shape inheritance — visibility integration (ADR-0005).

Integration tier: inherited relationship to an EXCLUDED shape fails closed-world.
"""

from __future__ import annotations

import textwrap

import pytest
from rdflib import Graph

from fastshaql.core.parser import parse_shapes
from fastshaql.core.registry import VisibilityError

_PREFIXES = textwrap.dedent(
    """
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix ex: <http://example.org/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix graphql: <http://datashapes.org/graphql#> .
    """
)


def _graph(turtle_body: str) -> Graph:
    graph = Graph()
    graph.parse(data=_PREFIXES + turtle_body, format="turtle")
    return graph


def test_public_child_inherits_relationship_to_excluded_shape_raises() -> None:
    turtle = textwrap.dedent(
        """
        ex:ApiSchema a graphql:Schema ;
            graphql:publicShape ex:PublicChildShape ;
            graphql:privateShape ex:SecretShape .

        ex:SecretShape a sh:NodeShape ;
            sh:codeIdentifier "Secret" ;
            sh:targetClass ex:Secret ;
            sh:property [
                sh:path ex:label ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .

        ex:ParentShape a sh:NodeShape ;
            sh:codeIdentifier "Parent" ;
            sh:property [
                sh:path ex:secret ;
                sh:node ex:SecretShape ;
                sh:minCount 0 ;
                sh:maxCount 1
            ] .

        ex:PublicChildShape a sh:NodeShape ;
            sh:codeIdentifier "PublicChild" ;
            sh:targetClass ex:PublicChild ;
            sh:node ex:ParentShape ;
            sh:property [
                sh:path ex:name ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .
        """
    )
    with pytest.raises(VisibilityError, match=r"PublicChild\.secret.*SecretShape"):
        parse_shapes(_graph(turtle))
