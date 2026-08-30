"""Flat vs paginated WHERE clause assembly (ADR-0010)."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from fastshaql.core.sparql import GroupPattern, Pattern, SelectQuery

if TYPE_CHECKING:
    from rdflib import Variable


@dataclasses.dataclass(frozen=True)
class WhereParts:
    """Pattern bags produced before WHERE routing."""

    entity: tuple[Pattern, ...]
    """Root entity type-binding patterns."""
    selection: tuple[Pattern, ...]
    """Selection-walk patterns for projected fields."""
    promoted: tuple[Pattern, ...]
    """Direct-property bind patterns promoted from the filter layer."""
    filters: tuple[Pattern, ...]
    """Filter expressions and relationship ``FILTER EXISTS`` patterns."""


def assemble_where(
    parts: WhereParts,
    *,
    subject: Variable,
    paginate: bool,
    limit: int | None,
    offset: int | None,
) -> GroupPattern:
    """Route pattern bags into a flat or paginated inner sub-SELECT WHERE."""
    if paginate:
        inner_entity = (*parts.entity, *parts.promoted, *parts.filters)
        inner = SelectQuery(
            projection=(subject,),
            where=GroupPattern(children=inner_entity),
            distinct=True,
            order_by=(subject,),
            limit=limit,
            offset=offset,
            as_subquery=True,
        )
        return GroupPattern(children=(inner, *parts.selection))
    return GroupPattern(
        children=(
            *parts.entity,
            *parts.selection,
            *parts.promoted,
            *parts.filters,
        )
    )
