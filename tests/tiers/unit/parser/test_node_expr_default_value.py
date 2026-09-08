"""``sh:defaultValue`` parsing — the value-nodes step-3 fallback (ADR-0015).

Unit tier: ``sh:defaultValue`` alone and behind ``sh:values``; the default as
a node expression (every statically single-valued arm); the scalar-only,
single-cardinality, and ``sh:datatype`` requirements.
"""

from __future__ import annotations

import pytest
from rdflib import Literal

from fastshaql.core.ir.node_expr import (
    ConstantNodeExpr,
    ExistsNodeExpr,
    IfNodeExpr,
    NodeExprIR,
    PathValuesNodeExpr,
    SparqlExprNodeExpr,
)
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.node_expr import UnsupportedShapeError
from fastshaql.core.parser.parse import parse_shapes
from support.builders import EX, thing_shape

# --- sh:defaultValue (value-nodes step 3, ADR-0015) ---


def test_default_value_constant_parses() -> None:
    """``sh:defaultValue`` alone: asserted path + step-3 fallback — the IR
    carries ``default_expr`` beside ``values_expr=None`` (ADR-0015)."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue "fallback" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.values_expr is None
    assert prop.default_expr == ConstantNodeExpr(Literal("fallback"))


def test_default_value_with_values_parses_both() -> None:
    """``sh:values`` + ``sh:defaultValue``: the fallback sits behind the
    derived values (value-nodes steps 2 then 3)."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue "fallback" ;
            sh:values [ shnex:pathValues ex:source ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert isinstance(prop.values_expr, PathValuesNodeExpr)
    assert prop.default_expr == ConstantNodeExpr(Literal("fallback"))


@pytest.mark.parametrize(
    ("default_body", "expected"),
    [
        ('"fallback"', ConstantNodeExpr(Literal("fallback"))),
        (
            "[ sh:sparqlExpr \"CONCAT('ref-', STR($this))\" ]",
            SparqlExprNodeExpr("CONCAT('ref-', STR($this))"),
        ),
        (
            "[ shnex:exists [ shnex:pathValues ex:flag ] ]",
            ExistsNodeExpr(PathValuesNodeExpr(path=PredicatePath(EX + "flag"))),
        ),
        (
            (
                "[ shnex:if [ shnex:exists [ shnex:pathValues ex:flag ] ] ;"
                ' shnex:then "flagged" ; shnex:else "plain" ]'
            ),
            IfNodeExpr(
                cond=ExistsNodeExpr(
                    PathValuesNodeExpr(path=PredicatePath(EX + "flag"))
                ),
                then=ConstantNodeExpr(Literal("flagged")),
                otherwise=ConstantNodeExpr(Literal("plain")),
            ),
        ),
    ],
    ids=["constant", "sparql-expr", "exists", "nested-if"],
)
def test_default_value_expression_parses(
    default_body: str, expected: NodeExprIR
) -> None:
    """The default is a node expression — every statically single-valued
    arm (constants, ``sh:sparqlExpr``, ``shnex:exists``, nested
    single-valued ``shnex:if``) parses."""
    turtle = thing_shape(
        f"""sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue {default_body} ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.default_expr == expected


def test_default_value_twice_raises() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue "a" ;
            sh:defaultValue "b" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="more than one sh:defaultValue"):
        parse_shapes(load_shapes(turtle))


def test_default_value_multivalued_arm_raises() -> None:
    """A multi-valued default expression cannot honour the single-value
    fallback — the same statically-single-valued discipline as ``shnex:if``
    branches (ADR-0015)."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:defaultValue [ shnex:pathValues ex:source ] ;
        ] ."""
    )
    with pytest.raises(
        UnsupportedShapeError,
        match=(
            r"sh:defaultValue on urn:fastshaql:inline:ThingRecordSource "
            r"field 'recordSource' uses .*"
            r"the fallback must be statically single-valued$"
        ),
    ):
        parse_shapes(load_shapes(turtle))


def test_default_value_relationship_raises() -> None:
    """Scalar-only (ADR-0015): a defaulted relationship would need
    per-entity set-emptiness over join rows — not flat-expressible."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:parent ;
            sh:class ex:Thing ;
            sh:maxCount 1 ;
            sh:defaultValue ex:someThing ;
        ] ."""
    )
    with pytest.raises(
        UnsupportedShapeError,
        match=(
            r"sh:defaultValue on urn:fastshaql:inline:ThingParent field 'parent' "
            r"is scalar-only \(a defaulted relationship"
        ),
    ):
        parse_shapes(load_shapes(turtle))


def test_default_value_without_datatype_raises() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:maxCount 1 ;
            sh:defaultValue "fallback" ;
        ] ."""
    )
    with pytest.raises(
        UnsupportedShapeError,
        match=(
            r"sh:defaultValue on urn:fastshaql:inline:ThingRecordSource "
            r"field 'recordSource' requires sh:datatype"
        ),
    ):
        parse_shapes(load_shapes(turtle))


@pytest.mark.parametrize(
    "max_count_clause", ["", " ; sh:maxCount 2"], ids=["no_max_count", "max_count_2"]
)
def test_default_value_list_cardinality_raises(max_count_clause: str) -> None:
    """List cardinality + default = multi-valued fallback — rejected, both
    when ``sh:maxCount`` is absent and when it exceeds 1."""
    turtle = thing_shape(
        f"""sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:defaultValue "fallback"{max_count_clause} ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"maxCount 1"):
        parse_shapes(load_shapes(turtle))
