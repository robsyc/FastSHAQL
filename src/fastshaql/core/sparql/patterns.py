"""SPARQL graph pattern nodes — triple patterns, groups, and optionals (§5 and §6).

See:
- Triple patterns: https://www.w3.org/TR/sparql12-query/#QSynTriples
- Basic graph patterns: https://www.w3.org/TR/sparql12-query/#BasicGraphPatterns
- Group graph patterns: https://www.w3.org/TR/sparql12-query/#GroupPatterns
- Optional patterns: https://www.w3.org/TR/sparql12-query/#optionals
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from rdflib import Literal, URIRef, Variable

from .terms import RenderTerm, render_term

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .expressions import Expression
    from .paths import SparqlPropertyPath
    from .queries import SelectQuery

type Pattern = (
    TriplePattern
    | GroupPattern
    | OptionalPattern
    | FilterPattern
    | SelectQuery
    | BindPattern
    | ValuesPattern
    | RawGraphPattern
)
"""Union of renderable graph pattern nodes for ``GroupPattern.children``."""


@dataclasses.dataclass(frozen=True)
class TriplePattern:
    """``subject predicate object .`` — SPARQL §4.2."""

    subject: RenderTerm
    """Subject position — typically a ``Variable``."""

    predicate: SparqlPropertyPath | Variable
    """Predicate position — a ``SparqlPropertyPath`` or a ``Variable`` (e.g. cascade ``?p``)."""

    object: RenderTerm
    """Object position — a ``Variable``, ``URIRef``, or ``Literal``."""

    def render(self, indent: int = 0) -> str:
        """Render as indented triple with trailing ``.``."""
        pad = "  " * indent
        pred = self.predicate
        pred_str = render_term(pred) if isinstance(pred, Variable) else pred.render()
        return (
            f"{pad}{render_term(self.subject)} {pred_str} {render_term(self.object)} ."
        )


@dataclasses.dataclass(frozen=True)
class GroupPattern:
    """``{ pattern . pattern . ... }`` — SPARQL §5.2."""

    children: tuple[Pattern, ...]
    """Ordered child patterns rendered sequentially inside braces."""

    def render(self, indent: int = 0) -> str:
        """Render as indented ``{ ... }`` block. Empty groups render as ``""``."""
        if not self.children:
            return ""
        pad = "  " * indent
        inner = "\n".join(c.render(indent + 1) for c in self.children)
        return f"{pad}{{\n{inner}\n{pad}}}"


@dataclasses.dataclass(frozen=True)
class OptionalPattern:
    """``OPTIONAL { ... }`` — SPARQL §6."""

    child: GroupPattern
    """Inner group pattern rendered inside the optional block."""

    def render(self, indent: int = 0) -> str:
        """Render as indented ``OPTIONAL { ... }`` block."""
        if not self.child.children:
            return ""  # pragma: no cover — always constructed with non-empty patterns
        pad = "  " * indent
        inner = "\n".join(c.render(indent + 1) for c in self.child.children)
        return f"{pad}OPTIONAL {{\n{inner}\n{pad}}}"


@dataclasses.dataclass(frozen=True)
class FilterPattern:
    """``FILTER(expression)`` — SPARQL §17 (expression evaluation; see §5.2.2 scope)."""

    expression: Expression
    """Filter expression rendered inline inside ``FILTER(...)``."""

    def render(self, indent: int = 0) -> str:
        """Render as indented ``FILTER(...)``."""
        pad = "  " * indent
        expr = self.expression.render(indent)
        return f"{pad}FILTER({expr})"


@dataclasses.dataclass(frozen=True)
class BindPattern:
    """``BIND(expr AS ?var)`` — SPARQL §10.1.

    Distinct from :mod:`fastshaql.core.translation.field_binding` (field binding).
    """

    expr: Expression
    """Expression bound to *var*."""

    var: Variable
    """Target variable for the BIND assignment."""

    def render(self, indent: int = 0) -> str:
        """Render as indented ``BIND(expr AS ?var)``."""
        pad = "  " * indent
        return f"{pad}BIND({self.expr.render(indent)} AS {render_term(self.var)})"


@dataclasses.dataclass(frozen=True)
class ValuesPattern:
    """``VALUES ?var { t1 t2 … }`` — inline data block (SPARQL §10.2).

    The terms are fastshaql-allocated constants (never author text), rendered
    via :func:`render_term` per the typed-AST rule (ADR-0017).
    """

    var: Variable
    """The variable bound to each term in turn."""

    terms: tuple[URIRef | Literal, ...]
    """Constant terms — one solution row per term. IRIs and literals only: a
    variable is not a legal data-block value, and ``UNDEF`` has no IR form."""

    def render(self, indent: int = 0) -> str:
        """Render as an indented ``VALUES`` block, one term per line."""
        pad = "  " * indent
        inner = "\n".join(
            f"{'  ' * (indent + 1)}{render_term(term)}" for term in self.terms
        )
        return f"{pad}VALUES {render_term(self.var)} {{\n{inner}\n{pad}}}"


@dataclasses.dataclass(frozen=True)
class RawGraphPattern:
    """Trusted author graph-pattern text dissolved from ``sh:select`` (ADR-0015/0017).

    Each non-empty line is indented independently so merged bodies slot into
    enclosing ``GroupPattern`` blocks.
    """

    text: str
    """Author WHERE body with ``$this`` substituted when applicable."""

    def render(self, indent: int = 0) -> str:
        """Render each line at *indent*, preserving blank lines."""
        pad = "  " * indent
        return "\n".join(
            f"{pad}{line}" if line.strip() else line for line in self.text.splitlines()
        )


ROW_KEEPING = (OptionalPattern, BindPattern)
"""Patterns that cannot eliminate a solution row (SPARQL §10, §6): a
``BIND`` expression error leaves the variable unbound with the row
surviving, and ``OPTIONAL`` keeps the row by definition. Bags made solely
of these are solution-set-identical under an ``OPTIONAL`` wrap — which
``contain_row_eliminating`` exploits in both directions."""


def contain_row_eliminating(patterns: Sequence[Pattern]) -> list[Pattern]:
    """Wrap *patterns* in one ``OPTIONAL`` unless the bag is all row-keeping.

    The single home of the containment rule: a row-eliminating sub-emission
    (a conjunct ``FILTER``, a triple join) inside a value lane must fail to
    *no value*, never to *no row* — so it is contained in its own scoped
    ``OPTIONAL``; an all-row-keeping bag (:data:`ROW_KEEPING`) already
    cannot eliminate the row, and the redundant nesting (doubly-nested
    ``OPTIONAL`` s, nested-group ``BIND`` s) trips rdflib 7.6.0 — it is
    returned flat. Used by ``wrap_if_unbound`` (optionality policy) and the
    node-expression branch/condition/default-lane containments.
    """
    if all(isinstance(p, ROW_KEEPING) for p in patterns):
        return list(patterns)
    return [OptionalPattern(GroupPattern(children=tuple(patterns)))]
