"""SPARQL filter expression rendering — ``core/sparql/expressions.py``.

Unit tier: render output of the expression AST nodes — ``TermExpr``,
``CompareExpr``, ``FunctionCall``, ``InExpr``, ``AndExpr``/``OrExpr``
parenthesization, ``NotExpr``, and ``ExistsExpr``.

Order: term → compare operators → function call → IN → AND/OR combinators → NOT → EXISTS.
"""

from __future__ import annotations

from rdflib import Literal, URIRef, Variable
from rdflib.namespace import RDF, XSD

from fastshaql.core.sparql import (
    AndExpr,
    CompareExpr,
    ComparisonOp,
    ExistsExpr,
    FunctionCall,
    GroupPattern,
    InExpr,
    NotExpr,
    OrExpr,
    PredicatePath,
    RawSparqlExpr,
    TermExpr,
    TriplePattern,
)

EX = URIRef("http://example.org/")
RDF_TYPE = RDF.type


# --- Expressions ---


def test_term_expr_renders_variable() -> None:
    assert TermExpr(Variable("x")).render() == "?x"


def test_compare_expr_renders_all_operators() -> None:
    left = TermExpr(Variable("age"))
    right = TermExpr(Literal(25, datatype=XSD.integer))
    cases: list[tuple[ComparisonOp, str]] = [
        ("=", '?age = "25"^^<http://www.w3.org/2001/XMLSchema#integer>'),
        ("!=", '?age != "25"^^<http://www.w3.org/2001/XMLSchema#integer>'),
        (">", '?age > "25"^^<http://www.w3.org/2001/XMLSchema#integer>'),
        (">=", '?age >= "25"^^<http://www.w3.org/2001/XMLSchema#integer>'),
        ("<", '?age < "25"^^<http://www.w3.org/2001/XMLSchema#integer>'),
        ("<=", '?age <= "25"^^<http://www.w3.org/2001/XMLSchema#integer>'),
    ]
    for op, expected in cases:
        expr = CompareExpr(op=op, left=left, right=right)
        assert expr.render() == expected


def test_compare_expr_brackets_raw_operand() -> None:
    """``RelationalExpression`` allows one relational per expression (SPARQL
    §19 grammar) — a raw author operand ending in its own comparison must be
    bracketed before ``op`` composes, or the result is unparseable."""
    expr = CompareExpr(
        op="=",
        left=RawSparqlExpr("?score > 0.4"),
        right=TermExpr(Literal(True)),
    )
    assert expr.render() == "(?score > 0.4) = true"


def test_compare_expr_brackets_compare_operand() -> None:
    """Nested :class:`CompareExpr` operands bracket for the same grammar
    reason; self-delimiting leaves stay bare."""
    inner = CompareExpr(
        op=">",
        left=TermExpr(Variable("x")),
        right=TermExpr(Literal(1, datatype=XSD.integer)),
    )
    outer = CompareExpr(op="=", left=inner, right=TermExpr(Literal(True)))
    assert (
        outer.render()
        == '(?x > "1"^^<http://www.w3.org/2001/XMLSchema#integer>) = true'
    )
    parenthesised = CompareExpr(
        op="=", left=FunctionCall("BOUND", (TermExpr(Variable("x")),)), right=inner
    )
    assert (
        parenthesised.render()
        == 'BOUND(?x) = (?x > "1"^^<http://www.w3.org/2001/XMLSchema#integer>)'
    )


def test_compare_expr_brackets_in_operand() -> None:
    """``IN`` is itself one of [131]'s relational alternatives (SPARQL §19),
    not a ``PrimaryExpression`` — an :class:`InExpr` operand must bracket:
    ``?x IN (…) = true`` is ungrammatical, ``(?x IN (…)) = true`` parses."""
    inner = InExpr(
        expr=TermExpr(Variable("x")),
        values=(Literal("a"), Literal("b")),
    )
    expr = CompareExpr(op="=", left=inner, right=TermExpr(Literal(True)))
    assert expr.render() == '(?x IN ("a", "b")) = true'


def test_function_call_renders_contains() -> None:
    expr = FunctionCall(
        "CONTAINS",
        (
            TermExpr(Variable("name")),
            TermExpr(Literal("Ali")),
        ),
    )
    assert expr.render() == 'CONTAINS(?name, "Ali")'


def test_in_expr_renders_value_list() -> None:
    expr = InExpr(
        expr=TermExpr(Variable("name")),
        values=(Literal("A"), Literal("B")),
    )
    assert expr.render() == '?name IN ("A", "B")'


def test_and_expr_renders_conjunction() -> None:
    expr = AndExpr(
        children=(
            CompareExpr(
                op=">",
                left=TermExpr(Variable("age")),
                right=TermExpr(Literal("25")),
            ),
            FunctionCall(
                "CONTAINS",
                (
                    TermExpr(Variable("name")),
                    TermExpr(Literal("Ali")),
                ),
            ),
        )
    )
    assert expr.render() == '?age > "25" && CONTAINS(?name, "Ali")'


def test_combinator_single_child_renders_lone_child() -> None:
    child = CompareExpr(
        op="=", left=TermExpr(Variable("x")), right=TermExpr(Literal("1"))
    )
    assert AndExpr(children=(child,)).render() == '?x = "1"'
    assert OrExpr(children=(child,)).render() == '?x = "1"'


def test_or_expr_renders_disjunction() -> None:
    age = TermExpr(Variable("age"))
    expr = OrExpr(
        children=(
            CompareExpr(op="<", left=age, right=TermExpr(Literal("20"))),
            CompareExpr(op=">", left=age, right=TermExpr(Literal("60"))),
        )
    )
    assert expr.render() == '?age < "20" || ?age > "60"'


def test_or_expr_wraps_and_children_in_parens() -> None:
    left_and = AndExpr(
        children=(
            CompareExpr(
                op=">", left=TermExpr(Variable("age")), right=TermExpr(Literal("25"))
            ),
            CompareExpr(
                op="<", left=TermExpr(Variable("score")), right=TermExpr(Literal("100"))
            ),
        )
    )
    right = CompareExpr(
        op="=",
        left=TermExpr(Variable("name")),
        right=TermExpr(Literal("Alice")),
    )
    expr = OrExpr(children=(left_and, right))
    assert expr.render() == '(?age > "25" && ?score < "100") || ?name = "Alice"'


def test_and_expr_wraps_or_children_in_parens() -> None:
    left = CompareExpr(
        op="=",
        left=TermExpr(Variable("active")),
        right=TermExpr(Literal("true")),
    )
    right_or = OrExpr(
        children=(
            CompareExpr(
                op="=",
                left=TermExpr(Variable("name")),
                right=TermExpr(Literal("Alice")),
            ),
            CompareExpr(
                op="=", left=TermExpr(Variable("name")), right=TermExpr(Literal("Bob"))
            ),
        )
    )
    expr = AndExpr(children=(left, right_or))
    assert expr.render() == '?active = "true" && (?name = "Alice" || ?name = "Bob")'


def test_not_expr_negates_in_expr() -> None:
    expr = NotExpr(
        child=InExpr(
            expr=TermExpr(Variable("name")),
            values=(Literal("A"), Literal("B")),
        )
    )
    assert expr.render() == '!(?name IN ("A", "B"))'


EXISTS_SINGLE_TRIPLE_SPARQL = """EXISTS {
  ?iri a <http://example.org/Thing> .
}"""


def test_exists_expr_renders_group_pattern() -> None:
    iri = Variable("iri")
    pattern = GroupPattern(
        children=(
            TriplePattern(
                subject=iri,
                predicate=PredicatePath(RDF_TYPE),
                object=EX + "Thing",
            ),
        )
    )
    assert ExistsExpr(pattern=pattern).render() == EXISTS_SINGLE_TRIPLE_SPARQL


def test_exists_expr_renders_empty_group() -> None:
    """An empty ``GroupPattern`` inside ``EXISTS`` renders as ``EXISTS {}``."""
    assert ExistsExpr(pattern=GroupPattern(children=())).render() == "EXISTS {}"
