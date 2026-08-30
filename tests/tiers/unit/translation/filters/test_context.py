"""Filter context strategies — ``core/translation/filters/context.py``.

Unit tier: ``RootFilterContext`` flat vs isolated scalar-var re-emission, and
``ExistsContext`` relationship-filter variable allocation.

Order: root flat scalar var → root isolated re-emit → EXISTS relationship re-emit → EXISTS scalar var.
"""

from __future__ import annotations

from graphql.language.ast import (
    NameNode,
    ObjectFieldNode,
    ObjectValueNode,
    StringValueNode,
)
from rdflib import Variable

from fastshaql.core.ir.node_expr import SelectNodeExpr
from fastshaql.core.sparql import (
    BindPattern,
    ExistsExpr,
    RawGraphPattern,
    TriplePattern,
)
from fastshaql.core.translation.filters.context import ExistsContext, RootFilterContext
from fastshaql.core.translation.variables import VariableMap
from support.builders import derived_property
from support.translation import translation_scope

# --- Root flat scalar var ---


def test_root_filter_context_flat_scalar_var_no_patterns(
    relationship_registry,
) -> None:
    scope = translation_scope(relationship_registry)
    scope.fields["name"] = Variable("name")
    ctx = RootFilterContext.from_scope(scope, isolated=False, selected=frozenset())
    prop = relationship_registry.by_type_name["Person"].property_shapes["name"]
    var, patterns = ctx.scalar_var("name", prop)
    assert var == Variable("name")
    assert patterns == []


# --- Root isolated re-emit ---


def test_root_filter_context_isolated_reemit_selected_scalar(
    relationship_registry,
) -> None:
    scope = translation_scope(relationship_registry)
    scope.fields["name"] = Variable("name")
    ctx = RootFilterContext.from_scope(
        scope, isolated=True, selected=frozenset({"name"})
    )
    prop = relationship_registry.by_type_name["Person"].property_shapes["name"]
    _, patterns = ctx.scalar_var("name", prop)
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)


# --- EXISTS relationship re-emit ---


def test_root_filter_context_isolated_relationship_reemit(
    relationship_registry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    employer_prop = person.property_shapes["employer"]
    scope = translation_scope(relationship_registry)
    join_var = Variable("employer_iri")
    scope.relationships["employer"] = (
        join_var,
        VariableMap(subject_var=join_var, fields={}, relationships={}),
    )
    ctx = RootFilterContext(
        subject=scope.subject,
        fields=scope.fields,
        relationships=scope.relationships,
        isolated=True,
        selected=frozenset({"employer"}),
    )
    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="name"),
                value=ObjectValueNode(
                    fields=(
                        ObjectFieldNode(
                            name=NameNode(value="eq"),
                            value=StringValueNode(value="Acme"),
                        ),
                    )
                ),
            ),
        )
    )
    patterns, expr = ctx.translate_relationship(
        "employer", node, employer_prop, relationship_registry
    )
    assert len(patterns) == 2
    assert all(isinstance(p, TriplePattern) for p in patterns)
    assert isinstance(expr, ExistsExpr)


# --- EXISTS scalar var ---


def test_exists_context_scalar_var_emits_rf_variable(
    relationship_registry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    prop = person.property_shapes["name"]
    ctx = ExistsContext(subject=Variable("employer_iri"), rf_prefix="employer")
    var, patterns = ctx.scalar_var("name", prop)
    assert var == Variable("_rf_employer_name")
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)


def test_exists_context_scalar_var_emits_derived_merge() -> None:
    """DERIVED arm inside EXISTS re-emits merged sh:select body, not a triple."""
    prop = derived_property(
        "mostSpecificClass",
        values_expr=SelectNodeExpr(
            body="$this <http://example.org/klass> ?v", projection_var="v"
        ),
        min_count=1,
        max_count=1,
    )
    ctx = ExistsContext(subject=Variable("hasCondition_iri"), rf_prefix="hasCondition")
    var, patterns = ctx.scalar_var("mostSpecificClass", prop)
    assert var == Variable("_rf_hasCondition_mostSpecificClass")
    assert any(isinstance(p, RawGraphPattern) for p in patterns)
    assert not any(isinstance(p, TriplePattern) for p in patterns)
    assert any(
        isinstance(p, BindPattern)
        and p.var == Variable("_rf_hasCondition_mostSpecificClass")
        for p in patterns
    )
