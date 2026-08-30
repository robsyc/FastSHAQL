"""Node-expression dispatcher — ``core/translation/node_expr.py``.

Unit tier: ``translate_node_expr``'s constant / sparqlExpr / select /
pathValues / filterShape arms, and the if / exists / ListExpression lowerings
with their sub-variable naming discipline.
"""

from __future__ import annotations

import pytest
from rdflib import RDF, RDFS, Literal, URIRef, Variable
from rdflib.namespace import XSD

from fastshaql.core.ir.filter_shape import (
    FilterClass,
    FilterCompare,
    FilterDatatype,
    FilterHasValue,
    FilterRegex,
    FilterRootClass,
    FilterShapeIR,
)
from fastshaql.core.ir.node_expr import (
    ConstantListNodeExpr,
    ConstantNodeExpr,
    ExistsNodeExpr,
    FilterShapeNodeExpr,
    IfNodeExpr,
    InstancesOfNodeExpr,
    PathValuesNodeExpr,
    SelectNodeExpr,
    SparqlExprNodeExpr,
)
from fastshaql.core.ir.shacl_path import InversePath, PredicatePath
from fastshaql.core.sparql import (
    BindPattern,
    CompareExpr,
    ExistsExpr,
    FilterPattern,
    FunctionCall,
    GroupPattern,
    NotExpr,
    OptionalPattern,
    RawGraphPattern,
    RawSparqlExpr,
    TermExpr,
    TriplePattern,
    ValuesPattern,
)
from fastshaql.core.sparql import (
    InversePath as SparqlInversePath,
)
from fastshaql.core.sparql import (
    PredicatePath as SparqlPredicatePath,
)
from fastshaql.core.sparql import (
    SequencePath as SparqlSequencePath,
)
from fastshaql.core.sparql import (
    ZeroOrMorePath as SparqlZeroOrMorePath,
)
from fastshaql.core.sparql.terms import render_term
from fastshaql.core.translation.node_expr import (
    _substitute_focus_var,
    translate_node_expr,
)

EX = URIRef("http://example.org/")


def _exists(path: str) -> ExistsNodeExpr:
    """``shnex:exists`` over a predicate ``pathValues`` — the standard
    condition arm in the ``if`` tests."""
    return ExistsNodeExpr(PathValuesNodeExpr(path=PredicatePath(EX + path)))


@pytest.mark.parametrize(
    "term", [Literal("FastshaqlEMR", datatype=XSD.string), EX + "constant"]
)
def test_constant_emits_bind_pattern(term: URIRef | Literal) -> None:
    """A constant arm (literal or IRI) emits one ``BIND`` of the term."""
    ir = ConstantNodeExpr(term)
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("recordSource"),
    )
    assert len(patterns) == 1
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("recordSource")
    assert isinstance(bind.expr, TermExpr)
    assert bind.expr.term == term


# --- sh:sparqlExpr arm ---


def test_substitute_focus_var_word_boundary() -> None:
    assert _substitute_focus_var("STRLEN(STR($this))", Variable("iri")) == (
        "STRLEN(STR(?iri))"
    )
    assert _substitute_focus_var("$thisfoo", Variable("iri")) == "$thisfoo"
    assert _substitute_focus_var("foo$this", Variable("iri")) == "foo$this"


def test_substitute_focus_var_question_sigil() -> None:
    # $this and ?this denote the same variable ``this`` (SPARQL [163]/[164],
    # pre-bound per SHACL-SPARQL §3.3.1); both must substitute — a dangling
    # ?this would be an unbound variable.
    assert _substitute_focus_var("STRLEN(STR(?this))", Variable("iri")) == (
        "STRLEN(STR(?iri))"
    )


def test_substitute_focus_var_protects_string_literal() -> None:
    # A ``$this`` inside a string literal is a literal value, not a focus-node
    # reference — it must not be substituted (protected-region guarantee,
    # SPARQL 1.2 §19; mirrors expand_sparql_prefixes).
    assert (
        _substitute_focus_var(
            'CONCAT(STR($this), "literal $this here")', Variable("iri")
        )
        == 'CONCAT(STR(?iri), "literal $this here")'
    )


def test_substitute_focus_var_protects_iriref_and_comment() -> None:
    assert (
        _substitute_focus_var(
            "<http://example.org/$this> # $this\n$this ex:p ?o",
            Variable("iri"),
        )
        == "<http://example.org/$this> # $this\n?iri ex:p ?o"
    )


def test_sparql_expr_emits_bind_with_focus_substitution() -> None:
    ir = SparqlExprNodeExpr("STRLEN(STR($this))")
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("uriLength"),
    )
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert isinstance(bind.expr, RawSparqlExpr)
    assert bind.expr.text == "STRLEN(STR(?iri))"
    assert bind.var == Variable("uriLength")


# --- sh:select arm ---


def test_select_merge_emits_raw_graph_pattern() -> None:
    body = (
        "$this ex:givenName ?given .\n"
        "$this ex:familyName ?family .\n"
        'BIND(CONCAT(?given, " ", ?family) AS ?label)'
    )
    ir = SelectNodeExpr(body=body, projection_var="label")
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("label"),
    )
    assert len(patterns) == 1
    pattern = patterns[0]
    assert isinstance(pattern, RawGraphPattern)
    assert "?iri ex:givenName ?given" in pattern.text
    assert "$this" not in pattern.text


def test_select_projection_collision_rebinds() -> None:
    ir = SelectNodeExpr(body="$this ex:name ?fullName .", projection_var="fullName")
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("label"),
    )
    assert len(patterns) == 2
    assert isinstance(patterns[0], RawGraphPattern)
    bind = patterns[1]
    assert isinstance(bind, BindPattern)
    # The author's projection var is renamed onto the value var via the typed
    # AST (render_term), not a raw-text node — keeps the raw-text escape for
    # trusted author SPARQL only (ADR-0017).
    assert isinstance(bind.expr, TermExpr)
    assert bind.expr.term == Variable("fullName")
    assert bind.var == Variable("label")


# --- Term focus: the focus is any term — a variable or a constant
# IRI (the shape IRI at sh:targetNode position) ---


def test_sparql_expr_constant_focus_substitutes_iri_term() -> None:
    ir = SparqlExprNodeExpr("STR($this)")
    patterns = translate_node_expr(
        ir,
        focus_term=EX + "VariantShape",
        value_var=Variable("shapeIri"),
    )
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert isinstance(bind.expr, RawSparqlExpr)
    assert bind.expr.text == f"STR({render_term(EX + 'VariantShape')})"


def test_select_constant_focus_substitutes_iri_term() -> None:
    ir = SelectNodeExpr(body="$this ex:status ?status .", projection_var="status")
    patterns = translate_node_expr(
        ir,
        focus_term=EX + "VariantShape",
        value_var=Variable("status"),
    )
    assert isinstance(patterns[0], RawGraphPattern)
    assert patterns[0].text.startswith(f"{render_term(EX + 'VariantShape')} ex:status")


def test_path_values_at_constant_focus_reads_shape_iri() -> None:
    """``pathValues`` without ``focusNode`` at target position evaluates the
    path at the shape IRI — spec-faithful, usually empty."""
    ir = PathValuesNodeExpr(path=PredicatePath(EX + "topic"))
    patterns = translate_node_expr(
        ir,
        focus_term=EX + "VariantShape",
        value_var=Variable("v"),
    )
    assert patterns == [
        TriplePattern(
            subject=EX + "VariantShape",
            predicate=SparqlPredicatePath(EX + "topic"),
            object=Variable("v"),
        )
    ]


def test_substitute_focus_var_accepts_iri_term() -> None:
    assert (
        _substitute_focus_var("STR($this)", EX + "X") == "STR(<http://example.org/X>)"
    )


def test_instances_of_ignores_focus() -> None:
    """``instancesOf`` reads the class parameter, never the focus term."""
    ir = InstancesOfNodeExpr(classes=(EX + "Variant",))
    by_var = translate_node_expr(
        ir, focus_term=Variable("this"), value_var=Variable("v")
    )
    by_iri = translate_node_expr(ir, focus_term=EX + "Shape", value_var=Variable("v"))
    assert by_var == by_iri


# --- shnex:pathValues / shnex:filterShape arms ---


def test_instances_of_single_class_emits_subclass_closing_triple() -> None:
    """One class → the class IRI sits directly as the path object."""
    ir = InstancesOfNodeExpr(classes=(EX + "Variant",))
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("this"),
        value_var=Variable("v"),
    )
    assert len(patterns) == 1
    triple = patterns[0]
    assert isinstance(triple, TriplePattern)
    assert triple.subject == Variable("v")
    assert triple.object == EX + "Variant"
    assert triple.predicate == SparqlSequencePath(
        (
            SparqlPredicatePath(RDF.type),
            SparqlZeroOrMorePath(SparqlPredicatePath(RDFS.subClassOf)),
        )
    )


def test_instances_of_class_list_emits_values_pattern() -> None:
    """Multiple classes → the folded constants bind a ``_class_`` variable."""
    ir = InstancesOfNodeExpr(classes=(EX + "Substitution", EX + "Deletion"))
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("this"),
        value_var=Variable("v"),
    )
    assert len(patterns) == 2
    triple, values = patterns
    assert isinstance(triple, TriplePattern)
    assert triple.subject == Variable("v")
    assert triple.object == Variable("_class_v")
    assert triple.predicate == SparqlSequencePath(
        (
            SparqlPredicatePath(RDF.type),
            SparqlZeroOrMorePath(SparqlPredicatePath(RDFS.subClassOf)),
        )
    )
    assert values == ValuesPattern(
        Variable("_class_v"), (EX + "Substitution", EX + "Deletion")
    )


def test_path_values_emits_triple_with_mapped_path() -> None:
    ir = PathValuesNodeExpr(path=PredicatePath(EX + "inGene"))
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("variant"),
        value_var=Variable("gene"),
    )
    assert patterns == [
        TriplePattern(
            subject=Variable("variant"),
            predicate=SparqlPredicatePath(EX + "inGene"),
            object=Variable("gene"),
        )
    ]


def test_path_values_constant_focus_node_emits_constant_subject() -> None:
    ir = PathValuesNodeExpr(
        path=InversePath(PredicatePath(RDF.type)),
        focus_node=EX + "Concept",
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("ignored"),
        value_var=Variable("instance"),
    )
    assert patterns == [
        TriplePattern(
            subject=EX + "Concept",
            predicate=SparqlInversePath(SparqlPredicatePath(RDF.type)),
            object=Variable("instance"),
        )
    ]


def test_filter_shape_pattern_lowers_to_regex_str() -> None:
    """``sh:pattern`` → ``FILTER(REGEX(STR(?v), "pat"[, "flags"]))`` — the
    STR wrap is required: REGEX's first argument must be a string literal
    (SPARQL §17.4.3), and the spec matches the SPARQL str form of the node
    (Core §7.4.3), IRIs included."""
    ir = FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(conjuncts=(FilterRegex(Literal("^ex:"), None),)),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("candidate"),
    )
    regex = patterns[1]
    assert isinstance(regex, FilterPattern)
    assert regex.expression == FunctionCall(
        "REGEX",
        (
            FunctionCall("STR", (TermExpr(Variable("candidate")),)),
            TermExpr(Literal("^ex:")),
        ),
    )


def test_filter_shape_pattern_flags_pass_third_argument() -> None:
    ir = FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(conjuncts=(FilterRegex(Literal("^ex:"), Literal("i")),)),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("candidate"),
    )
    regex = patterns[1]
    assert isinstance(regex, FilterPattern)
    call = regex.expression
    assert isinstance(call, FunctionCall)
    assert call.name == "REGEX"
    assert len(call.args) == 3
    assert call.args[2] == TermExpr(Literal("i"))


def test_filter_shape_lowering_conjuncts() -> None:
    """Class → type triple; datatype → FILTER(datatype(?v) = dt); range →
    FILTER comparison; hasValue → equality; conjunction order preserved."""
    ir = FilterShapeNodeExpr(
        nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
        shape=FilterShapeIR(
            conjuncts=(
                FilterClass((EX + "Person",)),
                FilterDatatype(XSD.string),
                FilterCompare(">=", Literal(18)),
                FilterHasValue(Literal("x")),
            )
        ),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("candidate"),
    )
    assert patterns[0] == TriplePattern(
        subject=Variable("iri"),
        predicate=SparqlPredicatePath(EX + "child"),
        object=Variable("candidate"),
    )
    assert patterns[1] == TriplePattern(
        subject=Variable("candidate"),
        predicate=SparqlPredicatePath(RDF.type),
        object=EX + "Person",
    )

    datatype_call, range_cmp, equality = patterns[2], patterns[3], patterns[4]
    assert isinstance(datatype_call, FilterPattern)
    call = datatype_call.expression
    assert isinstance(call, CompareExpr)
    assert isinstance(call.left, FunctionCall)
    assert call.left.name == "datatype"
    assert call.right == TermExpr(XSD.string)
    assert isinstance(range_cmp, FilterPattern)
    assert range_cmp.expression == CompareExpr(
        ">=", TermExpr(Variable("candidate")), TermExpr(Literal(18))
    )
    assert isinstance(equality, FilterPattern)
    assert equality.expression == CompareExpr(
        "=", TermExpr(Variable("candidate")), TermExpr(Literal("x"))
    )


def test_filter_shape_class_list_lowers_as_values_union() -> None:
    """``sh:class ( A B )`` — type join against a VALUES union (Core §7.1.1);
    two separate conjuncts lower as two triples (conjunction)."""
    patterns = translate_node_expr(
        FilterShapeNodeExpr(
            nodes=ConstantNodeExpr(EX + "thing"),
            shape=FilterShapeIR(
                conjuncts=(
                    FilterClass((EX + "Cat", EX + "Dog")),
                    FilterClass((EX + "Pet",)),
                )
            ),
        ),
        focus_term=Variable("iri"),
        value_var=Variable("pet"),
    )
    assert patterns[1] == TriplePattern(
        subject=Variable("pet"),
        predicate=SparqlPredicatePath(RDF.type),
        object=Variable("pet_cls0"),
    )
    assert patterns[2] == ValuesPattern(Variable("pet_cls0"), (EX + "Cat", EX + "Dog"))
    assert patterns[3] == TriplePattern(
        subject=Variable("pet"),
        predicate=SparqlPredicatePath(RDF.type),
        object=EX + "Pet",
    )


def test_filter_shape_empty_class_list_matches_nothing() -> None:
    """``sh:class ()`` — union over no classes: every value violates (the
    Core §7.1.1 formal text), lowering to FILTER(false)."""
    patterns = translate_node_expr(
        FilterShapeNodeExpr(
            nodes=ConstantNodeExpr(EX + "thing"),
            shape=FilterShapeIR(conjuncts=(FilterClass(()),)),
        ),
        focus_term=Variable("iri"),
        value_var=Variable("pet"),
    )
    assert patterns[1] == FilterPattern(TermExpr(Literal(False)))


def test_filter_shape_root_class_lowers_subclass_star_walk() -> None:
    """``sh:rootClass`` — ``?v rdfs:subClassOf* <root>`` (Core §7.9.4); a list
    of roots walks against a VALUES union."""
    single, multi = (
        translate_node_expr(
            FilterShapeNodeExpr(
                nodes=ConstantNodeExpr(EX + "thing"),
                shape=FilterShapeIR(conjuncts=(conjunct,)),
            ),
            focus_term=Variable("iri"),
            value_var=Variable("term"),
        )
        for conjunct in (
            FilterRootClass((EX + "Animal",)),
            FilterRootClass((EX + "Animal", EX + "Plant")),
        )
    )
    assert single[1] == TriplePattern(
        subject=Variable("term"),
        predicate=SparqlZeroOrMorePath(SparqlPredicatePath(RDFS.subClassOf)),
        object=EX + "Animal",
    )
    assert multi[1] == TriplePattern(
        subject=Variable("term"),
        predicate=SparqlZeroOrMorePath(SparqlPredicatePath(RDFS.subClassOf)),
        object=Variable("term_root0"),
    )
    assert multi[2] == ValuesPattern(
        Variable("term_root0"), (EX + "Animal", EX + "Plant")
    )


def test_filter_shape_inside_multivalued_if_branches_stays_in_each_arm() -> None:
    """Conjuncts must not outlive the conditioned arm that binds the value var.

    The parser normalises ``filterShape`` over an ``shnex:if`` into this shape
    (an ``if`` over two filter shapes) so that each ``OPTIONAL`` arm carries its
    own class triple. Emitted after the arms instead, the triple would run with
    the value variable unbound and enumerate every candidate in the graph.
    """
    shape = FilterShapeIR(conjuncts=(FilterClass((EX + "Target",)),))
    ir = IfNodeExpr(
        cond=ExistsNodeExpr(inner=PathValuesNodeExpr(PredicatePath(EX + "flag"))),
        then=FilterShapeNodeExpr(
            nodes=PathValuesNodeExpr(path=PredicatePath(EX + "goodLink")), shape=shape
        ),
        otherwise=FilterShapeNodeExpr(
            nodes=PathValuesNodeExpr(path=PredicatePath(EX + "badLink")), shape=shape
        ),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("links"),
    )
    assert len(patterns) == 2
    type_triple = TriplePattern(
        subject=Variable("links"),
        predicate=SparqlPredicatePath(RDF.type),
        object=EX + "Target",
    )
    for arm, predicate in zip(patterns, ("goodLink", "badLink"), strict=True):
        assert isinstance(arm, OptionalPattern)
        path_triple, arm_type_triple, guard = arm.child.children
        assert path_triple == TriplePattern(
            subject=Variable("iri"),
            predicate=SparqlPredicatePath(EX + predicate),
            object=Variable("links"),
        )
        assert arm_type_triple == type_triple
        assert isinstance(guard, FilterPattern)


# --- shnex:if / shnex:exists / shnex:ListExpression arms ---


def test_exists_emits_bind_exists() -> None:
    """A bare ``shnex:exists`` binds a total boolean — never null."""
    ir = _exists("inGene")
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("hasGene"),
    )
    assert len(patterns) == 1
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("hasGene")
    assert isinstance(bind.expr, ExistsExpr)
    (triple,) = bind.expr.pattern.children
    assert triple == TriplePattern(
        subject=Variable("iri"),
        predicate=SparqlPredicatePath(EX + "inGene"),
        object=Variable("_exists_hasGene"),
    )


def test_if_single_valued_constant_branches_emit_bind_if() -> None:
    """Both branches constant + exists condition → ``BIND(IF(EXISTS{…}, t, e))``
    (the single-valued form; an EXISTS test is total, so it needs no guard)."""
    ir = IfNodeExpr(
        cond=_exists("capitalOf"),
        then=ConstantNodeExpr(Literal("blue")),
        otherwise=ConstantNodeExpr(Literal("red")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("fillColor"),
    )
    assert len(patterns) == 1
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("fillColor")
    call = bind.expr
    assert isinstance(call, FunctionCall)
    assert call.name == "IF"
    cond, then_expr, else_expr = call.args
    assert isinstance(cond, ExistsExpr)
    assert then_expr == TermExpr(Literal("blue"))
    assert else_expr == TermExpr(Literal("red"))


def test_nested_single_valued_if_inlines_into_single_bind() -> None:
    """``if(E1, if(E2, A, B), C)`` with statically single-valued everything
    lowers to ONE ``BIND`` with the nested ``IF`` inlined.

    The pre-bind form (``BIND(IF(E2,A,B) AS ?_then_v)`` + ``BIND(IF(E1,
    ?_then_v, C) AS ?v)``) is wrong on rdflib 7.6.0 inside an ``OPTIONAL``:
    a ``BIND`` whose expression contains ``EXISTS``, preceded by another
    ``BIND``, has its ``EXISTS`` evaluated with forgotten ambient bindings —
    always-true — so focus nodes matching neither condition get the wrong
    branch. The single-``BIND`` form is verified correct (handoff Slice 5a).
    """
    ir = IfNodeExpr(
        cond=_exists("p1"),
        then=IfNodeExpr(
            cond=_exists("p2"),
            then=ConstantNodeExpr(Literal("A")),
            otherwise=ConstantNodeExpr(Literal("B")),
        ),
        otherwise=ConstantNodeExpr(Literal("C")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("triage"),
    )
    assert len(patterns) == 1
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("triage")
    outer = bind.expr
    assert isinstance(outer, FunctionCall)
    assert outer.name == "IF"
    outer_cond, outer_then, outer_else = outer.args
    assert isinstance(outer_cond, ExistsExpr)
    assert outer_else == TermExpr(Literal("C"))
    assert isinstance(outer_then, FunctionCall)
    assert outer_then.name == "IF"
    inner_cond, inner_then, inner_else = outer_then.args
    assert isinstance(inner_cond, ExistsExpr)
    assert inner_then == TermExpr(Literal("A"))
    assert inner_else == TermExpr(Literal("B"))
    # Nested EXISTS groups carry distinct sub-variables (role-prefixed bases).
    (outer_triple,) = outer_cond.pattern.children
    (inner_triple,) = inner_cond.pattern.children
    assert isinstance(outer_triple, TriplePattern)
    assert isinstance(inner_triple, TriplePattern)
    assert outer_triple.object == Variable("_exists_triage")
    assert inner_triple.object == Variable("_exists__then_triage")


def test_if_missing_then_emits_else_arm_only_optional() -> None:
    """Else-only ``if`` mirrors the then-only form; the arm negates the
    condition. This one is an ``EXISTS`` test, so no error-routing wrapper."""
    ir = IfNodeExpr(
        cond=_exists("a"),
        then=None,
        otherwise=ConstantNodeExpr(Literal("fallback")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    assert len(patterns) == 1
    (opt,) = patterns
    assert isinstance(opt, OptionalPattern)
    bind, filt = opt.child.children
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("chosen")
    assert isinstance(filt, FilterPattern)
    assert filt.expression == NotExpr(
        ExistsExpr(
            GroupPattern(
                (
                    TriplePattern(
                        subject=Variable("iri"),
                        predicate=SparqlPredicatePath(EX + "a"),
                        object=Variable("_exists_chosen"),
                    ),
                )
            )
        )
    )


def test_exists_over_filter_shape_inner_groups_patterns() -> None:
    """An ``exists`` inner may lower to multiple patterns — the ``EXISTS``
    group carries the candidate join and the conjunct filter together."""
    ir = ExistsNodeExpr(
        inner=FilterShapeNodeExpr(
            nodes=PathValuesNodeExpr(path=PredicatePath(EX + "child")),
            shape=FilterShapeIR(conjuncts=(FilterHasValue(Literal("x")),)),
        )
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("hasNamedChild"),
    )
    assert len(patterns) == 1
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("hasNamedChild")
    assert isinstance(bind.expr, ExistsExpr)
    triple, filt = bind.expr.pattern.children
    assert triple == TriplePattern(
        subject=Variable("iri"),
        predicate=SparqlPredicatePath(EX + "child"),
        object=Variable("_exists_hasNamedChild"),
    )
    assert isinstance(filt, FilterPattern)
    assert filt.expression == CompareExpr(
        "=", TermExpr(Variable("_exists_hasNamedChild")), TermExpr(Literal("x"))
    )


def test_if_value_condition_strict_true_with_else_on_error_guard() -> None:
    """A value condition compiles as ``cond = true`` — spec-strict, since SPARQL
    EBV would truthify a non-boolean — inlined into the single ``BIND``; the
    ``IF`` guards it with ``COALESCE(test, false)`` so errored conditions take
    the else branch (ADR-0015)."""
    ir = IfNodeExpr(
        cond=SparqlExprNodeExpr("BOUND(?iri)"),
        then=ConstantNodeExpr(Literal("yes")),
        otherwise=ConstantNodeExpr(Literal("no")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("flagged"),
    )
    assert len(patterns) == 1
    if_bind = patterns[0]
    assert isinstance(if_bind, BindPattern)
    assert if_bind.var == Variable("flagged")
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    assert if_call.name == "IF"
    guard, then_expr, else_expr = if_call.args
    assert isinstance(guard, FunctionCall)
    assert guard.name == "COALESCE"
    strict, fallback = guard.args
    assert strict == CompareExpr(
        "=", RawSparqlExpr("BOUND(?iri)"), TermExpr(Literal(True))
    )
    assert fallback == TermExpr(Literal(False))
    assert then_expr == TermExpr(Literal("yes"))
    assert else_expr == TermExpr(Literal("no"))


def test_if_single_valued_expression_branches_inline() -> None:
    """Non-constant pure branches (``sh:sparqlExpr``, ``shnex:exists``, nested
    single-valued ``if``) inline as ``IF`` operands — one ``BIND`` total, no
    ``_then_``/``_else_`` sub-bindings (rdflib 7.6.0 EXISTS-in-BIND trap;
    see the translator module docstring)."""
    ir = IfNodeExpr(
        cond=_exists("a"),
        then=SparqlExprNodeExpr("STRLEN(STR(?x))"),
        otherwise=ConstantNodeExpr(Literal(0)),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("score"),
    )
    assert len(patterns) == 1
    if_bind = patterns[0]
    assert isinstance(if_bind, BindPattern)
    assert if_bind.var == Variable("score")
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    cond, then_expr, else_expr = if_call.args
    assert isinstance(cond, ExistsExpr)
    assert then_expr == RawSparqlExpr("STRLEN(STR(?x))")
    assert else_expr == TermExpr(Literal(0))


def test_if_exists_branch_inlines_as_if_operand() -> None:
    """``if(exists(p1), exists(p2), C)`` — an exists *branch* inlines too;
    the pre-bind form put ``BIND(EXISTS{…} AS ?_then_v)`` before a
    ``BIND``-with-``EXISTS``, the always-true trap on rdflib 7.6.0."""
    ir = IfNodeExpr(
        cond=_exists("p1"),
        then=_exists("p2"),
        otherwise=ConstantNodeExpr(Literal("C")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    assert len(patterns) == 1
    if_bind = patterns[0]
    assert isinstance(if_bind, BindPattern)
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    cond, then_expr, else_expr = if_call.args
    assert isinstance(cond, ExistsExpr)
    assert isinstance(then_expr, ExistsExpr)
    assert else_expr == TermExpr(Literal("C"))


def test_if_constant_condition_inlines_strict_true() -> None:
    """A constant condition inlines as ``true = true`` (spec-strict, not EBV
    truthified) — no sub-``BIND`` for constants."""
    ir = IfNodeExpr(
        cond=ConstantNodeExpr(Literal(True)),
        then=ConstantNodeExpr(Literal("yes")),
        otherwise=ConstantNodeExpr(Literal("no")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    assert len(patterns) == 1
    if_bind = patterns[0]
    assert isinstance(if_bind, BindPattern)
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    guard, then_expr, else_expr = if_call.args
    # Non-total condition: the strict comparison is wrapped in the else-on-error
    # guard even though it is a tautology here — totality is structural.
    assert isinstance(guard, FunctionCall)
    assert guard.name == "COALESCE"
    assert guard.args[0] == CompareExpr(
        "=", TermExpr(Literal(True)), TermExpr(Literal(True))
    )
    assert guard.args[1] == TermExpr(Literal(False))
    assert then_expr == TermExpr(Literal("yes"))
    assert else_expr == TermExpr(Literal("no"))


def test_if_nested_if_condition_inlines() -> None:
    """A pure nested-``if`` condition inlines as the strict ``IF(…) = true``
    comparison — the whole expression stays one ``BIND``."""
    ir = IfNodeExpr(
        cond=IfNodeExpr(
            cond=_exists("a"),
            then=ConstantNodeExpr(Literal(True)),
            otherwise=ConstantNodeExpr(Literal(False)),
        ),
        then=ConstantNodeExpr(Literal("yes")),
        otherwise=ConstantNodeExpr(Literal("no")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    assert len(patterns) == 1
    if_bind = patterns[0]
    assert isinstance(if_bind, BindPattern)
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    guard = if_call.args[0]
    assert isinstance(guard, FunctionCall)
    assert guard.name == "COALESCE"
    strict = guard.args[0]
    assert isinstance(strict, CompareExpr)
    assert strict.op == "="
    assert isinstance(strict.left, FunctionCall)
    assert strict.left.name == "IF"


def test_if_impure_condition_pure_branches_materializes_with_guard() -> None:
    """Form 2 with a *non-total* materialized condition: an impure condition
    (``filterShape`` over a constant) with constant branches materialises
    ``?_cond_{base}`` and guards the ``IF`` test with ``COALESCE(…, false)``
    (ADR-0015 else-on-error deviation)."""
    ir = IfNodeExpr(
        cond=FilterShapeNodeExpr(
            nodes=ConstantNodeExpr(Literal("raw")),
            shape=FilterShapeIR(conjuncts=(FilterHasValue(Literal("x")),)),
        ),
        then=ConstantNodeExpr(Literal("yes")),
        otherwise=ConstantNodeExpr(Literal("no")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    cond_optional, if_bind = patterns
    # The impure condition's sub-emission is contained in its own OPTIONAL:
    # a failed conjunct leaves ?_cond unbound (empty output → not ( true ) →
    # else, node-expr §4.1.6), never a dropped row.
    assert isinstance(cond_optional, OptionalPattern)
    cond_bind, conjunct = cond_optional.child.children
    assert isinstance(cond_bind, BindPattern)
    assert cond_bind.var == Variable("_cond_chosen")
    assert isinstance(conjunct, FilterPattern)
    assert isinstance(if_bind, BindPattern)
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    guard, then_expr, else_expr = if_call.args
    assert isinstance(guard, FunctionCall)
    assert guard.name == "COALESCE"
    assert guard.args[0] == CompareExpr(
        "=", TermExpr(Variable("_cond_chosen")), TermExpr(Literal(True))
    )
    assert guard.args[1] == TermExpr(Literal(False))
    assert then_expr == TermExpr(Literal("yes"))
    assert else_expr == TermExpr(Literal("no"))


def test_if_impure_else_branch_falls_back_to_sub_binds() -> None:
    """A pure *then* with an impure *else* (``filterShape``) blocks Form 1 at
    the else operand — Form 2 materialises the condition and sub-binds only
    the impure branch (constants stay inlined)."""
    ir = IfNodeExpr(
        cond=_exists("flag"),
        then=ConstantNodeExpr(Literal("yes")),
        otherwise=FilterShapeNodeExpr(
            nodes=ConstantNodeExpr(Literal("raw")),
            shape=FilterShapeIR(conjuncts=(FilterHasValue(Literal("x")),)),
        ),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    cond_bind, else_optional, if_bind = patterns
    assert isinstance(cond_bind, BindPattern)
    assert cond_bind.var == Variable("_cond_chosen")
    # The impure branch's sub-emission is contained in its own OPTIONAL:
    # its conjunct FILTER must mean "no else value" (node-expr §4.2.5),
    # never a dropped or corrupted then-routed row.
    assert isinstance(else_optional, OptionalPattern)
    else_bind, conjunct = else_optional.child.children
    assert isinstance(else_bind, BindPattern)
    assert else_bind.var == Variable("_else_chosen")
    assert isinstance(conjunct, FilterPattern)
    assert isinstance(if_bind, BindPattern)
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    # Total condition (BIND of an EXISTS always binds): no COALESCE guard.
    assert if_call.args[0] == CompareExpr(
        "=", TermExpr(Variable("_cond_chosen")), TermExpr(Literal(True))
    )
    assert if_call.args[1] == TermExpr(Literal("yes"))
    assert if_call.args[2] == TermExpr(Variable("_else_chosen"))


def test_if_nested_missing_else_branch_falls_back_to_sub_bind_form() -> None:
    """A nested single-valued ``if`` missing its else cannot inline (the
    empty-list semantics need the ``OPTIONAL``-arm form), so the outer
    single-valued ``if`` falls back to Form 2 and the nested arm sub-binds."""
    ir = IfNodeExpr(
        cond=_exists("flag"),
        then=IfNodeExpr(
            cond=_exists("a"),
            then=ConstantNodeExpr(Literal("yes")),
            otherwise=None,
        ),
        otherwise=ConstantNodeExpr(Literal("no")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    cond_bind, *then_arm_patterns, if_bind = patterns
    assert isinstance(cond_bind, BindPattern)
    assert cond_bind.var == Variable("_cond_chosen")
    assert any(isinstance(p, OptionalPattern) for p in then_arm_patterns), (
        then_arm_patterns
    )
    assert isinstance(if_bind, BindPattern)
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    assert if_call.args[1] == TermExpr(Variable("_then_chosen"))
    assert if_call.args[2] == TermExpr(Literal("no"))


def test_if_multivalued_branches_emit_conditioned_two_optionals() -> None:
    """Multi-valued branches → two OPTIONAL arms sharing the value var. An
    ``EXISTS`` test is total, so the else arm negates it directly — no
    error-routing ``COALESCE`` wrapper (contrast the value-condition test)."""
    ir = IfNodeExpr(
        cond=_exists("reviewed"),
        then=PathValuesNodeExpr(path=PredicatePath(EX + "reviewedLink")),
        otherwise=PathValuesNodeExpr(path=PredicatePath(EX + "provisionalLink")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("links"),
    )
    assert len(patterns) == 2
    then_opt, else_opt = patterns
    assert isinstance(then_opt, OptionalPattern)
    assert isinstance(else_opt, OptionalPattern)
    then_triple, then_filter = then_opt.child.children
    assert then_triple == TriplePattern(
        subject=Variable("iri"),
        predicate=SparqlPredicatePath(EX + "reviewedLink"),
        object=Variable("links"),
    )
    assert isinstance(then_filter, FilterPattern)
    assert then_filter.expression == ExistsExpr(
        GroupPattern(
            (
                TriplePattern(
                    subject=Variable("iri"),
                    predicate=SparqlPredicatePath(EX + "reviewed"),
                    object=Variable("_exists_links"),
                ),
            )
        )
    )
    else_triple, else_filter = else_opt.child.children
    assert else_triple == TriplePattern(
        subject=Variable("iri"),
        predicate=SparqlPredicatePath(EX + "provisionalLink"),
        object=Variable("links"),
    )
    assert isinstance(else_filter, FilterPattern)
    assert else_filter.expression == NotExpr(
        ExistsExpr(
            GroupPattern(
                (
                    TriplePattern(
                        subject=Variable("iri"),
                        predicate=SparqlPredicatePath(EX + "reviewed"),
                        object=Variable("_exists_links"),
                    ),
                )
            )
        )
    )


def test_if_multivalued_value_condition_else_arm_routes_errors_to_else() -> None:
    """A value condition can error, so the arm ``FILTER`` s carry the strict
    test inline — bare on the then arm (an errored ``FILTER`` already
    excludes the row), ``COALESCE(!…, true)`` on the else arm — the
    else-on-error deviation (ADR-0015) in the
    two-OPTIONAL form. Inlining the test (no enclosing ``?_cond_`` BIND)
    keeps the form safe inside OPTIONAL-wrapped entity groups."""
    ir = IfNodeExpr(
        cond=SparqlExprNodeExpr("?missing > 1"),
        then=PathValuesNodeExpr(path=PredicatePath(EX + "reviewedLink")),
        otherwise=PathValuesNodeExpr(path=PredicatePath(EX + "provisionalLink")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("links"),
    )
    then_opt, else_opt = patterns
    strict = CompareExpr("=", RawSparqlExpr("?missing > 1"), TermExpr(Literal(True)))
    assert isinstance(then_opt, OptionalPattern)
    # The then side needs no guard — an errored FILTER already excludes the row.
    assert then_opt.child.children[-1] == FilterPattern(strict)
    assert isinstance(else_opt, OptionalPattern)
    assert else_opt.child.children[-1] == FilterPattern(
        FunctionCall("COALESCE", (NotExpr(strict), TermExpr(Literal(True))))
    )


def test_if_missing_else_emits_single_conditioned_optional() -> None:
    """A missing branch is the empty list — its arm is simply absent; only
    single-valued *and* fully-present branches take the BIND+IF form."""
    ir = IfNodeExpr(
        cond=_exists("a"),
        then=ConstantNodeExpr(Literal("yes")),
        otherwise=None,
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    assert len(patterns) == 1
    (opt,) = patterns
    assert isinstance(opt, OptionalPattern)
    bind, filt = opt.child.children
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("chosen")
    assert isinstance(filt, FilterPattern)
    assert isinstance(filt.expression, ExistsExpr)


def test_if_multivalued_value_condition_inlines_into_arm_filters() -> None:
    """A pure value condition inlines into both arm ``FILTER`` s — no
    ``?_cond_<value>`` BIND at the enclosing scope, where it would precede
    (or be preceded by) other ``BIND`` s inside an OPTIONAL-wrapped entity
    group; the then-arm filter is the strict ``= true`` comparison."""
    ir = IfNodeExpr(
        cond=SparqlExprNodeExpr("BOUND(?iri)"),
        then=PathValuesNodeExpr(path=PredicatePath(EX + "a")),
        otherwise=PathValuesNodeExpr(path=PredicatePath(EX + "b")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("vals"),
    )
    assert len(patterns) == 2
    then_opt, else_opt = patterns
    assert isinstance(then_opt, OptionalPattern)
    _, then_filter = then_opt.child.children
    assert isinstance(then_filter, FilterPattern)
    assert then_filter.expression == CompareExpr(
        "=", RawSparqlExpr("BOUND(?iri)"), TermExpr(Literal(True))
    )
    assert isinstance(else_opt, OptionalPattern)
    # Else-arm guard shape is pinned by the error-routing test above.
    assert isinstance(else_opt.child.children[-1], FilterPattern)


def test_constant_list_emits_values_pattern() -> None:
    ir = ConstantListNodeExpr((Literal("sweet"), EX + "Umami"))
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("flavors"),
    )
    assert patterns == [
        ValuesPattern(Variable("flavors"), (Literal("sweet"), EX + "Umami"))
    ]


def test_nested_if_in_branch_inlines_without_sub_variables() -> None:
    """A nested ``shnex:if`` inside a branch of a value-conditioned outer if
    composes into one ``BIND`` — nested ``IF`` s, inlined strict tests, and
    no ``_cond_``/``_then_`` variables at all (the old sub-variable
    collision hazard is vacuous in the inlined form)."""
    ir = IfNodeExpr(
        cond=SparqlExprNodeExpr("BOUND(?iri)"),
        then=IfNodeExpr(
            cond=SparqlExprNodeExpr("BOUND(?x)"),
            then=ConstantNodeExpr(Literal("a")),
            otherwise=ConstantNodeExpr(Literal("b")),
        ),
        otherwise=ConstantNodeExpr(Literal("c")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    assert len(patterns) == 1
    bind = patterns[0]
    assert isinstance(bind, BindPattern)
    assert bind.var == Variable("chosen")
    outer = bind.expr
    assert isinstance(outer, FunctionCall)
    assert outer.name == "IF"
    outer_guard, outer_then, outer_else = outer.args
    assert isinstance(outer_guard, FunctionCall)
    assert outer_guard.name == "COALESCE"
    assert outer_guard.args[0] == CompareExpr(
        "=", RawSparqlExpr("BOUND(?iri)"), TermExpr(Literal(True))
    )
    assert outer_else == TermExpr(Literal("c"))
    assert isinstance(outer_then, FunctionCall)
    assert outer_then.name == "IF"
    inner_guard, inner_then, inner_else = outer_then.args
    assert isinstance(inner_guard, FunctionCall)
    assert inner_guard.args[0] == CompareExpr(
        "=", RawSparqlExpr("BOUND(?x)"), TermExpr(Literal(True))
    )
    assert inner_then == TermExpr(Literal("a"))
    assert inner_else == TermExpr(Literal("b"))


def test_if_filter_shape_branch_materializes_condition_first() -> None:
    """A ``shnex:filterShape`` branch needs sub-``BIND`` s (its conjunct
    ``FILTER`` s read a bound variable), so the sub-``BIND`` fallback fires:
    the condition materialises into ``?_cond_{base}`` *first* — keeping any
    ``EXISTS`` ahead of later ``BIND`` s — the branch sub-emission is
    contained in its own ``OPTIONAL`` (a failed conjunct means "no then
    value", never a dropped or corrupted row), and the trailing value
    ``BIND`` references variables only (the rdflib always-true trap;
    module docstring)."""
    ir = IfNodeExpr(
        cond=_exists("flag"),
        then=FilterShapeNodeExpr(
            nodes=SparqlExprNodeExpr("STR(?iri)"),
            shape=FilterShapeIR(conjuncts=(FilterHasValue(Literal("x")),)),
        ),
        otherwise=ConstantNodeExpr(Literal("c")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("chosen"),
    )
    cond_bind, then_optional, if_bind = patterns
    assert isinstance(cond_bind, BindPattern)
    assert cond_bind.var == Variable("_cond_chosen")
    assert isinstance(cond_bind.expr, ExistsExpr)
    assert isinstance(then_optional, OptionalPattern)
    branch_bind, conjunct = then_optional.child.children
    assert isinstance(branch_bind, BindPattern)
    assert branch_bind.var == Variable("_then_chosen")
    assert isinstance(conjunct, FilterPattern)
    assert conjunct.expression == CompareExpr(
        "=", TermExpr(Variable("_then_chosen")), TermExpr(Literal("x"))
    )
    assert isinstance(if_bind, BindPattern)
    assert if_bind.var == Variable("chosen")
    if_call = if_bind.expr
    assert isinstance(if_call, FunctionCall)
    assert if_call.name == "IF"
    # Total materialized condition (BIND of an EXISTS always binds): no guard.
    assert if_call.args[0] == CompareExpr(
        "=", TermExpr(Variable("_cond_chosen")), TermExpr(Literal(True))
    )
    assert if_call.args[1] == TermExpr(Variable("_then_chosen"))
    assert if_call.args[2] == TermExpr(Literal("c"))


def test_if_multivalued_impure_condition_keeps_materialized_cond_var() -> None:
    """Multivalued branches with an *impure* condition (a nested if carrying
    a ``filterShape`` branch) keep the materialised-condition form: sub-BINDs
    plus ``?_cond_{base}`` at the enclosing scope, arm ``FILTER`` s comparing
    the variable — bare on the then arm, ``COALESCE(!…, true)`` on the else
    arm (the nested condition is non-total). Pure conditions inline instead
    (contrast the test above); this pins the fallback that remains for
    conditions needing sub-BINDs."""
    inner_shape = FilterShapeIR(conjuncts=(FilterHasValue(Literal("x")),))
    ir = IfNodeExpr(
        cond=IfNodeExpr(
            cond=_exists("a"),
            then=FilterShapeNodeExpr(
                nodes=SparqlExprNodeExpr("STR(?iri)"), shape=inner_shape
            ),
            otherwise=ConstantNodeExpr(Literal(True)),
        ),
        then=PathValuesNodeExpr(path=PredicatePath(EX + "a")),
        otherwise=PathValuesNodeExpr(path=PredicatePath(EX + "c")),
    )
    patterns = translate_node_expr(
        ir,
        focus_term=Variable("iri"),
        value_var=Variable("vals"),
    )
    # The impure condition materialises as sub-BINDs + conjunct FILTERs +
    # ``?_cond_vals`` (the nested if's own value BIND, last of its block).
    cond_bind = patterns[-3]
    then_arm, else_arm = patterns[-2], patterns[-1]
    assert isinstance(cond_bind, BindPattern)
    assert cond_bind.var == Variable("_cond_vals")
    assert isinstance(then_arm, OptionalPattern)
    triple, arm_filter = then_arm.child.children
    assert triple == TriplePattern(
        subject=Variable("iri"),
        predicate=SparqlPredicatePath(EX + "a"),
        object=Variable("vals"),
    )
    assert arm_filter == FilterPattern(
        CompareExpr("=", TermExpr(Variable("_cond_vals")), TermExpr(Literal(True)))
    )
    strict = CompareExpr("=", TermExpr(Variable("_cond_vals")), TermExpr(Literal(True)))
    assert isinstance(else_arm, OptionalPattern)
    assert else_arm.child.children[-1] == FilterPattern(
        FunctionCall("COALESCE", (NotExpr(strict), TermExpr(Literal(True))))
    )


def test_boolean_literals_render_canonical() -> None:
    """``Literal(True)`` renders as SPARQL ``true`` (canonical BooleanLiteral),
    not the verbose typed form."""
    assert render_term(Literal(True)) == "true"
    assert render_term(Literal(False)) == "false"
    assert render_term(Literal("true")) == '"true"'
