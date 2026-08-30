"""SPARQL filter expression AST — composable nodes for FILTER rendering (§17).

See: https://www.w3.org/TR/sparql12-query/#expressions
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Literal

from .terms import RenderTerm, render_term

if TYPE_CHECKING:
    from .patterns import GroupPattern

ComparisonOp = Literal["=", "!=", ">", ">=", "<", "<="]
"""SPARQL comparison operators for :class:`CompareExpr`."""

type Expression = (
    CompareExpr
    | FunctionCall
    | InExpr
    | AndExpr
    | OrExpr
    | NotExpr
    | ExistsExpr
    | TermExpr
    | RawSparqlExpr
)
"""Union of renderable SPARQL filter expression nodes."""


def _render_child(
    child: Expression,
    *,
    wrap_type: type[Expression],
    indent: int = 0,
) -> str:
    """Render *child*, wrapping in parens when it is an instance of *wrap_type*."""
    rendered = child.render(indent)
    if isinstance(child, wrap_type):
        return f"({rendered})"
    return rendered


@dataclasses.dataclass(frozen=True)
class RawSparqlExpr:
    """Trusted author SPARQL expression text (ADR-0015/0017).

    ``render()`` returns the stored string verbatim — the only substitution is
    ``$this`` → focus variable, applied before construction.
    """

    text: str
    """Author expression with ``$this`` already substituted when applicable."""

    def render(self, indent: int = 0) -> str:
        """Render as verbatim trusted expression text."""
        del indent
        return self.text


@dataclasses.dataclass(frozen=True)
class TermExpr:
    """Leaf expression — variable, IRI, or literal (SPARQL §17.3)."""

    term: RenderTerm
    """RDFLib term rendered via :func:`render_term`."""

    def render(self, indent: int = 0) -> str:
        """Render as SPARQL term syntax."""
        del indent
        return render_term(self.term)


@dataclasses.dataclass(frozen=True)
class CompareExpr:
    """Binary comparison — ``left op right`` (SPARQL §17.3).

    Non-atomic operands are bracketed: ``RelationalExpression`` permits a
    single relational per expression, so a raw ``?score > 0.4`` operand
    must render as ``(?score > 0.4) = true`` to stay grammatical.
    """

    op: ComparisonOp
    """Comparison operator."""

    left: Expression
    """Left-hand expression."""

    right: Expression
    """Right-hand expression."""

    def render(self, indent: int = 0) -> str:
        """Render as ``left op right``, bracketing non-atomic operands."""
        return f"{_operand(self.left, indent)} {self.op} {_operand(self.right, indent)}"


@dataclasses.dataclass(frozen=True)
class FunctionCall:
    """Built-in or extension function call (SPARQL §17.4)."""

    name: str
    """Function name as rendered (e.g. ``CONTAINS``, ``REGEX``)."""

    args: tuple[Expression, ...]
    """Positional arguments."""

    def render(self, indent: int = 0) -> str:
        """Render as ``NAME(arg1, arg2, ...)``."""
        rendered_args = ", ".join(a.render(indent) for a in self.args)
        return f"{self.name}({rendered_args})"


@dataclasses.dataclass(frozen=True)
class InExpr:
    """Membership test — ``expr IN (v1, v2, ...)`` (SPARQL §17.4.1.8)."""

    expr: Expression
    """Expression tested for membership."""

    values: tuple[RenderTerm, ...]
    """Literal or term values in the IN list."""

    def render(self, indent: int = 0) -> str:
        """Render as ``expr IN (v1, v2, ...)``."""
        expr = self.expr.render(indent)
        value_strs = ", ".join(render_term(v) for v in self.values)
        return f"{expr} IN ({value_strs})"


@dataclasses.dataclass(frozen=True)
class AndExpr:
    """Logical conjunction — ``child1 && child2 && ...`` (SPARQL §17.3)."""

    children: tuple[Expression, ...]
    """Conjuncts joined with ``&&``."""

    def render(self, indent: int = 0) -> str:
        """Render with ``&&``; wrap :class:`OrExpr` children in parens."""
        if len(self.children) == 1:
            return self.children[0].render(indent)
        parts = [
            _render_child(c, wrap_type=OrExpr, indent=indent) for c in self.children
        ]
        return " && ".join(parts)


@dataclasses.dataclass(frozen=True)
class OrExpr:
    """Logical disjunction — ``child1 || child2 || ...`` (SPARQL §17.3)."""

    children: tuple[Expression, ...]
    """Disjuncts joined with ``||``."""

    def render(self, indent: int = 0) -> str:
        """Render with ``||``; wrap :class:`AndExpr` children in parens."""
        if len(self.children) == 1:
            return self.children[0].render(indent)
        parts = [
            _render_child(c, wrap_type=AndExpr, indent=indent) for c in self.children
        ]
        return " || ".join(parts)


@dataclasses.dataclass(frozen=True)
class NotExpr:
    """Logical negation — ``!(child)`` (SPARQL §17.3)."""

    child: Expression
    """Negated sub-expression."""

    def render(self, indent: int = 0) -> str:
        """Render as ``!(child)``."""
        return f"!({self.child.render(indent)})"


@dataclasses.dataclass(frozen=True)
class ExistsExpr:
    """Existence test — ``EXISTS { pattern }`` (SPARQL §17.4.1.4, §19.7 [145])."""

    pattern: GroupPattern
    """Inner group graph pattern."""

    def render(self, indent: int = 0) -> str:
        """Render as ``EXISTS { ... }`` with a consistently indented body."""
        if not self.pattern.children:
            return "EXISTS {}"
        body_indent = indent + 1
        inner = "\n".join(c.render(body_indent) for c in self.pattern.children)
        pad = "  " * indent
        return f"EXISTS {{\n{inner}\n{pad}}}"


_ATOMIC_EXPRS = (TermExpr, FunctionCall, NotExpr, ExistsExpr)
"""Leaves whose render is self-delimiting (SPARQL §19 grammar) — safe as
unbracketed :class:`CompareExpr` operands: terms and function calls are
``PrimaryExpression`` productions [136], ``!`` closes over its own unary
operand [135], and ``EXISTS`` is a ``BuiltInCall`` [141]. Anything else
must be bracketed — notably :class:`InExpr` (``IN`` is itself one of
[131]'s relational alternatives, so ``x IN (…) = true`` is ungrammatical),
:class:`RawSparqlExpr` author text, and nested comparisons."""


def _operand(expr: Expression, indent: int) -> str:
    """Render *expr*, bracketed unless self-delimiting."""
    rendered = expr.render(indent)
    if isinstance(expr, _ATOMIC_EXPRS):
        return rendered
    return f"({rendered})"
