"""SPARQL graph pattern emission shared by binding and filter translation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import Literal, Variable

from fastshaql.core.ir import LiteralSpace, PropertyShapeIR, ValueSource
from fastshaql.core.sparql import (
    BindPattern,
    CompareExpr,
    Expression,
    FilterPattern,
    FunctionCall,
    OrExpr,
    Pattern,
    TermExpr,
    TriplePattern,
    contain_row_eliminating,
)

from .node_expr import default_value_operand, role_var, translate_node_expr
from .paths import map_shacl_path_to_sparql_path

if TYPE_CHECKING:
    from collections.abc import Sequence

_UNTAGGED_SENTINEL = ""
"""The untagged chain entry — matches plain literals only (``LANG(?v) = ""``;
``langMatches(x, "*")`` never matches untagged, SPARQL §17.4.3.11)."""


def wrap_if_unbound(patterns: Sequence[Pattern], *, bound: bool) -> list[Pattern]:
    """Return *patterns* when bound, or contained in a single ``OPTIONAL``
    group — the optionality policy over :func:`contain_row_eliminating`
    (which also flattens all-row-keeping bags)."""
    if bound:
        return list(patterns)
    return contain_row_eliminating(patterns)


def _step_predicate(var: Variable, entry: str) -> Expression:
    """The matching predicate for one language-preference chain entry.

    A basic range lowers through ``langMatches`` (range match,
    case-insensitive — ``"en"`` also serves ``en-US``); the untagged
    sentinel ``""`` matches plain literals only via ``LANG(?v) = ""`` (never
    ``STR()`` — it strips tags and cannot discriminate); the any-language
    sentinel ``"*"`` matches any tagged literal.
    """
    lang_of_var = FunctionCall("LANG", (TermExpr(var),))
    if entry == _UNTAGGED_SENTINEL:
        return CompareExpr("=", lang_of_var, TermExpr(Literal(_UNTAGGED_SENTINEL)))
    return FunctionCall("langMatches", (lang_of_var, TermExpr(Literal(entry))))


def _raw_core(prop: PropertyShapeIR, var: Variable, subject: Variable) -> list[Pattern]:
    """Values-or-path emission binding *var* (value-nodes steps 1-2) — the
    per-field core each language step re-emits against its own variable."""
    if prop.source is ValueSource.DERIVED:
        if prop.values_expr is None:
            raise ValueError(
                f"derived property {prop.graphql_field_name!r} lacks its sh:values node expression"
            )  # pragma: no cover — source is DERIVED iff values_expr set
        return translate_node_expr(prop.values_expr, focus_term=subject, value_var=var)
    return [
        TriplePattern(
            subject=subject,
            predicate=map_shacl_path_to_sparql_path(prop.path),
            object=var,
        )
    ]


def _chain_applies(prop: PropertyShapeIR, lang_tags: tuple[str, ...]) -> bool:
    """Whether the language-preference machinery engages for *prop*: a
    non-empty chain and language-accepting values (PLAIN properties ignore
    the chain — ADR-0012 owns the per-space chain semantics)."""
    return bool(lang_tags) and prop.is_language_typed


def _chain_entries(
    prop: PropertyShapeIR, lang_tags: tuple[str, ...]
) -> tuple[str, ...]:
    """Chain entries with the union's implicit untagged terminal appended
    last (when the caller did not already include one)."""
    if prop.literal_space is LiteralSpace.UNION and _UNTAGGED_SENTINEL not in lang_tags:
        return (*lang_tags, _UNTAGGED_SENTINEL)
    return lang_tags


def _step_optional(
    prop: PropertyShapeIR, step_var: Variable, subject: Variable, entry: str
) -> Pattern:
    """One scalar chain step: the per-step core binding *step_var*, its
    step filter, contained — a failed step means *no value at that step*,
    never a dropped row."""
    step = [
        *_raw_core(prop, step_var, subject),
        FilterPattern(_step_predicate(step_var, entry)),
    ]
    return contain_row_eliminating(step)[0]


def _scalar_chain_patterns(
    prop: PropertyShapeIR,
    var: Variable,
    *,
    subject: Variable,
    lang_tags: tuple[str, ...],
    trailing: Sequence[Expression] = (),
) -> list[Pattern]:
    """Chain lowering for scalar fields (maxCount 1): one ``OPTIONAL`` step
    per chain entry binding a ``_l{i}_``-roled variable, then one
    ``BIND(COALESCE(steps in chain order, …trailing) AS ?var)`` — the
    projected variable is the resolved value (S1/S3/S4; S5 passes the
    ``sh:defaultValue`` operand as *trailing*, keeping it the **last**
    argument).

    The steps-plus-``BIND`` bag is all-row-keeping; the row-eliminating
    requiredness guard is the caller's (S2), appended after this bag.
    """
    step_vars: list[Variable] = []
    patterns: list[Pattern] = []
    for index, entry in enumerate(_chain_entries(prop, lang_tags)):
        step_var = role_var(f"l{index}", var)
        step_vars.append(step_var)
        patterns.append(_step_optional(prop, step_var, subject, entry))
    operands = (TermExpr(v) for v in step_vars)
    patterns.append(BindPattern(FunctionCall("COALESCE", (*operands, *trailing)), var))
    return patterns


def _list_chain_patterns(
    prop: PropertyShapeIR,
    var: Variable,
    *,
    subject: Variable,
    lang_tags: tuple[str, ...],
    bound: bool,
) -> list[Pattern]:
    """Chain lowering for list fields: one variable under a single
    conjunctive filter OR-ing the chain predicates (plus the union's
    untagged terminal) — the union of all steps' matches (S6).

    Per-step priority needs per-entity set-emptiness over multiple values —
    not flat-expressible (the reason ``sh:defaultValue`` is scalar-only).
    A single predicate is not wrapped in an ``OR`` (single-entry chains
    render byte-identically to the single-tag form). ``bound`` preserves
    required-list behavior: the triple join itself eliminates
    non-matching entities.
    """
    predicates = [
        _step_predicate(var, entry) for entry in _chain_entries(prop, lang_tags)
    ]
    step_filter = predicates[0] if len(predicates) == 1 else OrExpr(tuple(predicates))
    return wrap_if_unbound(
        [*_raw_core(prop, var, subject), FilterPattern(step_filter)], bound=bound
    )


def _values_or_path_core(
    prop: PropertyShapeIR,
    var: Variable,
    *,
    subject: Variable,
    lang_tags: tuple[str, ...],
    bound: bool,
) -> list[Pattern]:
    """Values-or-path emission binding *var* (value-nodes steps 1-2),
    chain-lowered and optionality-wrapped."""
    if not _chain_applies(prop, lang_tags):
        return wrap_if_unbound(_raw_core(prop, var, subject), bound=bound)
    if prop.kind.is_list:
        return _list_chain_patterns(
            prop, var, subject=subject, lang_tags=lang_tags, bound=bound
        )
    return _scalar_chain_patterns(prop, var, subject=subject, lang_tags=lang_tags)


def _requiredness_guard(var: Variable) -> FilterPattern:
    """The S2 requiredness guard — ``FILTER(BOUND(?var))``, row-eliminating:
    an entity whose field resolves to null is dropped."""
    return FilterPattern(FunctionCall("BOUND", (TermExpr(var),)))


def scalar_bind_patterns(
    prop: PropertyShapeIR,
    var: Variable,
    *,
    subject: Variable,
    lang_tags: tuple[str, ...],
    bound: bool,
) -> list[Pattern]:
    """Emit bind patterns for scalar or derived properties.

    Under a language-preference chain (ADR-0012), a scalar language-accepting
    field lowers as per-step ``OPTIONAL`` s plus ``BIND(COALESCE(...))`` —
    the first step with a value wins the field. When *bound* (required or
    promoted), a row-eliminating ``FILTER(BOUND(?var))`` follows **after**
    the all-row-keeping bag; list fields take a single union filter instead.
    A defaulted property (``sh:defaultValue``, ADR-0015) keeps the
    default as the **last** ``COALESCE`` argument — the ``BIND`` always
    binds, so *bound* is irrelevant on that arm (SD-6).
    """
    if prop.default_expr is None:
        patterns = _values_or_path_core(
            prop, var, subject=subject, lang_tags=lang_tags, bound=bound
        )
        if bound and _chain_applies(prop, lang_tags) and not prop.kind.is_list:
            patterns.append(_requiredness_guard(var))
        return patterns
    default_expr, default_patterns = default_value_operand(
        prop.default_expr, subject, var
    )
    if _chain_applies(prop, lang_tags):
        # S5 — steps over `_l{i}_` roles; the default is the last argument.
        return [
            *default_patterns,
            *_scalar_chain_patterns(
                prop,
                var,
                subject=subject,
                lang_tags=lang_tags,
                trailing=(default_expr,),
            ),
        ]
    inner = role_var("dv", var)
    return [
        *default_patterns,
        *wrap_if_unbound(_raw_core(prop, inner, subject), bound=False),
        BindPattern(FunctionCall("COALESCE", (TermExpr(inner), default_expr)), var),
    ]
