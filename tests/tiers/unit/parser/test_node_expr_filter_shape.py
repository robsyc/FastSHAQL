"""``shnex:filterShape`` parsing — ``core/parser/node_expr/filter_shape.py``.

Unit tier: the filter-shape arm — node- and property-level conjuncts
(``sh:pattern``, ``sh:hasValue``, class/datatype/rootClass, range bounds,
``sh:minCount 1``), union-vs-conjunction list semantics, malformed-input
rejections, distribution over ``shnex:if`` branches, and subject-scoped
conjunct scans (mutation hardening).
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Graph, Literal
from rdflib.namespace import SH, XSD

from fastshaql.core.ir.filter_shape import (
    FilterClass,
    FilterCompare,
    FilterConstraintIR,
    FilterDatatype,
    FilterHasValue,
    FilterMinCountOne,
    FilterProperty,
    FilterRegex,
    FilterRootClass,
    FilterShapeIR,
)
from fastshaql.core.ir.node_expr import (
    ConstantNodeExpr,
    ExistsNodeExpr,
    FilterShapeNodeExpr,
    IfNodeExpr,
    PathValuesNodeExpr,
)
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.node_expr import UnsupportedShapeError, parse_node_expr
from fastshaql.core.parser.node_expr.filter_shape import parse_filter_shape
from fastshaql.core.parser.parse import parse_shapes
from support.builders import EX, graph_with_values, thing_shape

# --- shnex:filterShape (ADR-0015) ---


def test_filter_shape_pattern_parses_at_node_level() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:pattern "^http://example.org/variant/" ;
                ] ;
            ] .
        """
    )
    assert parse_node_expr(graph, prop) == FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(
            conjuncts=(FilterRegex(pattern=Literal("^http://example.org/variant/")),)
        ),
    )


def test_filter_shape_pattern_with_flags_parses_at_property_level() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:code ;
                        sh:pattern "^A" ;
                        sh:flags "i" ;
                    ] ;
                ] ;
            ] .
        """
    )
    assert parse_node_expr(graph, prop) == FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(
            conjuncts=(
                FilterProperty(
                    path=PredicatePath(EX + "code"),
                    nested=FilterShapeIR(
                        conjuncts=(FilterRegex(Literal("^A"), Literal("i")),)
                    ),
                ),
            )
        ),
    )


@pytest.mark.parametrize(
    "constraint",
    [
        'sh:pattern "x" ; sh:pattern ex:NotALiteral',
        'sh:pattern "x" ; sh:flags ex:NotALiteral',
        'sh:pattern "x" ; sh:flags "i" ; sh:flags "s"',
    ],
    ids=["non-literal-pattern", "non-literal-flags", "multiple-flags"],
)
def test_filter_shape_pattern_malformed_values_raise(constraint: str) -> None:
    graph, prop = graph_with_values(
        f"""
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [ {constraint} ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:filterShape"):
        parse_node_expr(graph, prop)


def test_filter_shape_has_value_property_parses() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:gender ;
                        sh:hasValue "male" ;
                    ] ;
                ] ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(
            conjuncts=(
                FilterProperty(
                    path=PredicatePath(EX + "gender"),
                    nested=FilterShapeIR(conjuncts=(FilterHasValue(Literal("male")),)),
                ),
            )
        ),
    )


def test_filter_shape_over_if_distributes_into_branches() -> None:
    """``filterShape`` over an ``shnex:if`` normalises to an ``if`` over two
    filter shapes — the condition never reads the candidate values, so the
    filter distributes over branch selection and each branch keeps its own
    conjuncts (they would otherwise outlive the arm that binds them)."""
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [
                    shnex:if [ shnex:exists [ shnex:pathValues ex:review ] ] ;
                    shnex:then [ shnex:pathValues ex:reviewedTag ] ;
                    shnex:else [ shnex:pathValues ex:provisionalTag ] ;
                ] ;
                shnex:filterShape [ sh:class ex:Tag ] ;
            ] .
        """
    )
    shape = FilterShapeIR(conjuncts=(FilterClass((EX + "Tag",)),))
    assert parse_node_expr(graph, prop) == IfNodeExpr(
        cond=ExistsNodeExpr(
            inner=PathValuesNodeExpr(path=PredicatePath(EX + "review"))
        ),
        then=FilterShapeNodeExpr(
            nodes=PathValuesNodeExpr(path=PredicatePath(EX + "reviewedTag")),
            shape=shape,
        ),
        otherwise=FilterShapeNodeExpr(
            nodes=PathValuesNodeExpr(path=PredicatePath(EX + "provisionalTag")),
            shape=shape,
        ),
    )


def test_filter_shape_without_nodes_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:hasValue ex:x ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="shnex:nodes"):
        parse_node_expr(graph, prop)


def test_filter_shape_unknown_constraint_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:minLength 8 ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"shacl#minLength"):
        parse_node_expr(graph, prop)


def test_filter_shape_has_value_blank_node_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:hasValue [ ] ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:hasValue"):
        parse_node_expr(graph, prop)


def test_filter_shape_max_count_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:gender ;
                        sh:maxCount 1 ;
                    ] ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:maxCount"):
        parse_node_expr(graph, prop)


def test_filter_shape_nonliteral_range_bound_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:minInclusive ex:NotALiteral ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match=r"minInclusive.*not a literal"):
        parse_node_expr(graph, prop)


def test_filter_shape_deactivated_conjunct_raises() -> None:
    """``sh:deactivated`` inside a filter shape would be silently ignored —
    the conjunct would apply anyway, opposite of the declared intent."""
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [
                    sh:deactivated true ;
                    sh:hasValue "x" ;
                ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"shacl#deactivated.*not supported"
    ):
        parse_node_expr(graph, prop)


def test_filter_shape_min_count_two_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:gender ;
                        sh:minCount 2 ;
                    ] ;
                ] ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="sh:minCount 2"):
        parse_node_expr(graph, prop)


def test_filter_shape_min_count_one_parses() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:nodes [ shnex:pathValues ex:child ] ;
                shnex:filterShape [
                    sh:property [
                        sh:path ex:review ;
                        sh:minCount 1 ;
                    ] ;
                ] ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert isinstance(ir, FilterShapeNodeExpr)
    assert ir.shape.conjuncts == (
        FilterProperty(
            path=PredicatePath(EX + "review"),
            nested=FilterShapeIR(conjuncts=(FilterMinCountOne(),)),
        ),
    )


# --- Filter-shape conjunct coverage: term constraints and range bounds ---


@pytest.mark.parametrize(
    ("predicate", "value", "expected"),
    [
        ("sh:class", EX + "Class", FilterClass((EX + "Class",))),
        ("sh:datatype", EX + "DT", FilterDatatype(EX + "DT")),
    ],
)
def test_filter_shape_term_constraint_parses(predicate, value, expected) -> None:
    graph, prop = graph_with_values(
        f"""
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ {predicate} {value.n3()} ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == FilterShapeNodeExpr(
        nodes=ConstantNodeExpr(EX + "thing"),
        shape=FilterShapeIR(conjuncts=(expected,)),
    )


def _filter_shape_conjuncts(turtle: str) -> tuple[FilterConstraintIR, ...]:
    graph, prop = graph_with_values(turtle)
    ir = parse_node_expr(graph, prop)
    assert isinstance(ir, FilterShapeNodeExpr)
    return ir.shape.conjuncts


def test_filter_shape_class_list_parses_as_union() -> None:
    """``sh:class ( A B )`` — one conjunct holding the list: union within one
    value (Core §7.1.1 "use lists for union semantics")."""
    assert _filter_shape_conjuncts(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:class ( ex:Cat ex:Dog ) ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (FilterClass((EX + "Cat", EX + "Dog")),)


def test_filter_shape_class_nil_parses_as_empty_union() -> None:
    """``sh:class rdf:nil`` — the empty list is a legal single value (the
    class constraint matching nothing), distinct from a malformed list."""
    assert _filter_shape_conjuncts(
        """
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:class rdf:nil ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (FilterClass(()),)


def test_filter_shape_repeated_class_parses_as_conjunction() -> None:
    """Multiple ``sh:class`` triples — one conjunct each, AND-composed by the
    translator (Core §7.1.1: "multiple values ... are a conjunction")."""
    assert _filter_shape_conjuncts(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [
                    sh:class ex:Cat ;
                    sh:class ( ex:Dog ex:Owl ) ;
                ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (
        FilterClass((EX + "Cat",)),
        FilterClass((EX + "Dog", EX + "Owl")),
    )


def test_filter_shape_class_list_with_literal_member_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="not an IRI"):
        _filter_shape_conjuncts(
            """
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:class ( ex:Cat "Dog" ) ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


def test_filter_shape_class_list_malformed_rest_raises() -> None:
    """Class lists share the strict list walk — a rest chain ending anywhere
    but ``rdf:nil`` rejects loudly."""
    with pytest.raises(UnsupportedShapeError, match=r"well-formed.*neither rdf:nil"):
        _filter_shape_conjuncts(
            """
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [
                        sh:class [
                            rdf:first ex:Cat ;
                            rdf:rest ex:notANode ;
                        ] ;
                    ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


def test_filter_shape_class_literal_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="not an IRI or SHACL list of IRIs"):
        _filter_shape_conjuncts(
            """
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:class "Cat" ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


def test_filter_shape_datatype_literal_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="must be IRIs"):
        _filter_shape_conjuncts(
            """
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:datatype "string" ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


@pytest.mark.parametrize(
    "value",
    ["ex:Animal", "( ex:Animal ex:Plant )"],
)
def test_filter_shape_root_class_parses(value: str) -> None:
    """``sh:rootClass`` (Core §7.9.4) — same IRI-or-list syntax as sh:class."""
    expected = {
        "ex:Animal": FilterRootClass((EX + "Animal",)),
        "( ex:Animal ex:Plant )": FilterRootClass((EX + "Animal", EX + "Plant")),
    }[value]
    assert _filter_shape_conjuncts(
        f"""
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:rootClass {value} ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    ) == (expected,)


def test_filter_shape_root_class_literal_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="not an IRI or SHACL list of IRIs"):
        _filter_shape_conjuncts(
            """
            ex:prop a sh:PropertyShape ;
                sh:values [
                    shnex:filterShape [ sh:rootClass "Animal" ] ;
                    shnex:nodes ex:thing ;
                ] .
            """
        )


@pytest.mark.parametrize(
    ("predicate", "op"),
    [
        ("sh:minInclusive", ">="),
        ("sh:maxInclusive", "<="),
        ("sh:minExclusive", ">"),
        ("sh:maxExclusive", "<"),
    ],
)
def test_filter_shape_range_bound_parses(predicate, op) -> None:
    graph, prop = graph_with_values(
        f"""
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ {predicate} 10 ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    ir = parse_node_expr(graph, prop)
    assert ir == FilterShapeNodeExpr(
        nodes=ConstantNodeExpr(EX + "thing"),
        shape=FilterShapeIR(conjuncts=(FilterCompare(op, Literal(10)),)),
    )


# --- Filter-shape malformed-input rejections ---


def test_filter_shape_named_shape_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape ex:NamedShape ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="blank-node shape"):
        parse_node_expr(graph, prop)


def test_filter_shape_property_without_path_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:property [ sh:hasValue "x" ] ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="without sh:path"):
        parse_node_expr(graph, prop)


def test_filter_shape_property_with_multiple_paths_raises() -> None:
    """A filter conjunct follows §3.3 too — no silent pick among paths."""
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [
                    sh:property [
                        sh:path ex:label , ex:name ;
                        sh:hasValue "x" ;
                    ] ;
                ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="Multiple sh:path values"):
        parse_node_expr(graph, prop)


def test_filter_shape_node_level_min_count_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:minCount 1 ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="only supported inside"):
        parse_node_expr(graph, prop)


def test_derived_list_field_filter_shape_over_constant_raises() -> None:
    """A single-valued ``shnex:nodes`` arm cannot honour list cardinality —
    the error names the composite arm."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:filtered ;
            sh:datatype xsd:string ;
            sh:values [
                shnex:filterShape [ sh:hasValue "x" ] ;
                shnex:nodes ex:thing ;
            ] ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"filterShape over constant"):
        parse_shapes(load_shapes(turtle))


def test_filter_shape_non_blank_property_raises() -> None:
    graph, prop = graph_with_values(
        """
        ex:prop a sh:PropertyShape ;
            sh:values [
                shnex:filterShape [ sh:property ex:NamedProperty ] ;
                shnex:nodes ex:thing ;
            ] .
        """
    )
    with pytest.raises(UnsupportedShapeError, match="must be a blank node"):
        parse_node_expr(graph, prop)


# --- filter-shape conjunct scoping (mutation-hardening batch) ---


def test_filter_shape_conjuncts_never_leak_from_sibling_nodes() -> None:
    """Conjunct scans are subject-scoped: a sibling node's class, datatype,
    range, flags, and hasValue triples must never enter the target's IR."""
    graph = Graph()
    target, sibling = BNode("target"), BNode("sibling")
    graph.add((target, SH["class"], EX + "Disease"))
    graph.add((target, SH.pattern, Literal("^A")))
    graph.add((sibling, SH["class"], EX + "Other"))
    graph.add((sibling, SH.datatype, XSD.date))
    graph.add((sibling, SH.minInclusive, Literal(1)))
    graph.add((sibling, SH.flags, Literal("i")))
    graph.add((sibling, SH.hasValue, EX + "Alpha"))
    assert parse_filter_shape(graph, target) == FilterShapeIR(
        conjuncts=(FilterClass((EX + "Disease",)), FilterRegex(Literal("^A"), None))
    )


def test_filter_shape_rejects_unknown_predicate_after_known_one() -> None:
    graph = Graph()
    shape = BNode("shape")
    graph.add((shape, SH["class"], EX + "Disease"))
    graph.add((shape, EX + "bogus", Literal("x")))
    with pytest.raises(UnsupportedShapeError, match="bogus"):
        parse_filter_shape(graph, shape)
