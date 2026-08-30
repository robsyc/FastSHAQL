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
)

from fastshaql.core.translation.filters.context import RootFilterContext
from fastshaql.core.translation.filters.fields import translate_fields
from support.translation import translation_scope


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
