"""``where`` object field walking — ``core/translation/filters/fields.py``.

Unit tier: ``translate_fields`` dispatch across combinator and property fields,
including the empty-relationship-filter no-op relied on by root promotion.

Order: combinator branch no-op.
"""

from __future__ import annotations

from graphql.language.ast import (
    ListValueNode,
    NameNode,
    ObjectFieldNode,
    ObjectValueNode,
    StringValueNode,
)
from rdflib import Literal, URIRef, Variable

from fastshaql.core.sparql import (
    AndExpr,
    ExistsExpr,
    FilterPattern,
    GroupPattern,
    NotExpr,
    Pattern,
    PredicatePath,
    TermExpr,
    TriplePattern,
)
from fastshaql.core.translation.filters.context import (
    ExistsContext,
    RootFilterContext,
)
from fastshaql.core.translation.filters.fields import (
    _branch_to_expression,
    translate_fields,
)
from fastshaql.core.translation.variables import VariableMap
from support.translation import translation_scope

EX = URIRef("http://example.org/")


def test_combinator_branch_empty_relationship_filter_is_noop(
    relationship_registry,
) -> None:
    """Empty relationship filters inside combinators rely on root promotion."""
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    ctx = RootFilterContext.from_scope(scope, isolated=False, selected=frozenset())
    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="AND"),
                value=ListValueNode(
                    values=(
                        ObjectValueNode(
                            fields=(
                                ObjectFieldNode(
                                    name=NameNode(value="employer"),
                                    value=ObjectValueNode(fields=()),
                                ),
                            )
                        ),
                    )
                ),
            ),
        )
    )
    patterns, expr = translate_fields(node, person, ctx, relationship_registry)
    assert patterns == []
    assert expr is None


# --- branch wrapping and deep nesting (mutation-hardening batch) ---


def test_branch_with_patterns_and_expr_wraps_in_exists() -> None:
    """A filter branch carrying both join patterns and an expression becomes
    one ``EXISTS { patterns FILTER(expr) }`` — the group keeps them scoped."""
    patterns: list[Pattern] = [
        TriplePattern(Variable("s"), PredicatePath(EX + "p"), Variable("o"))
    ]
    expr = TermExpr(Literal(1))
    assert _branch_to_expression(patterns, expr) == ExistsExpr(
        GroupPattern((patterns[0], FilterPattern(expr)))
    )


def test_branch_without_patterns_returns_expr_directly() -> None:
    expr = TermExpr(Literal(1))
    assert _branch_to_expression([], expr) is expr


def test_branch_without_expr_is_a_noop() -> None:
    patterns: list[Pattern] = [
        TriplePattern(Variable("s"), PredicatePath(EX + "p"), Variable("o"))
    ]
    assert _branch_to_expression(patterns, None) is None


def test_deeply_nested_relationship_filters_resolve_targets(
    relationship_registry,
) -> None:
    """Three ``knows`` levels: the innermost relationship filter resolves its
    target shape through the registry threaded into the nested EXISTS walk."""
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    join_var = Variable("knows_iri")
    scope.relationships["knows"] = (
        join_var,
        VariableMap(subject_var=join_var, fields={}, relationships={}),
    )
    ctx = RootFilterContext.from_scope(scope, isolated=False, selected=frozenset())
    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="knows"),
                value=ObjectValueNode(
                    fields=(
                        ObjectFieldNode(
                            name=NameNode(value="knows"),
                            value=ObjectValueNode(
                                fields=(
                                    ObjectFieldNode(
                                        name=NameNode(value="knows"),
                                        value=ObjectValueNode(
                                            fields=(
                                                ObjectFieldNode(
                                                    name=NameNode(value="name"),
                                                    value=ObjectValueNode(
                                                        fields=(
                                                            ObjectFieldNode(
                                                                name=NameNode(
                                                                    value="eq"
                                                                ),
                                                                value=StringValueNode(
                                                                    value="Alice"
                                                                ),
                                                            ),
                                                        )
                                                    ),
                                                ),
                                            )
                                        ),
                                    ),
                                )
                            ),
                        ),
                    )
                ),
            ),
        )
    )
    patterns, expr = translate_fields(node, person, ctx, relationship_registry)
    assert patterns == []
    assert isinstance(expr, ExistsExpr)


def test_not_combinator_wraps_pattern_bearing_branch_in_exists(
    relationship_registry,
) -> None:
    """Inside an EXISTS scope a ``NOT`` branch carries bind triples plus its
    filter expression — the branch expression is the ``EXISTS`` of both."""
    person = relationship_registry.by_type_name["Person"]
    ctx = ExistsContext(subject=Variable("emp_iri"), rf_prefix="employer")
    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="NOT"),
                value=ObjectValueNode(
                    fields=(
                        ObjectFieldNode(
                            name=NameNode(value="name"),
                            value=ObjectValueNode(
                                fields=(
                                    ObjectFieldNode(
                                        name=NameNode(value="eq"),
                                        value=StringValueNode(value="Alice"),
                                    ),
                                )
                            ),
                        ),
                    )
                ),
            ),
        )
    )
    _, expr = translate_fields(node, person, ctx, relationship_registry)
    assert isinstance(expr, NotExpr)
    assert isinstance(expr.child, ExistsExpr)


def test_and_combinator_wraps_each_pattern_bearing_branch(
    relationship_registry,
) -> None:
    person = relationship_registry.by_type_name["Person"]
    ctx = ExistsContext(subject=Variable("emp_iri"), rf_prefix="employer")

    def _eq(value: str) -> ObjectValueNode:
        return ObjectValueNode(
            fields=(
                ObjectFieldNode(
                    name=NameNode(value="name"),
                    value=ObjectValueNode(
                        fields=(
                            ObjectFieldNode(
                                name=NameNode(value="eq"),
                                value=StringValueNode(value=value),
                            ),
                        )
                    ),
                ),
            )
        )

    node = ObjectValueNode(
        fields=(
            ObjectFieldNode(
                name=NameNode(value="AND"),
                value=ListValueNode(values=(_eq("Alice"), _eq("Bob"))),
            ),
        )
    )
    _, expr = translate_fields(node, person, ctx, relationship_registry)
    assert isinstance(expr, AndExpr)
    assert all(isinstance(child, ExistsExpr) for child in expr.children)
