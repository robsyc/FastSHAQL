"""Derived-field boundary wiring for ``sh:values`` — ``core/parser/parse.py``.

Unit tier: the property-shape boundary around derived fields — one
``sh:values`` per property, the ``sh:datatype`` requirement, derived
relationship and enum anchors, list-cardinality arm discipline, the
predicate-``sh:path`` rule for host predicates, and the read-ignored
``sh:minCount`` warning. The expression arms themselves live in the sibling
``test_node_expr_*.py`` files.
"""

from __future__ import annotations

import logging

import pytest
from rdflib import Literal

from fastshaql.core.ir.node_expr import (
    ConstantListNodeExpr,
    ConstantNodeExpr,
    IfNodeExpr,
    SelectNodeExpr,
)
from fastshaql.core.ir.property_shape import ValueSource, ValueType
from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.node_expr import UnsupportedShapeError
from fastshaql.core.parser.parse import parse_shapes
from support.builders import thing_shape

# --- Boundary raises (property_shape wiring) ---


def test_multiple_values_raises() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:values "FastshaqlEMR" ;
            sh:values "OtherEMR" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="more than one sh:values"):
        parse_shapes(load_shapes(turtle))


def test_derived_without_datatype_raises() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    with pytest.raises(
        UnsupportedShapeError,
        match=(
            r"derived field 'recordSource' on urn:fastshaql:inline:ThingRecordSource "
            r"requires sh:datatype"
        ),
    ):
        parse_shapes(load_shapes(turtle))


@pytest.mark.parametrize("anchor", ["sh:class ex:Other", "sh:node ex:OtherShape"])
def test_derived_plus_relationship_anchor_is_derived_relationship(
    anchor: str,
) -> None:
    """``sh:values`` + ``sh:class``/``sh:node`` is a derived relationship —
    supported (ADR-0015); (RELATIONSHIP, DERIVED)."""
    turtle = thing_shape(
        f"""sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            {anchor} ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.value_type is ValueType.RELATIONSHIP
    assert prop.source is ValueSource.DERIVED


def test_derived_sparql_expr_list_raises() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:tags ;
            sh:datatype xsd:string ;
            sh:values [ sh:sparqlExpr "STRLEN(STR($this))" ] ;
        ] ."""
    )
    with pytest.raises(
        UnsupportedShapeError, match=r"uses sh:sparqlExpr.*multi-valued arm"
    ):
        parse_shapes(load_shapes(turtle))


def test_derived_constant_list_raises() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:tags ;
            sh:datatype xsd:string ;
            sh:values "only-one" ;
        ] ."""
    )
    with pytest.raises(
        UnsupportedShapeError,
        # The remediation names the multi-valued arms, exact terms.
        match=r"shnex:pathValues, shnex:ListExpression",
    ):
        parse_shapes(load_shapes(turtle))


def test_derived_select_list_parses() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:tags ;
            sh:datatype xsd:string ;
            sh:minCount 0 ;
            sh:values [
                sh:select \"\"\"
                    SELECT ?tag
                    WHERE { $this ex:tag ?tag }
                \"\"\";
            ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["tags"]
    assert isinstance(prop.values_expr, SelectNodeExpr)
    assert prop.kind.is_list


@pytest.mark.parametrize("host_predicate", ["sh:values", "sh:defaultValue"])
def test_composite_path_plus_host_predicate_raises(host_predicate: str) -> None:
    """SHACL Core §3.3: values for ``sh:values``/``sh:defaultValue`` require a
    predicate ``sh:path``."""
    turtle = thing_shape(
        f"""sh:property [
            sh:path ( ex:first ex:last ) ;
            sh:codeIdentifier "fullName" ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            {host_predicate} "FastshaqlEMR" ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match="predicate"):
        parse_shapes(load_shapes(turtle))


def test_derived_with_datatype_parses_values_expr() -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    shape = registry.by_type_name["Thing"]
    prop = shape.property_shapes["recordSource"]
    assert isinstance(prop.values_expr, ConstantNodeExpr)
    assert prop.values_expr.value == Literal("FastshaqlEMR")


# --- Boundary warnings ---


def test_derived_plus_in_is_derived_enum() -> None:
    """``sh:values`` + ``sh:in`` is a derived enum — (ENUM, DERIVED) — no
    read-ignored warning (ADR-0015)."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:maxCount 1 ;
            sh:in ( "a" "b" ) ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.value_type is ValueType.ENUM
    assert prop.source is ValueSource.DERIVED


def test_derived_min_count_warns(caplog: pytest.LogCaptureFixture) -> None:
    turtle = thing_shape(
        """sh:property [
            sh:path ex:recordSource ;
            sh:datatype xsd:string ;
            sh:minCount 1 ;
            sh:maxCount 1 ;
            sh:values "FastshaqlEMR" ;
        ] ."""
    )
    with caplog.at_level(logging.WARNING):
        registry = parse_shapes(load_shapes(turtle))
    ignored = [r for r in caplog.records if "minCount" in r.message]
    assert len(ignored) == 1
    # The warning names the field and its shape, and states the retained
    # cardinality — ignored for validation, still emitted.
    message = ignored[0].getMessage()
    assert "sh:minCount on derived field 'recordSource'" in message
    assert "urn:fastshaql:inline:ThingRecordSource" in message
    assert "min_count=1" in message
    prop = registry.by_type_name["Thing"].property_shapes["recordSource"]
    assert prop.min_count == 1


# --- Derived list fields ---


def test_derived_list_field_with_list_expression_parses() -> None:
    """A ListExpression honours list cardinality (multi-valued capable)."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:flavors ;
            sh:datatype xsd:string ;
            sh:values ( "sweet" "umami" ) ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["flavors"]
    assert isinstance(prop.values_expr, ConstantListNodeExpr)
    assert prop.kind.is_list


def test_derived_list_field_if_over_multi_valued_branch_parses() -> None:
    """An ``shnex:if`` with any multi-valued branch honours list cardinality."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:links ;
            sh:datatype xsd:string ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
                shnex:then [ shnex:pathValues ex:reviewedLink ] ;
                shnex:else [ shnex:pathValues ex:provisionalLink ] ;
            ] ;
        ] ."""
    )
    registry = parse_shapes(load_shapes(turtle))
    prop = registry.by_type_name["Thing"].property_shapes["links"]
    assert isinstance(prop.values_expr, IfNodeExpr)
    assert prop.kind.is_list


def test_derived_list_field_if_over_constants_raises() -> None:
    """An ``shnex:if`` over only single-valued branches cannot honour list
    cardinality — the error names the arm."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:statuses ;
            sh:datatype xsd:string ;
            sh:values [
                shnex:if [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
                shnex:then "reviewed" ;
                shnex:else "provisional" ;
            ] ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"uses shnex:if"):
        parse_shapes(load_shapes(turtle))


def test_derived_list_field_bare_exists_raises() -> None:
    """A bare ``shnex:exists`` is single-valued (total boolean) — the list
    cardinality error names the arm."""
    turtle = thing_shape(
        """sh:property [
            sh:path ex:flags ;
            sh:datatype xsd:boolean ;
            sh:values [ shnex:exists [ shnex:pathValues ex:reviewed ] ] ;
        ] ."""
    )
    with pytest.raises(UnsupportedShapeError, match=r"uses shnex:exists"):
        parse_shapes(load_shapes(turtle))
