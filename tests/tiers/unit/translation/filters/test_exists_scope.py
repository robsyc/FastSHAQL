"""Filter context strategies — ``core/translation/filters/exists_scope.py``.

Unit tier: ``RootFilterContext`` flat vs isolated scalar-var re-emission, and
``ExistsContext`` relationship-filter variable allocation.

Order: root flat scalar var → root isolated re-emit → EXISTS relationship re-emit → EXISTS scalar var → EXISTS child scope.
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
    SelectQuery,
    TriplePattern,
)
from fastshaql.core.translation.field_binding import FieldBindings
from fastshaql.core.translation.filters.exists_scope import (
    ExistsContext,
    RootFilterContext,
)
from fastshaql.core.translation.variables import (
    RelationshipBinding,
    VariableMap,
)
from support.builders import derived_property
from support.cases import registry_for
from support.translation import translation_scope

# --- Root flat scalar var ---


def test_root_filter_context_flat_scalar_var_no_patterns(
    relationship_registry,
) -> None:
    scope = translation_scope(relationship_registry)
    scope.fields["name"] = Variable("name")
    ctx = RootFilterContext.from_scope(scope, bindings=FieldBindings())
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
    bindings = FieldBindings(isolated=True)
    bindings.note_selected("name")
    ctx = RootFilterContext.from_scope(scope, bindings=bindings)
    prop = relationship_registry.by_type_name["Person"].property_shapes["name"]
    _, patterns = ctx.scalar_var("name", prop)
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)


# --- EXISTS relationship re-emit ---


def test_root_filter_context_isolated_relationship_reemit(
    relationship_registry,
) -> None:
    """The isolated re-emission is the guarded link alone — the typing guard
    lives inside the EXISTS block, never duplicated at the re-emission site
    (ADR-0026 containment)."""
    person = relationship_registry.by_type_name["Person"]
    employer_prop = person.property_shapes["employer"]
    scope = translation_scope(relationship_registry)
    join_var = Variable("employer_iri")
    scope.relationships["employer"] = RelationshipBinding.single(
        join_var, VariableMap(subject_var=join_var, fields={}, relationships={})
    )
    bindings = FieldBindings(isolated=True)
    bindings.note_selected("employer")
    ctx = RootFilterContext(
        subject=scope.subject,
        fields=scope.fields,
        relationships=scope.relationships,
        bindings=bindings,
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
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)
    assert isinstance(expr, ExistsExpr)


def test_nested_exists_derived_relationship_link_is_contained() -> None:
    """A derived link inside a nested EXISTS is contained — the inner EXISTS
    typing guard must never re-bind an unbound child (ADR-0026)."""
    registry = registry_for("derived_relationships")
    prop = registry.by_type_name["Member"].property_shapes["recommendedBooks"]
    ctx = ExistsContext(subject=Variable("member_iri"), rf_prefix="member")
    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="title"),
                value=ObjectValueNode(
                    fields=(
                        ObjectFieldNode(
                            name=NameNode(value="eq"),
                            value=StringValueNode(value="SPARQL 101"),
                        ),
                    )
                ),
            ),
        )
    )
    patterns, expr = ctx.translate_relationship(
        "recommendedBooks", node, prop, registry
    )
    assert len(patterns) == 1
    contained = patterns[0]
    assert isinstance(contained, SelectQuery)
    assert contained.projection == (
        Variable("member_iri"),
        Variable("member_recommendedBooks_iri"),
    )
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


def test_exists_context_child_scope_inherits_lang_tags() -> None:
    """A nested EXISTS scope keeps the request's language chain — scalar
    bindings inside it emit the same lang filters as the parent block —
    and grows the prefix chain with the nested field name."""
    parent = ExistsContext(
        subject=Variable("employer_iri"), rf_prefix="employer", lang_tags=("en",)
    )
    child = parent.child_scope(Variable("employer_department_iri"), "department")
    assert child.lang_tags == ("en",)
    assert child.rf_prefix == "employer_department"


def test_exists_context_child_scope_without_prefix_starts_chain() -> None:
    """A scope with an empty prefix seeds the chain at the field name —
    no leading underscore (the pipeline always seeds non-empty, this pins
    the guard)."""
    child = ExistsContext(subject=Variable("iri"), rf_prefix="").child_scope(
        Variable("department_iri"), "department"
    )
    assert child.rf_prefix == "department"
