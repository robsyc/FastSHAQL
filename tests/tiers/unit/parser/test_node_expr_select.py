"""``sh:select`` / ``sh:sparqlExpr`` parsing — ``core/parser/node_expr``.

Unit tier: the SPARQL arms of ``sh:values`` — inline ``sh:sparqlExpr``
expressions (with parse-time prefix expansion) and ``sh:select`` bodies,
end-to-end through ``parse_shapes``. Select-body surgery lives in
``test_select_scan.py``; prefix declarations in ``test_shacl_prefixes.py``.
"""

from __future__ import annotations

from fastshaql.core.ir.node_expr import SelectNodeExpr, SparqlExprNodeExpr
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.node_expr import parse_node_expr
from fastshaql.core.parser.parse import parse_shapes
from support.builders import graph_with_values, thing_shape

# --- sh:sparqlExpr ---


def test_parse_sparql_expr() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [ sh:sparqlExpr "STRLEN(STR($this))" ] .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, SparqlExprNodeExpr)
    assert expr.expr == "STRLEN(STR($this))"


def test_parse_sparql_expr_expands_prefixes() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                sh:prefixes [
                    sh:declare [
                        sh:prefix "demo" ;
                        sh:namespace "http://example.org/demo/" ;
                    ] ;
                ] ;
                sh:sparqlExpr "EXISTS { $this demo:hasGoal ?g }" ;
            ] .
        """
    )
    expr = parse_node_expr(graph, prop)
    assert isinstance(expr, SparqlExprNodeExpr)
    assert expr.expr == "EXISTS { $this <http://example.org/demo/hasGoal> ?g }"


def test_derived_sparql_expr_parses_end_to_end() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:uriLength ;
            sh:datatype xsd:integer ;
            sh:maxCount 1 ;
            sh:values [ sh:sparqlExpr "STRLEN(STR($this))" ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    shape = registry.by_type_name["Thing"]
    prop = shape.property_shapes["uriLength"]

    assert isinstance(prop.values_expr, SparqlExprNodeExpr)
    assert prop.values_expr.expr == "STRLEN(STR($this))"


# --- sh:select ---


def test_parse_select_end_to_end() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:label ;
            sh:datatype xsd:string ;
            sh:values [
                sh:prefixes ex:prefixes ;
                sh:select \"\"\"
                    SELECT ?label
                    WHERE {
                        $this ex:givenName ?given .
                        $this ex:familyName ?family .
                        BIND(CONCAT(?given, ' ', ?family) AS ?label)
                    }\"\"\" ;
            ] ;
        ] .
        ex:prefixes a sh:ShapesGraph ;
        sh:declare [ sh:prefix "ex" ; sh:namespace "http://example.org/" ] .    """
    )
    registry = parse_shapes(load_shapes(turtle))
    shape = registry.by_type_name["Thing"]
    prop = shape.property_shapes["label"]

    assert isinstance(prop.values_expr, SelectNodeExpr)
    assert prop.values_expr.projection_var == "label"
    assert "BIND(CONCAT(?given" in prop.values_expr.body
    assert "$this" in prop.values_expr.body
    # Prefixes are expanded at parse time (ADR-0015): ex:givenName -> full IRI.
    assert "<http://example.org/givenName>" in prop.values_expr.body
