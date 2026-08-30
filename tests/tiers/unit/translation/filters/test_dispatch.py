"""Top-level ``where`` argument dispatch — ``core/translation/filters/dispatch.py``.

Unit tier: ``translate_where_filter`` routing a ``where`` object through field
translation into ``FILTER`` graph patterns.

Order: scalar filter dispatch.
"""

from __future__ import annotations

from graphql.language.ast import ObjectValueNode

from fastshaql.core.sparql import FilterPattern
from fastshaql.core.translation.field_binding import bind_scalar_field
from fastshaql.core.translation.filters.context import RootFilterContext
from fastshaql.core.translation.filters.dispatch import translate_where_filter
from fastshaql.core.translation.filters.extract import extract_where_argument
from support.graphql_utils import root_field_node
from support.translation import translation_scope


def test_translate_where_filter_scalar(relationship_registry) -> None:
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    bind_scalar_field(
        "name", person.property_shapes["name"], scope, project=True, bound=True
    )
    where = extract_where_argument(
        root_field_node('query { persons(where: { name: { eq: "Alice" } }) { name } }')
    )
    assert isinstance(where, ObjectValueNode)
    ctx = RootFilterContext.from_scope(scope, isolated=False, selected=frozenset())
    patterns = translate_where_filter(where, ctx, person, relationship_registry)
    assert len(patterns) == 1
    assert isinstance(patterns[0], FilterPattern)
