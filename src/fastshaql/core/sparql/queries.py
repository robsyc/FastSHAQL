"""SPARQL query templates — SELECT (§16.1).

See: https://www.w3.org/TR/sparql12-query/#select
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .terms import render_term

if TYPE_CHECKING:
    from rdflib import URIRef, Variable

    from .patterns import GroupPattern


def _validate_solution_modifiers(limit: int | None, offset: int | None) -> None:
    """Reject negative LIMIT/OFFSET values (SPARQL §15.5 / §15.4)."""
    if limit is not None and limit < 0:
        raise ValueError("LIMIT may not be negative (SPARQL §15.5)")
    if offset is not None and offset < 0:
        raise ValueError("OFFSET must be non-negative (SPARQL §15.4)")


@dataclasses.dataclass(frozen=True)
class SelectQuery:
    """``SELECT … WHERE { … }`` — SPARQL §16.1 / nested SubSelect §12."""

    projection: tuple[Variable, ...]
    """Variables to project in the SELECT clause."""

    where: GroupPattern
    """The WHERE clause body."""

    distinct: bool = False
    """When ``True``, emit ``SELECT DISTINCT`` (§15.3)."""

    order_by: tuple[Variable, ...] = ()
    """``ORDER BY`` variables (§15.1)."""

    limit: int | None = None
    """``LIMIT`` clause value (§15.5 — must be non-negative)."""

    offset: int | None = None
    """``OFFSET`` clause value (§15.4 / §18.2 ``Slice`` — must be non-negative)."""

    as_subquery: bool = False
    """When ``True``, wrap the rendered body in ``{ … }`` for nested SubSelect (§12)."""

    from_default: tuple[URIRef, ...] = ()
    """``FROM`` dataset clauses for the default graph (grammar [9]; top-level only)."""

    def __post_init__(self) -> None:
        _validate_solution_modifiers(self.limit, self.offset)

    def render(self, indent: int = 0) -> str:
        """Render as ``SELECT … WHERE { … }`` with optional solution modifiers (top-level or as subquery)."""
        # Keyword and projection
        select_kw = "SELECT DISTINCT" if self.distinct else "SELECT"
        proj = " ".join(render_term(v) for v in self.projection)

        # Indentation setup
        pad = "  " * indent if self.as_subquery else ""
        content_indent = indent + 1 if self.as_subquery else 0
        cp = "  " * content_indent if self.as_subquery else ""

        # WHERE clause body. When nested, render at ``content_indent`` so the
        # inner triples and closing brace pick up the subquery's pad, then strip
        # the leading pad off the brace — the ``WHERE`` keyword supplies it.
        where_body = (
            self.where.render(content_indent).lstrip()
            if self.as_subquery
            else self.where.render()
        )
        where_line = f"{cp}WHERE {where_body}"

        # Optional clauses
        order_line = (
            f"{cp}ORDER BY {' '.join(render_term(v) for v in self.order_by)}"
            if self.order_by
            else ""
        )
        limit_line = f"{cp}LIMIT {self.limit}" if self.limit is not None else ""
        offset_line = f"{cp}OFFSET {self.offset}" if self.offset is not None else ""

        from_lines = (
            [f"{cp}FROM {render_term(iri)}" for iri in self.from_default]
            if not self.as_subquery
            else []
        )

        # Assemble body (for both top-level and subquery cases)
        body = "\n".join(
            filter(
                None,
                [
                    f"{cp}{select_kw} {proj}",
                    *from_lines,
                    where_line,
                    order_line,
                    limit_line,
                    offset_line,
                ],
            )
        )

        if self.as_subquery:
            return f"{pad}{{\n{body}\n{pad}}}"
        return body
