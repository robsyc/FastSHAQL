"""Scalar bind and optional-wrap pattern helpers — ``core/translation/patterns.py``.

Unit tier: ``scalar_bind_patterns`` emitting a bare triple or ``OPTIONAL`` wrap
(asserted, derived, and defaulted lanes), the language-preference chain
lowering S1-S6 (per-step ``OPTIONAL`` + ``BIND(COALESCE)``, the ``BOUND``
guard, the union-filter list form), and ``wrap_if_unbound``
relationship-pattern wrapping.

Order: bound triple → optional wrap → unbound relationship wrap → sh:defaultValue → language chains.
"""

from __future__ import annotations

import pytest
from rdflib import Literal, URIRef, Variable
from rdflib.namespace import RDF, XSD

from fastshaql.core.ir.filter_shape import FilterHasValue, FilterShapeIR
from fastshaql.core.ir.node_expr import (
    ConstantListNodeExpr,
    ConstantNodeExpr,
    ExistsNodeExpr,
    FilterShapeNodeExpr,
    IfNodeExpr,
    PathValuesNodeExpr,
    SparqlExprNodeExpr,
)
from fastshaql.core.ir.shacl_path import PredicatePath as ShaclPredicatePath
from fastshaql.core.sparql import (
    BindPattern,
    CompareExpr,
    ExistsExpr,
    FilterPattern,
    FunctionCall,
    OptionalPattern,
    OrExpr,
    PredicatePath,
    RawSparqlExpr,
    TermExpr,
    TriplePattern,
)
from fastshaql.core.translation.node_expr import default_value_operand
from fastshaql.core.translation.patterns import scalar_bind_patterns, wrap_if_unbound
from support.builders import defaulted_property, derived_property, scalar_property

EX = "http://example.org/"


# --- Bind patterns ---


def test_scalar_bind_patterns_bound_emits_triple() -> None:
    prop = scalar_property("name", min_count=1, max_count=1)
    var = Variable("name")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=True
    )
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)


def test_scalar_bind_patterns_optional_wraps_optional() -> None:
    prop = scalar_property("name", min_count=0, max_count=1)
    var = Variable("name")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    assert len(patterns) == 1
    assert isinstance(patterns[0], OptionalPattern)


def test_derived_scalar_bind_emits_bind_not_triple() -> None:
    prop = derived_property(
        "recordSource",
        values_expr=ConstantNodeExpr(Literal("FastshaqlEMR")),
        min_count=1,
        max_count=1,
    )
    var = Variable("recordSource")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=True
    )
    assert len(patterns) == 1
    assert isinstance(patterns[0], BindPattern)
    assert patterns[0].var == var


def test_derived_optional_pure_bind_bag_escapes_wrap() -> None:
    """An unbound (optional) derived field whose emission is solely ``BIND``
    patterns needs no ``OPTIONAL`` wrap: a ``BIND`` cannot eliminate a row
    (SPARQL §10 — an expression error leaves the variable unbound, row
    kept), so the wrap would be solution-set-identical — and on rdflib
    7.6.0 it is worse than redundant: a nested-group ``BIND`` expression
    forgets ambient bindings, so a ``$this``-referencing ``sh:sparqlExpr``
    would compute on a forgotten focus."""
    prop = derived_property(
        "recordSource",
        values_expr=ConstantNodeExpr(Literal("FastshaqlEMR")),
        min_count=0,
        max_count=1,
    )
    var = Variable("recordSource")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    assert len(patterns) == 1
    assert isinstance(patterns[0], BindPattern)
    assert patterns[0].var == var


def test_derived_sparql_expr_bind_emits_raw_sparql() -> None:
    prop = derived_property(
        "uriLength",
        values_expr=SparqlExprNodeExpr("STRLEN(STR($this))"),
        min_count=1,
        max_count=1,
        datatype=XSD.integer,
    )
    var = Variable("uriLength")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=True
    )
    assert len(patterns) == 1
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert isinstance(bind.expr, RawSparqlExpr)
    assert bind.expr.text == "STRLEN(STR(?iri))"


def test_wrap_if_unbound_relationship_patterns() -> None:
    triple = TriplePattern(
        Variable("iri"), PredicatePath(RDF.type), Literal(EX + "Company")
    )
    assert wrap_if_unbound([triple], bound=True) == [triple]
    wrapped = wrap_if_unbound([triple], bound=False)
    assert len(wrapped) == 1
    assert isinstance(wrapped[0], OptionalPattern)


# --- sh:defaultValue (ADR-0015: OPTIONAL {…} BIND(COALESCE(…))) ---


def test_defaulted_scalar_emits_optional_coalesce() -> None:
    """Path + default: the path triples move inside an ``OPTIONAL`` and the
    value variable is bound by ``COALESCE`` — asserted values win, the
    default fills entities the path misses (value-nodes step 3). The inner
    variable is underscore-prefixed (``_dv_``), never colliding with
    allocation-stemmed field variables."""
    prop = defaulted_property(
        "recordSource",
        default_expr=ConstantNodeExpr(Literal("FSQ-REG")),
        min_count=0,
        max_count=1,
    )
    var = Variable("recordSource")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    assert len(patterns) == 2
    optional, bind = patterns
    assert isinstance(optional, OptionalPattern)
    (triple,) = optional.child.children
    assert triple == TriplePattern(
        subject=Variable("iri"),
        predicate=PredicatePath(URIRef(EX + "recordSource")),
        object=Variable("_dv_recordSource"),
    )
    assert isinstance(bind, BindPattern)
    assert bind.var == var
    call = bind.expr
    assert isinstance(call, FunctionCall)
    assert call.name == "COALESCE"
    inner, fallback = call.args
    assert inner == TermExpr(Variable("_dv_recordSource"))
    assert fallback == TermExpr(Literal("FSQ-REG"))


def test_defaulted_scalar_bound_still_optional_coalesce() -> None:
    """``bound`` is irrelevant for defaulted fields — a ``minCount 1`` default
    field must NOT emit a mandatory path triple (it would drop the very
    entities the default serves, SD-6); the ``BIND`` guarantees the value
    variable, so no outer wrap either way."""
    prop = defaulted_property(
        "recordSource",
        default_expr=ConstantNodeExpr(Literal("FSQ-REG")),
        min_count=1,
        max_count=1,
    )
    var = Variable("recordSource")
    for bound in (True, False):
        patterns = scalar_bind_patterns(
            prop, var, subject=Variable("iri"), lang_tags=(), bound=bound
        )
        assert len(patterns) == 2
        assert isinstance(patterns[0], OptionalPattern)
        assert isinstance(patterns[1], BindPattern)


def test_defaulted_derived_falls_back_over_values_expression() -> None:
    """``sh:values`` + ``sh:defaultValue``: the derived ``BIND`` (binding the
    inner variable) sits at group level — a lone ``BIND`` cannot drop rows,
    so no ``OPTIONAL`` around it — and the ``COALESCE`` fallback applies
    when the expression yields nothing (steps 2 → 3)."""
    prop = defaulted_property(
        "recordSource",
        default_expr=ConstantNodeExpr(Literal("FSQ-REG")),
        values_expr=SparqlExprNodeExpr("STR($this)"),
        min_count=0,
        max_count=1,
    )
    var = Variable("recordSource")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    assert len(patterns) == 2
    values_bind, bind = patterns
    assert isinstance(values_bind, BindPattern)
    assert values_bind.var == Variable("_dv_recordSource")
    assert isinstance(values_bind.expr, RawSparqlExpr)
    assert isinstance(bind, BindPattern)
    call = bind.expr
    assert isinstance(call, FunctionCall)
    assert call.args[0] == TermExpr(Variable("_dv_recordSource"))
    assert call.args[1] == TermExpr(Literal("FSQ-REG"))


def test_defaulted_expression_default_inlines() -> None:
    """An expression default (here ``shnex:exists``) inlines into the
    ``COALESCE`` operand — pure operands need no sub-``BIND``."""
    prop = defaulted_property(
        "hasFallback",
        default_expr=ExistsNodeExpr(
            inner=PathValuesNodeExpr(ShaclPredicatePath(URIRef(EX + "flag")))
        ),
        min_count=0,
        max_count=1,
        datatype=XSD.boolean,
    )
    var = Variable("hasFallback")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    _, bind = patterns
    assert isinstance(bind, BindPattern)
    assert bind.var == var
    call = bind.expr
    assert isinstance(call, FunctionCall)
    assert call.name == "COALESCE"
    assert call.args[0] == TermExpr(Variable("_dv_hasFallback"))
    assert isinstance(call.args[1], ExistsExpr)


def test_defaulted_filter_shape_default_materializes_sub_bind() -> None:
    """An impure default (``shnex:filterShape`` over a constant) cannot inline
    — its conjunct ``FILTER`` s need a bound variable — so the fallback binds
    ``_dv_default_{var}`` inside a single ``OPTIONAL`` before the
    ``COALESCE`` (the ``_dv_default_`` naming invariant). The wrap is
    load-bearing: a failed conjunct leaves the variable unbound (no
    default, node-expr §4.2.5) instead of eliminating the entity row."""
    prop = defaulted_property(
        "graded",
        default_expr=FilterShapeNodeExpr(
            nodes=ConstantNodeExpr(Literal("raw")),
            shape=FilterShapeIR(conjuncts=(FilterHasValue(Literal("x")),)),
        ),
        min_count=0,
        max_count=1,
    )
    var = Variable("graded")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    default_optional, path_optional, coalesce_bind = patterns
    assert isinstance(default_optional, OptionalPattern)
    default_bind, conjunct = default_optional.child.children
    assert isinstance(default_bind, BindPattern)
    assert default_bind.var == Variable("_dv_default_graded")
    assert default_bind.expr == TermExpr(Literal("raw"))
    assert isinstance(conjunct, FilterPattern)
    assert isinstance(path_optional, OptionalPattern)
    assert isinstance(coalesce_bind, BindPattern)
    call = coalesce_bind.expr
    assert isinstance(call, FunctionCall)
    assert call.args == (
        TermExpr(Variable("_dv_graded")),
        TermExpr(Variable("_dv_default_graded")),
    )


def test_defaulted_derived_all_optional_emission_nests_directly() -> None:
    """A derived values emission that is already an all-``OPTIONAL`` bag (a
    single-valued ``shnex:if`` with a missing branch) nests directly inside
    the fallback — no doubly-nested ``OPTIONAL`` (the ``wrap_if_unbound``
    flattening rule; doubly-nested optionals mis-scope filters on rdflib)."""
    prop = defaulted_property(
        "triage",
        default_expr=ConstantNodeExpr(Literal("none")),
        values_expr=IfNodeExpr(
            cond=ExistsNodeExpr(
                inner=PathValuesNodeExpr(ShaclPredicatePath(URIRef(EX + "flag")))
            ),
            then=ConstantNodeExpr(Literal("urgent")),
            otherwise=None,
        ),
        min_count=0,
        max_count=1,
    )
    var = Variable("triage")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    arm, bind = patterns
    # The single conditioned OPTIONAL arm is the whole emission — no wrap.
    assert isinstance(arm, OptionalPattern)
    _, arm_filter = arm.child.children
    assert isinstance(arm_filter, FilterPattern)
    assert isinstance(bind, BindPattern)
    call = bind.expr
    assert isinstance(call, FunctionCall)
    assert call.args == (
        TermExpr(Variable("_dv_triage")),
        TermExpr(Literal("none")),
    )


def test_defaulted_if_shaped_default_nests_directly() -> None:
    """An ``shnex:if``-shaped default with a missing branch lowers to an
    all-row-keeping bag (one conditioned ``OPTIONAL`` arm) — it must nest
    directly as the default lane, not be wrapped in a second ``OPTIONAL``
    (the ``wrap_if_unbound`` flattening rule; doubly-nested optionals
    mis-scope filters on rdflib)."""
    prop = defaulted_property(
        "triage",
        default_expr=IfNodeExpr(
            cond=ExistsNodeExpr(
                inner=PathValuesNodeExpr(ShaclPredicatePath(URIRef(EX + "flag")))
            ),
            then=ConstantNodeExpr(Literal("flagged")),
            otherwise=None,
        ),
        min_count=0,
        max_count=1,
    )
    var = Variable("triage")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(), bound=False
    )
    default_arm, path_optional, coalesce_bind = patterns
    # The single conditioned OPTIONAL arm is the whole default emission — the
    # BIND sits directly inside it, no wrapping OPTIONAL.
    assert isinstance(default_arm, OptionalPattern)
    default_bind, arm_filter = default_arm.child.children
    assert isinstance(default_bind, BindPattern)
    assert default_bind.var == Variable("_dv_default_triage")
    assert isinstance(arm_filter, FilterPattern)
    assert isinstance(path_optional, OptionalPattern)
    assert isinstance(coalesce_bind, BindPattern)
    call = coalesce_bind.expr
    assert isinstance(call, FunctionCall)
    assert call.args == (
        TermExpr(Variable("_dv_triage")),
        TermExpr(Variable("_dv_default_triage")),
    )


def test_defaulted_language_typed_scalar_uses_chain_steps_s5() -> None:
    """S5 — a language-typed defaulted scalar under a chain: the language
    steps replace the ``_dv_`` lane (``_l0_``/``_l1_`` roles) and the
    SHACL step-3 default stays the **last** ``COALESCE`` argument."""
    prop = defaulted_property(
        "label",
        default_expr=ConstantNodeExpr(Literal("n/a")),
        min_count=0,
        max_count=1,
        datatype=RDF.langString,
    )
    var = Variable("label")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en", "nl"), bound=False
    )
    step0, step1, bind = patterns
    assert isinstance(step0, OptionalPattern)
    triple0, filter0 = step0.child.children
    assert triple0 == TriplePattern(
        subject=Variable("iri"),
        predicate=PredicatePath(URIRef(EX + "label")),
        object=Variable("_l0_label"),
    )
    assert filter0 == FilterPattern(
        FunctionCall(
            "langMatches",
            (
                FunctionCall("LANG", (TermExpr(Variable("_l0_label")),)),
                TermExpr(Literal("en")),
            ),
        )
    )
    assert isinstance(step1, OptionalPattern)
    assert isinstance(bind, BindPattern)
    call = bind.expr
    assert isinstance(call, FunctionCall)
    assert call.args == (
        TermExpr(Variable("_l0_label")),
        TermExpr(Variable("_l1_label")),
        TermExpr(Literal("n/a")),
    )


def test_defaulted_plain_scalar_keeps_dv_lane_under_chain() -> None:
    """PLAIN defaulted fields ignore the chain — the ``_dv_`` lane and the
    two-argument ``COALESCE`` survive unchanged."""
    prop = defaulted_property(
        "source",
        default_expr=ConstantNodeExpr(Literal("FSQ-REG")),
        min_count=0,
        max_count=1,
    )
    var = Variable("source")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en",), bound=False
    )
    optional, bind = patterns
    assert isinstance(optional, OptionalPattern)
    (triple,) = optional.child.children
    assert isinstance(triple, TriplePattern)
    assert triple.object == Variable("_dv_source")
    assert isinstance(bind, BindPattern)
    assert bind.expr == FunctionCall(
        "COALESCE",
        (TermExpr(Variable("_dv_source")), TermExpr(Literal("FSQ-REG"))),
    )


def test_default_value_operand_rejects_multivalued() -> None:
    """The multi-valued backstop behind the parser boundary (ADR-0015):
    a multi-valued default arm cannot inline."""
    with pytest.raises(ValueError, match="multi-valued"):
        default_value_operand(
            ConstantListNodeExpr((Literal("a"), Literal("b"))),
            focus_term=Variable("iri"),
            value_var=Variable("graded"),
        )


# --- Language-preference chains (S1-S6, ADR-0012) ---


def _lang_matches(var: Variable, tag: str) -> FunctionCall:
    return FunctionCall(
        "langMatches",
        (FunctionCall("LANG", (TermExpr(var),)), TermExpr(Literal(tag))),
    )


def test_s1_optional_scalar_chain_steps_then_coalesce() -> None:
    """S1 — optional scalar, chain ``("en", "nl")``: one ``OPTIONAL`` per
    step binding ``_l0_``/``_l1_``-roled variables, then one
    ``BIND(COALESCE(...))`` whose target is the projected variable."""
    prop = scalar_property("name", min_count=0, max_count=1, datatype=RDF.langString)
    var = Variable("name")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en", "nl"), bound=False
    )
    step0, step1, bind = patterns
    assert isinstance(step0, OptionalPattern)
    triple0, filter0 = step0.child.children
    assert triple0 == TriplePattern(
        subject=Variable("iri"),
        predicate=PredicatePath(URIRef(EX + "name")),
        object=Variable("_l0_name"),
    )
    assert filter0 == FilterPattern(_lang_matches(Variable("_l0_name"), "en"))
    assert isinstance(step1, OptionalPattern)
    triple1, filter1 = step1.child.children
    assert isinstance(triple1, TriplePattern)
    assert triple1.object == Variable("_l1_name")
    assert filter1 == FilterPattern(_lang_matches(Variable("_l1_name"), "nl"))
    assert isinstance(bind, BindPattern)
    assert bind.var == var
    assert bind.expr == FunctionCall(
        "COALESCE",
        (TermExpr(Variable("_l0_name")), TermExpr(Variable("_l1_name"))),
    )


def test_s1_single_entry_chain_is_not_special_cased() -> None:
    """A single-entry chain lowers in the same steps+``BIND`` shape — no
    simplification pass (uniform lowering; ROADMAP's AST-transform item)."""
    prop = scalar_property("name", min_count=0, max_count=1, datatype=RDF.langString)
    patterns = scalar_bind_patterns(
        prop, Variable("name"), subject=Variable("iri"), lang_tags=("en",), bound=False
    )
    assert len(patterns) == 2
    assert isinstance(patterns[0], OptionalPattern)
    assert isinstance(patterns[1], BindPattern)


def test_s2_required_scalar_appends_bound_guard_after_bag() -> None:
    """S2 — required (or promoted) under a chain: the ``FILTER(BOUND)``
    guard sits **after** the steps+``BIND`` bag, at group level — never
    inside an ``OPTIONAL`` wrap (it is the row-eliminating half by
    design)."""
    prop = scalar_property("name", min_count=1, max_count=1, datatype=RDF.langString)
    var = Variable("name")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en", "nl"), bound=True
    )
    step0, step1, bind, guard = patterns
    assert isinstance(step0, OptionalPattern)
    assert isinstance(step1, OptionalPattern)
    assert isinstance(bind, BindPattern)
    assert guard == FilterPattern(FunctionCall("BOUND", (TermExpr(var),)))


def test_s3_union_appends_implicit_untagged_terminal() -> None:
    """S3 — a string-union Property under ``("en",)``: steps for the chain
    entries plus the implicit ``""`` terminal, always last — tested as
    ``LANG(?v) = ""`` (never ``langMatches(x, "*")``, never ``STR()``)."""
    prop = scalar_property(
        "label",
        min_count=0,
        max_count=1,
        datatype=None,
        datatypes=(XSD.string, RDF.langString),
    )
    patterns = scalar_bind_patterns(
        prop, Variable("label"), subject=Variable("iri"), lang_tags=("en",), bound=False
    )
    step0, terminal, bind = patterns
    assert isinstance(step0, OptionalPattern)
    assert isinstance(terminal, OptionalPattern)
    _, terminal_filter = terminal.child.children
    assert terminal_filter == FilterPattern(
        CompareExpr(
            "=",
            FunctionCall("LANG", (TermExpr(Variable("_l1_label")),)),
            TermExpr(Literal("")),
        )
    )
    assert isinstance(bind, BindPattern)
    assert bind.expr == FunctionCall(
        "COALESCE",
        (TermExpr(Variable("_l0_label")), TermExpr(Variable("_l1_label"))),
    )


def test_s3_union_terminal_not_duplicated_when_untagged_in_chain() -> None:
    """A chain that already includes the untagged sentinel gets no second
    terminal — the caller's ordering stands."""
    prop = scalar_property(
        "label",
        min_count=0,
        max_count=1,
        datatype=None,
        datatypes=(XSD.string, RDF.langString),
    )
    patterns = scalar_bind_patterns(
        prop,
        Variable("label"),
        subject=Variable("iri"),
        lang_tags=("en", ""),
        bound=False,
    )
    assert len(patterns) == 3  # two steps + BIND
    _, terminal, _bind = patterns
    assert isinstance(terminal, OptionalPattern)
    _, terminal_filter = terminal.child.children
    assert terminal_filter == FilterPattern(
        CompareExpr(
            "=",
            FunctionCall("LANG", (TermExpr(Variable("_l1_label")),)),
            TermExpr(Literal("")),
        )
    )


def test_s4_derived_scalar_repeats_values_lowering_per_step() -> None:
    """S4 — a derived language-typed scalar: each step's core is the node-
    expression lowering binding the step variable, wrapped per-step."""
    prop = derived_property(
        "summary",
        values_expr=PathValuesNodeExpr(ShaclPredicatePath(URIRef(EX + "summary"))),
        min_count=0,
        max_count=1,
        datatype=RDF.langString,
    )
    step0, step1, bind = scalar_bind_patterns(
        prop,
        Variable("summary"),
        subject=Variable("iri"),
        lang_tags=("en", "nl"),
        bound=False,
    )
    assert isinstance(step0, OptionalPattern)
    triple0, filter0 = step0.child.children
    assert triple0 == TriplePattern(
        subject=Variable("iri"),
        predicate=PredicatePath(URIRef(EX + "summary")),
        object=Variable("_l0_summary"),
    )
    assert filter0 == FilterPattern(_lang_matches(Variable("_l0_summary"), "en"))
    assert isinstance(step1, OptionalPattern)
    assert isinstance(bind, BindPattern)
    assert bind.expr == FunctionCall(
        "COALESCE",
        (TermExpr(Variable("_l0_summary")), TermExpr(Variable("_l1_summary"))),
    )


@pytest.mark.parametrize("entry", ["", "*"])
def test_sentinel_step_predicates(entry: str) -> None:
    """``""`` renders ``LANG(?v) = ""``; ``"*"`` renders
    ``langMatches(LANG(?v), "*")`` — the any-language sentinel never
    matches untagged literals."""
    prop = scalar_property("name", min_count=0, max_count=1, datatype=RDF.langString)
    var = Variable("name")
    (step, _bind) = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=(entry,), bound=False
    )
    assert isinstance(step, OptionalPattern)
    _, step_filter = step.child.children
    assert isinstance(step_filter, FilterPattern)
    if entry == "":
        assert step_filter.expression == CompareExpr(
            "=",
            FunctionCall("LANG", (TermExpr(Variable("_l0_name")),)),
            TermExpr(Literal("")),
        )
    else:
        assert step_filter.expression == _lang_matches(Variable("_l0_name"), "*")


def test_plain_scalar_ignores_chain() -> None:
    """PLAIN (``xsd:string`` or any non-language datatype) under a chain:
    no filtering, today's emission."""
    prop = scalar_property("name", min_count=1, max_count=1)
    patterns = scalar_bind_patterns(
        prop, Variable("name"), subject=Variable("iri"), lang_tags=("en",), bound=True
    )
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)


def test_empty_chain_is_today_s_emission() -> None:
    prop = scalar_property("name", min_count=1, max_count=1, datatype=RDF.langString)
    patterns = scalar_bind_patterns(
        prop, Variable("name"), subject=Variable("iri"), lang_tags=(), bound=True
    )
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)


def test_s6_list_chain_is_union_filter() -> None:
    """S6 — optional list under ``("en", "nl")``: one variable, one
    conjunctive filter OR-ing the step predicates."""
    prop = scalar_property(
        "altLabel", min_count=0, max_count=None, datatype=RDF.langString
    )
    var = Variable("altLabel")
    patterns = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en", "nl"), bound=False
    )
    (optional,) = patterns
    assert isinstance(optional, OptionalPattern)
    triple, union_filter = optional.child.children
    assert isinstance(triple, TriplePattern)
    assert triple.object == var
    assert union_filter == FilterPattern(
        OrExpr(
            (
                _lang_matches(var, "en"),
                _lang_matches(var, "nl"),
            )
        )
    )


def test_s6_required_list_chain_keeps_row_eliminating_join() -> None:
    """A required list under a chain keeps the ``FILTER`` without the
    ``OPTIONAL`` wrap — the triple join itself drops non-matching entities
    (today's behavior)."""
    prop = scalar_property(
        "altLabel", min_count=1, max_count=None, datatype=RDF.langString
    )
    var = Variable("altLabel")
    triple, union_filter = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en", "nl"), bound=True
    )
    assert isinstance(triple, TriplePattern)
    assert isinstance(union_filter, FilterPattern)
    assert union_filter.expression == OrExpr(
        (_lang_matches(var, "en"), _lang_matches(var, "nl"))
    )


def test_s6_single_entry_list_chain_renders_single_predicate() -> None:
    """One entry, no ``OR`` wrapper — byte-identical to the single-tag form
    (pinned end-to-end by the migrated ``filters/lang_filter`` golden)."""
    prop = scalar_property("bio", min_count=0, max_count=None, datatype=RDF.langString)
    var = Variable("bio")
    (optional,) = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en",), bound=False
    )
    assert isinstance(optional, OptionalPattern)
    _, union_filter = optional.child.children
    assert union_filter == FilterPattern(_lang_matches(var, "en"))


def test_s6_union_list_appends_untagged_lane() -> None:
    """The union's implicit untagged terminal joins the OR for lists too."""
    prop = scalar_property(
        "note",
        min_count=0,
        max_count=None,
        datatype=None,
        datatypes=(XSD.string, RDF.langString),
    )
    var = Variable("note")
    (optional,) = scalar_bind_patterns(
        prop, var, subject=Variable("iri"), lang_tags=("en",), bound=False
    )
    assert isinstance(optional, OptionalPattern)
    _, union_filter = optional.child.children
    assert isinstance(union_filter, FilterPattern)
    assert union_filter.expression == OrExpr(
        (
            _lang_matches(var, "en"),
            CompareExpr(
                "=", FunctionCall("LANG", (TermExpr(var),)), TermExpr(Literal(""))
            ),
        )
    )
