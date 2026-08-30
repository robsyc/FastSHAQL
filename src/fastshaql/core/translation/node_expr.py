"""Translate ``NodeExprIR`` into SPARQL graph patterns (ADR-0015).

Dispatched by ``match`` over the closed-sum IR union. ``$this`` substitution
is confined to the ``SparqlExprNodeExpr`` / ``SelectNodeExpr`` arms.

Derived fields bind-then-filter: the expression is bound to *value_var* once
and filters compare against that variable, so the expression evaluates once
even when the field is both selected and filtered.

Two load-bearing invariants (ADR-0015; every helper below defers to them):

1. **rdflib ``BIND`` discipline** — a ``BIND`` expression must not depend on
   bindings made outside its group (rdflib 7.6.0 ``evalExtend`` evaluates
   against ``forget()``-filtered solutions). Row-keeping emissions sit at
   group level; ``FILTER`` placement is always safe.
2. **Containment** — a row-eliminating sub-emission (a conjunct ``FILTER``,
   a branch triple join) is wrapped in its own scoped ``OPTIONAL``: a failed
   pattern means *no value*, never a dropped row.

``shnex:if`` / ``shnex:exists`` conditions compile strictly as
``cond = true`` with errored conditions taking the else branch — the
documented else-on-error deviation of ADR-0015. Internal variables
derive from a per-expression *base* with underscore-prefixed roles, all
minted by :func:`role_var` (``_cond_``, ``_then_``, ``_else_``,
``_exists_``; ``_dv_``/``_dv_default_`` for the ``sh:defaultValue`` lanes
and ``_l{i}_`` for the language-preference chain steps in ``patterns.py``)
— GraphQL field names cannot start with an underscore,
so they never collide with allocation-stemmed selection variables, and
each nested expression lowers against a role-prefixed base so same-role
sub-variables at different nesting depths stay distinct.

Known residual corner (spec-correct emission, wrong on rdflib 7.6.0): an
``EXISTS``-bearing sub-``BIND`` inside a nested group whose ambient
bindings it needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from rdflib import RDF, RDFS, Literal, URIRef, Variable

from fastshaql.core.ir.node_expr import (
    ConstantListNodeExpr,
    ConstantNodeExpr,
    ExistsNodeExpr,
    FilterShapeNodeExpr,
    IfNodeExpr,
    InstancesOfNodeExpr,
    NodeExprIR,
    PathValuesNodeExpr,
    SelectNodeExpr,
    SparqlExprNodeExpr,
    is_multivalued_capable,
    is_total,
)
from fastshaql.core.sparql import (
    BindPattern,
    CompareExpr,
    ExistsExpr,
    Expression,
    FilterPattern,
    FunctionCall,
    GroupPattern,
    NotExpr,
    OptionalPattern,
    Pattern,
    RawGraphPattern,
    RawSparqlExpr,
    TermExpr,
    TriplePattern,
    ValuesPattern,
    contain_row_eliminating,
)
from fastshaql.core.sparql.lex import THIS_REF, code_spans
from fastshaql.core.sparql.paths import (
    PredicatePath as SparqlPredicatePath,
)
from fastshaql.core.sparql.paths import (
    SequencePath as SparqlSequencePath,
)
from fastshaql.core.sparql.paths import (
    ZeroOrMorePath as SparqlZeroOrMorePath,
)
from fastshaql.core.sparql.terms import RenderTerm, render_term

from .filter_shape import translate_filter_shape
from .paths import map_shacl_path_to_sparql_path

_TRUE = Literal(True)
_FALSE = Literal(False)

_SHACL_INSTANCE_PATH = SparqlSequencePath(
    (
        SparqlPredicatePath(RDF.type),
        SparqlZeroOrMorePath(SparqlPredicatePath(RDFS.subClassOf)),
    )
)
"""``rdf:type/rdfs:subClassOf*`` — the subclass-closing instance path.

SHACL instances of a class are nodes typed with the class or any subclass
(Core §1.1); the closure reads the queried graphs only — the spec's §6.3
shapes-graph ``rdfs:subClassOf`` lookup is a documented deviation (ADR-0016)."""


def _substitute_focus_var(text: str, focus_term: RenderTerm) -> str:
    """Replace ``$this``/``?this`` with *focus_term*, only in code position.

    String literals, IRIREFs, and comments are protected (SPARQL 1.2 §19) — a
    ``$this`` inside a string is a literal value, not a focus-node reference, so
    it is left untouched. Mirrors the protected-region guarantee of
    :func:`~fastshaql.core.parser.node_expr.shacl_prefixes.expand_sparql_prefixes`.
    The term renders through :func:`~fastshaql.core.sparql.terms.render_term`
    (``?var`` for variables, ``<iri>`` for the constant-IRI focus at target
    position).
    """
    replacement = render_term(focus_term)
    parts: list[str] = []
    pos = 0
    for start, end in code_spans(text):
        parts.append(text[pos:start])
        parts.append(THIS_REF.sub(replacement, text[start:end]))
        pos = end
    parts.append(text[pos:])
    return "".join(parts)


def translate_node_expr(
    ir: NodeExprIR,
    *,
    focus_term: RenderTerm,
    value_var: Variable,
) -> list[Pattern]:
    """Translate a node expression into graph patterns binding *value_var*.

    Args:
        ir: Parsed node expression from ``sh:values`` or ``sh:targetNode``.
        focus_term: Focus-node term (``$this`` substitution target) — the
            enclosing subject variable, or the shape-IRI constant at target
            position.
        value_var: Caller-allocated variable for the derived value.

    Returns:
        Graph patterns binding *value_var* to the derived value.
    """
    return _translate(ir, focus_term=focus_term, value_var=value_var, base=value_var)


def default_value_operand(
    ir: NodeExprIR, focus_term: RenderTerm, value_var: Variable
) -> tuple[Expression, list[Pattern]]:
    """A statically single-valued expression as the ``sh:defaultValue``
    COALESCE operand (``patterns.py`` default lane).

    Pure arms inline as expressions with no patterns; an arm needing
    sub-``BIND`` s binds ``_dv_default_{value_var}`` and references the
    variable, contained per module invariant 2 (unbound ⇒ no default, not
    a dropped entity row).

    Raises:
        ValueError: For multi-valued arms — the parser guarantees
            single-valued defaults (ADR-0015 boundary).
    """
    if is_multivalued_capable(ir):
        raise ValueError(f"multi-valued node expression cannot inline: {ir!r}")
    expr = _pure_branch(ir, "dv_default", focus_term, value_var)
    if expr is not None:
        return expr, []
    default_var = role_var("dv_default", value_var)
    patterns = _translate(
        ir, focus_term=focus_term, value_var=default_var, base=default_var
    )
    return TermExpr(default_var), contain_row_eliminating(patterns)


def _translate(
    ir: NodeExprIR,
    *,
    focus_term: RenderTerm,
    value_var: Variable,
    base: Variable,
) -> list[Pattern]:
    """The dispatcher proper — the fourth exhaustively-guarded union match
    (with ``is_multivalued_capable``, ``arm_label``,
    ``reject_derived_path_targets``); *base* is the sub-variable naming base
    (defaults to *value_var* at the public boundary and role-prefixes
    through nesting)."""
    patterns: list[Pattern]
    match ir:
        case ConstantNodeExpr(value=value):
            patterns = [BindPattern(TermExpr(value), value_var)]
        case SparqlExprNodeExpr(expr=expr_text):
            subbed = _substitute_focus_var(expr_text, focus_term)
            patterns = [BindPattern(RawSparqlExpr(subbed), value_var)]
        case SelectNodeExpr(body=body, projection_var=proj_name):
            subbed = _substitute_focus_var(body, focus_term)
            patterns = [RawGraphPattern(subbed)]
            if Variable(proj_name) != value_var:
                # Rename the author's projection var onto the caller's value var
                # via the typed AST (render_term), not a raw-text node — the only
                # raw-text paths are trusted author SPARQL (ADR-0017).
                patterns.append(BindPattern(TermExpr(Variable(proj_name)), value_var))
        case PathValuesNodeExpr(path=path, focus_node=focus):
            subject: RenderTerm = focus_term
            if focus is not None:
                subject = focus
            patterns = [
                TriplePattern(
                    subject=subject,
                    predicate=map_shacl_path_to_sparql_path(path),
                    object=value_var,
                )
            ]
        case FilterShapeNodeExpr(nodes=nodes, shape=shape):
            inner = _translate(
                nodes, focus_term=focus_term, value_var=value_var, base=base
            )
            patterns = [*inner, *translate_filter_shape(shape, value_var)]
        case ConstantListNodeExpr(values=values):
            patterns = [ValuesPattern(value_var, values)]
        case InstancesOfNodeExpr(classes=classes):
            patterns = _instances_of_patterns(classes, value_var, base)
        case ExistsNodeExpr(inner=inner):
            patterns = [BindPattern(_exists_expr(inner, focus_term, base), value_var)]
        case IfNodeExpr(cond=cond, then=then, otherwise=otherwise):
            patterns = _translate_if(cond, then, otherwise, focus_term, value_var, base)
        case _ as unreachable:  # pragma: no cover — unreachable: closed union
            assert_never(unreachable)
    return patterns


def role_var(role: str, base: Variable) -> Variable:
    """A fresh sub-expression variable ``_{role}_{base}`` — the single mint
    of underscore-role names (see module docstring for the role inventory)."""
    return Variable(f"_{role}_{base}")


def _instances_of_patterns(
    classes: tuple[URIRef, ...], value_var: Variable, base: Variable
) -> list[Pattern]:
    """Lower ``shnex:instancesOf`` (node-expr §4.5.1) — ``?value
    rdf:type/rdfs:subClassOf* ?class`` with the folded class constants.

    A single class sits directly as the path object; a list binds a
    ``_class_{base}`` variable via ``VALUES``. The triple join is
    row-eliminating — the host position decides containment, as with
    ``pathValues``.
    """
    if len(classes) == 1:
        return [
            TriplePattern(
                subject=value_var,
                predicate=_SHACL_INSTANCE_PATH,
                object=classes[0],
            )
        ]
    class_var = role_var("class", base)
    return [
        TriplePattern(
            subject=value_var, predicate=_SHACL_INSTANCE_PATH, object=class_var
        ),
        ValuesPattern(class_var, classes),
    ]


def _exists_expr(
    nodes: NodeExprIR, focus_term: RenderTerm, base: Variable
) -> ExistsExpr:
    """``EXISTS { … }`` over *nodes*' inner patterns (multi-line body)."""
    inner_var = role_var("exists", base)
    inner = _translate(
        nodes, focus_term=focus_term, value_var=inner_var, base=inner_var
    )
    return ExistsExpr(GroupPattern(tuple(inner)))


def _condition(
    cond: NodeExprIR, focus_term: RenderTerm, base: Variable
) -> tuple[list[Pattern], Condition]:
    """Compile an ``shnex:if`` condition.

    Returns ``(binding patterns, condition)``. The test is ``cond = true``
    (spec-strict; SPARQL EBV would truthify non-boolean literals) or the
    ``EXISTS { … }`` of an exists condition. Pure conditions (:func:`_pure_branch`
    — its purity set is the single home of the arm knowledge) inline as
    expressions with no binding patterns; impure ones fall through to
    :func:`_materialized_condition` (rdflib trap, module docstring).
    """
    if isinstance(cond, ExistsNodeExpr):
        return [], Condition(
            _exists_expr(cond.inner, focus_term, base), total=is_total(cond)
        )
    if (pure := _pure_branch(cond, "cond", focus_term, base)) is not None:
        return [], Condition(_strict_true(pure), total=False)
    return _materialized_condition(cond, focus_term, base)


@dataclass(frozen=True)
class Condition:
    """A compiled ``shnex:if`` condition: the strict test plus whether it
    cannot error (*total* — an ``EXISTS`` is, a value comparison is not).
    The two error-routing wrappings (ADR-0015, else-on-error deviation) live
    here, each in its position-specific shape."""

    test: Expression
    total: bool

    def guarded(self) -> Expression:
        """IF position: ``COALESCE(test, false)`` — errors take the else
        operand (a total test passes through bare)."""
        if self.total:
            return self.test
        return FunctionCall("COALESCE", (self.test, TermExpr(_FALSE)))

    def negated_guarded(self) -> Expression:
        """Else-arm ``FILTER`` position: ``COALESCE(!(test), true)``."""
        if self.total:
            return NotExpr(self.test)
        return FunctionCall("COALESCE", (NotExpr(self.test), TermExpr(_TRUE)))


def _strict_true(expr: Expression) -> CompareExpr:
    """The spec-strict condition test ``expr = true`` (node-expr §4.1.6)."""
    return CompareExpr("=", expr, TermExpr(_TRUE))


def _raw_expr(text: str, focus_term: RenderTerm) -> RawSparqlExpr:
    """Author SPARQL text with the focus variable substituted (trusted author
    text — the only raw-expression carrier, ADR-0017)."""
    return RawSparqlExpr(_substitute_focus_var(text, focus_term))


def _pure_branch(
    branch: NodeExprIR, role: str, focus_term: RenderTerm, base: Variable
) -> Expression | None:
    """A single-valued branch as a pure ``IF`` operand — inlined, no patterns.

    Constants, ``shnex:exists``, ``sh:sparqlExpr`` and fully-present nested
    single-valued ``if`` s qualify; ``None`` marks an arm that needs
    sub-``BIND`` s (``shnex:filterShape``) or a missing branch (whose
    empty-list semantics only the ``OPTIONAL``-arm form can express).
    """
    match branch:
        case ConstantNodeExpr(value=value):
            return TermExpr(value)
        case ExistsNodeExpr(inner=inner):
            return _exists_expr(inner, focus_term, role_var(role, base))
        case SparqlExprNodeExpr(expr=text):
            return _raw_expr(text, focus_term)
        case IfNodeExpr(cond=c, then=t, otherwise=o) if t is not None and o is not None:
            return _pure_if(c, t, o, focus_term, role_var(role, base))
    return None


def _pure_if(
    cond: NodeExprIR,
    then: NodeExprIR,
    otherwise: NodeExprIR,
    focus_term: RenderTerm,
    base: Variable,
) -> FunctionCall | None:
    """The fully-inlined ``IF(…)`` expression, or ``None`` when any operand
    cannot inline (see :func:`_pure_branch` / :func:`_condition`)."""
    cond_patterns, condition = _condition(cond, focus_term, base)
    if cond_patterns:
        return None
    then_expr = _pure_branch(then, "then", focus_term, base)
    if then_expr is None:
        return None
    else_expr = _pure_branch(otherwise, "else", focus_term, base)
    if else_expr is None:
        return None
    return FunctionCall("IF", (condition.guarded(), then_expr, else_expr))


def _single_branch(
    branch: NodeExprIR, role: str, focus_term: RenderTerm, base: Variable
) -> tuple[Expression, list[Pattern]]:
    """A single-valued branch as an ``IF`` operand: constants inline as
    terms, every other arm binds a ``_{role}_{base}`` variable referenced
    here, contained per module invariant 2 — a failed pattern means *no
    branch value*, never a dropped or other-branch-corrupted row
    (``IF``'s laziness, SPARQL §17.4.1.2, protects the unbound branch
    variable)."""
    if isinstance(branch, ConstantNodeExpr):
        return TermExpr(branch.value), []
    branch_var = role_var(role, base)
    patterns: list[Pattern] = _translate(
        branch, focus_term=focus_term, value_var=branch_var, base=branch_var
    )
    return TermExpr(branch_var), contain_row_eliminating(patterns)


def _materialized_condition(
    cond: NodeExprIR, focus_term: RenderTerm, base: Variable
) -> tuple[list[Pattern], Condition]:
    """A condition bound to ``?_cond_{base}`` regardless of purity — the
    sub-``BIND`` fallback's condition source and ``_condition``'s tail.
    Contained per module invariant 2: a failed conjunct leaves ``?_cond``
    unbound — empty output, so node-expr §4.1.6 routes to else via the
    ``COALESCE`` guard. Binding ahead of later ``BIND`` s keeps any
    ``EXISTS`` out of them (module invariant 1); an exists condition
    stays total (:func:`is_total` — a ``BIND`` of it always binds).
    """
    cond_var = role_var("cond", base)
    patterns: list[Pattern] = _translate(
        cond, focus_term=focus_term, value_var=cond_var, base=cond_var
    )
    contained = contain_row_eliminating(patterns)
    return contained, Condition(_strict_true(TermExpr(cond_var)), total=is_total(cond))


def _translate_if(
    cond: NodeExprIR,
    then: NodeExprIR | None,
    otherwise: NodeExprIR | None,
    focus_term: RenderTerm,
    value_var: Variable,
    base: Variable,
) -> list[Pattern]:
    """Lower ``shnex:if`` (node-expr §4.1.6).

    Three forms, most-preferred first. (1) Both branches present, single-valued,
    everything pure → one ``BIND(IF(cond, then, else))`` with nested ``IF`` s
    inlined. (2) Both present, single-valued, some operand impure → condition
    materialised into ``?_cond_{base}``, each impure branch contained in its
    own ``OPTIONAL`` (:func:`_single_branch`), then a value ``BIND``
    referencing variables only. (3) Otherwise two conditioned ``OPTIONAL``
    arms sharing *value_var*; a missing branch is the empty list — its arm
    is simply absent. Branch sub-expressions lower against role-prefixed
    bases so a nested expression cannot reuse an enclosing
    ``_cond_``/``_then_``/``_else_`` variable.

    Where the condition can error, the *else* side is wrapped so the error
    lands on the else branch (ADR-0015 else-on-error deviation):
    ``COALESCE(test, false)`` inside ``IF``, ``COALESCE(!(test), true)`` on the
    else arm's ``FILTER``. A total condition needs neither. The *then* side
    never needs a guard — an errored ``FILTER`` already excludes the row; in
    the ``BIND(IF(…))`` forms the ``COALESCE`` guard on the test is what
    routes errors to else: per SPARQL §17.4.1.2 an erroring ``IF`` test
    errors the whole expression (the ``BIND`` variable stays unbound), it
    does not yield the else operand.
    """
    if then is not None and otherwise is not None:
        inlined = _pure_if(cond, then, otherwise, focus_term, base)
        if inlined is not None:
            return [BindPattern(inlined, value_var)]
        if not is_multivalued_capable(then) and not is_multivalued_capable(otherwise):
            cond_patterns, condition = _materialized_condition(cond, focus_term, base)
            patterns = list(cond_patterns)
            then_expr, then_patterns = _single_branch(then, "then", focus_term, base)
            else_expr, else_patterns = _single_branch(
                otherwise, "else", focus_term, base
            )
            patterns.extend(then_patterns)
            patterns.extend(else_patterns)
            patterns.append(
                BindPattern(
                    FunctionCall("IF", (condition.guarded(), then_expr, else_expr)),
                    value_var,
                )
            )
            return patterns

    cond_patterns, condition = _condition(cond, focus_term, base)
    patterns = list(cond_patterns)
    if then is not None:
        arm = _translate(
            then,
            focus_term=focus_term,
            value_var=value_var,
            base=role_var("then", base),
        )
        patterns.append(
            OptionalPattern(GroupPattern((*arm, FilterPattern(condition.test))))
        )
    if otherwise is not None:
        arm = _translate(
            otherwise,
            focus_term=focus_term,
            value_var=value_var,
            base=role_var("else", base),
        )
        patterns.append(
            OptionalPattern(
                GroupPattern((*arm, FilterPattern(condition.negated_guarded())))
            )
        )
    return patterns
