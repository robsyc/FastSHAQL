"""Derived-target semantics — ``core/parser/node_expr/semantics.py``.

Unit tier: rule-chaining rejections (ADR-0015 deviation 5a) — any
node-expression position reading a predicate carried by another derived
property shape, including composite-path walks and nested property conjuncts —
plus the derived-target scan edges (mutation hardening).
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import SH

from fastshaql.core.ir.filter_shape import FilterProperty, FilterShapeIR
from fastshaql.core.ir.node_expr import (
    ConstantNodeExpr,
    ExistsNodeExpr,
    FilterShapeNodeExpr,
    IfNodeExpr,
    PathValuesNodeExpr,
)
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.node_expr import UnsupportedShapeError
from fastshaql.core.parser.node_expr.semantics import reject_derived_path_targets
from fastshaql.core.parser.parse import parse_shapes
from fastshaql.core.parser.util.namespaces import SH_VALUES
from support.builders import EX, thing_shape

# --- Rule chaining (ADR-0015 deviation 5a) ---


_DERIVED_FLAG_PROPERTY = """
    sh:property [
        sh:path ex:derivedFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values "constant" ;
    ] ;
"""


@pytest.mark.parametrize(
    ("test_id", "consumer_property"),
    [
        (
            "path_values",
            """
    sh:property [
        sh:path ex:chained ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues ex:derivedFlag ] ;
    ] .
""",
        ),
        (
            "filter_shape_conjunct",
            """
    sh:property [
        sh:path ex:conjunct ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [
                sh:property [
                    sh:path ex:derivedFlag ;
                    sh:hasValue "keep" ;
                ] ;
            ] ;
            shnex:nodes [ shnex:pathValues ex:thing ] ;
        ] ;
    ] .
""",
        ),
        (
            "filter_shape_nodes_arm",
            """
    sh:property [
        sh:path ex:filtered ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [ sh:hasValue "x" ] ;
            shnex:nodes [ shnex:pathValues ex:derivedFlag ] ;
        ] ;
    ] .
""",
        ),
        (
            "if_branch",
            """
    sh:property [
        sh:path ex:chosen ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
            shnex:then [ shnex:pathValues ex:derivedFlag ] ;
            shnex:else "none" ;
        ] ;
    ] .
""",
        ),
        (
            "if_exists_condition",
            """
    sh:property [
        sh:path ex:chosen ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:if [ shnex:exists [ shnex:pathValues ex:derivedFlag ] ] ;
            shnex:then "yes" ;
            shnex:else "no" ;
        ] ;
    ] .
""",
        ),
        (
            "bare_exists",
            """
    sh:property [
        sh:path ex:hasFlag ;
        sh:datatype xsd:boolean ;
        sh:maxCount 1 ;
        sh:values [ shnex:exists [ shnex:pathValues ex:derivedFlag ] ] ;
    ] .
""",
        ),
    ],
)
def test_expression_targeting_derived_property_raises(
    test_id: str,  # noqa: ARG001 — naming-only parameter
    consumer_property: str,
) -> None:
    """Rule chaining (ADR-0015 deviation 5a): any node-expression position
    reading a predicate carried by another derived property shape rejects
    loudly — a derived property's asserted triples are ignored under
    replace-not-union, so the read would be silently empty or stale.
    Parametrized over every walkable position: ``pathValues`` paths,
    ``filterShape`` conjunct paths and ``nodes`` arms, ``shnex:if``
    branches and conditions, and bare ``shnex:exists`` values."""
    turtle = thing_shape(
        f"""{_DERIVED_FLAG_PROPERTY}
            {consumer_property}"""
    )
    with pytest.raises(
        UnsupportedShapeError,
        # The rejection names the consuming field and its property shape.
        match=(
            r"derived field '\w+' on urn:fastshaql:inline:Thing\S* "
            r"reads derived property"
        ),
    ):
        parse_shapes(load_shapes(turtle))


@pytest.mark.parametrize(
    ("test_id", "consumer_property"),
    [
        (
            "inverse_path",
            """
    sh:property [
        sh:path ex:inverseFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:inversePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "zero_or_more_path",
            """
    sh:property [
        sh:path ex:closureFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:zeroOrMorePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "one_or_more_path",
            """
    sh:property [
        sh:path ex:plusFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:oneOrMorePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "zero_or_one_path",
            """
    sh:property [
        sh:path ex:optionalFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues [ sh:zeroOrOnePath ex:derivedFlag ] ] ;
    ] .
    """,
        ),
        (
            "nested_modifier_path",
            """
    sh:property [
        sh:path ex:nestedFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:pathValues [ sh:zeroOrMorePath [ sh:inversePath ex:derivedFlag ] ]
        ] ;
    ] .
    """,
        ),
        (
            "sequence_path",
            """
    sh:property [
        sh:path ex:sequenceFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [ shnex:pathValues ( ex:reviewed ex:derivedFlag ) ] ;
    ] .
    """,
        ),
        (
            "alternative_path",
            """
    sh:property [
        sh:path ex:eitherFlag ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:pathValues [ sh:alternativePath ( ex:reviewed ex:derivedFlag ) ]
        ] ;
    ] .
    """,
        ),
        (
            "filter_shape_conjunct_inverse",
            """
    sh:property [
        sh:path ex:conjunctInverse ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [
                sh:property [
                    sh:path [ sh:inversePath ex:derivedFlag ] ;
                    sh:hasValue "keep" ;
                ] ;
            ] ;
            shnex:nodes [ shnex:pathValues ex:thing ] ;
        ] ;
    ] .
    """,
        ),
        (
            "filter_shape_conjunct_sequence",
            """
    sh:property [
        sh:path ex:conjunctSequence ;
        sh:datatype xsd:string ;
        sh:maxCount 1 ;
        sh:values [
            shnex:filterShape [
                sh:property [
                    sh:path ( ex:reviewed ex:derivedFlag ) ;
                    sh:hasValue "keep" ;
                ] ;
            ] ;
            shnex:nodes [ shnex:pathValues ex:thing ] ;
        ] ;
    ] .
    """,
        ),
    ],
)
def test_composite_path_targeting_derived_property_raises(
    test_id: str,  # noqa: ARG001 — naming-only parameter
    consumer_property: str,
) -> None:
    """The rule-chaining walk must descend into composite paths (SHACL §4):
    unary modifiers, sequences, and alternatives yield their inner
    predicates to :func:`iter_path_predicates`, so a derived predicate
    anywhere inside a composite path rejects just like a bare one —
    at ``shnex:pathValues`` positions and in ``filterShape`` conjuncts."""
    turtle = thing_shape(
        f"""{_DERIVED_FLAG_PROPERTY}
            {consumer_property}"""
    )
    with pytest.raises(UnsupportedShapeError, match="rule chaining"):
        parse_shapes(load_shapes(turtle))


def test_if_without_then_walk_skips_absent_branch() -> None:
    """``shnex:if`` requires only one of ``shnex:then``/``shnex:else`` — the
    rule-chaining walk must skip the absent arm (no paths to walk) and still
    walk the present one."""
    turtle = thing_shape(
        """
        sh:property [
            sh:path ex:chosen ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
                shnex:else "none" ;
            ] ;
        ] .
    """
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["chosen"]
    assert prop.values_expr == IfNodeExpr(
        cond=ExistsNodeExpr(
            inner=PathValuesNodeExpr(path=PredicatePath(EX + "reviewed"))
        ),
        then=None,
        otherwise=ConstantNodeExpr(Literal("none")),
    )


# --- parser scoping and rule-chaining edges (mutation-hardening batch) ---


@pytest.mark.parametrize(
    "path_chain",
    [(EX + "salary",), (EX + "employed", EX + "salary")],
    ids=["one_level", "two_levels"],
)
def test_rule_chaining_through_nested_property_conjuncts_rejected(
    path_chain: tuple[str, ...],
) -> None:
    """The chaining guard recurses through nested ``sh:property`` conjuncts —
    a derived path at any nesting depth is still rejected."""
    graph = Graph()
    derived = BNode("derivedShape")
    graph.add((derived, SH.path, EX + "salary"))
    graph.add((derived, SH_VALUES, Literal("derived")))
    shape = FilterShapeIR(conjuncts=())
    for path in reversed(path_chain):
        shape = FilterShapeIR(
            conjuncts=(FilterProperty(path=PredicatePath(URIRef(path)), nested=shape),)
        )
    ir = FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "employed")),
        shape=shape,
    )
    with pytest.raises(UnsupportedShapeError, match="rule chaining"):
        reject_derived_path_targets(graph, ir, EX + "Shape", "score")


def test_derived_target_scan_requires_a_path_predicate() -> None:
    """Only ``sh:path`` declarations count as property shapes — an object
    position match under any other predicate is not a derived target."""
    graph = Graph()
    decoy = BNode("decoy")
    graph.add((decoy, EX + "mentions", EX + "name"))
    graph.add((decoy, SH_VALUES, Literal("x")))
    reject_derived_path_targets(
        graph, PathValuesNodeExpr(path=PredicatePath(EX + "name")), EX + "S", "f"
    )
