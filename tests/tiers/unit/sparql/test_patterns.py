"""Graph pattern and predicate rendering — ``core/sparql/patterns.py``.

Unit tier: ``PredicatePath`` predicate rendering, and ``TriplePattern``,
``GroupPattern``, ``OptionalPattern``, and ``FilterPattern`` render output.

Order: predicate paths → triple/group/optional → FilterPattern → default-indent and edge-shape hardening.
"""

from __future__ import annotations

from rdflib import Literal, URIRef, Variable
from rdflib.namespace import RDF

from fastshaql.core.sparql import (
    CompareExpr,
    ExistsExpr,
    FilterPattern,
    GroupPattern,
    OptionalPattern,
    PredicatePath,
    RawGraphPattern,
    TermExpr,
    TriplePattern,
    ValuesPattern,
)

EX = URIRef("http://example.org/")
RDF_TYPE = RDF.type


# --- Predicate paths ---


def test_predicate_path_renders_full_iri() -> None:
    path = PredicatePath(EX + "label")
    assert path.render() == "<http://example.org/label>"


def test_predicate_path_renders_a_shorthand() -> None:
    path = PredicatePath(RDF_TYPE)
    assert path.render() == "a"


# --- Triple, group, and optional patterns ---


def test_triple_pattern_renders_with_trailing_dot() -> None:
    triple = TriplePattern(
        subject=Variable("iri"),
        predicate=PredicatePath(RDF_TYPE),
        object=EX + "Thing",
    )
    assert triple.render() == "?iri a <http://example.org/Thing> ."


def test_group_pattern_renders_indented_block() -> None:
    iri = Variable("iri")
    label = Variable("label")
    group = GroupPattern(
        children=(
            TriplePattern(
                subject=iri,
                predicate=PredicatePath(RDF_TYPE),
                object=EX + "Thing",
            ),
            TriplePattern(
                subject=iri,
                predicate=PredicatePath(EX + "label"),
                object=label,
            ),
        )
    )
    expected = """{
  ?iri a <http://example.org/Thing> .
  ?iri <http://example.org/label> ?label .
}"""
    assert group.render() == expected


def test_group_pattern_composes_bound_triple_and_optional() -> None:
    iri = Variable("iri")
    label = Variable("label")
    subtitle = Variable("subtitle")
    group = GroupPattern(
        children=(
            TriplePattern(
                subject=iri,
                predicate=PredicatePath(RDF_TYPE),
                object=EX + "Thing",
            ),
            TriplePattern(
                subject=iri,
                predicate=PredicatePath(EX + "label"),
                object=label,
            ),
            OptionalPattern(
                GroupPattern(
                    children=(
                        TriplePattern(
                            subject=iri,
                            predicate=PredicatePath(EX + "subtitle"),
                            object=subtitle,
                        ),
                    )
                )
            ),
        )
    )
    expected = """{
  ?iri a <http://example.org/Thing> .
  ?iri <http://example.org/label> ?label .
  OPTIONAL {
    ?iri <http://example.org/subtitle> ?subtitle .
  }
}"""
    assert group.render() == expected


def test_optional_pattern_renders_single_triple() -> None:
    triple = TriplePattern(
        subject=Variable("iri"),
        predicate=PredicatePath(EX + "subtitle"),
        object=Variable("subtitle"),
    )
    optional = OptionalPattern(GroupPattern(children=(triple,)))
    expected = """OPTIONAL {
  ?iri <http://example.org/subtitle> ?subtitle .
}"""
    assert optional.render() == expected


# --- FilterPattern ---


def test_filter_pattern_renders_expression() -> None:
    expr = CompareExpr(
        op="=",
        left=TermExpr(Variable("age")),
        right=TermExpr(Literal("25")),
    )
    assert FilterPattern(expression=expr).render() == 'FILTER(?age = "25")'


FILTER_IN_GROUP_SPARQL = """{
  ?iri a <http://example.org/Thing> .
  FILTER(?age = "25")
}"""


def test_filter_pattern_renders_indented_in_group() -> None:
    iri = Variable("iri")
    age_filter = FilterPattern(
        expression=CompareExpr(
            op="=",
            left=TermExpr(Variable("age")),
            right=TermExpr(Literal("25")),
        )
    )
    group = GroupPattern(
        children=(
            TriplePattern(
                subject=iri,
                predicate=PredicatePath(RDF_TYPE),
                object=EX + "Thing",
            ),
            age_filter,
        )
    )
    assert group.render() == FILTER_IN_GROUP_SPARQL


# --- FILTER(EXISTS) rendering composition ---


def test_exists_expr_render_inside_filter_pattern() -> None:
    triple = TriplePattern(
        Variable("s"), PredicatePath(RDF.type), Literal(EX + "Company")
    )
    exists = ExistsExpr(GroupPattern((triple,)))
    rendered = FilterPattern(exists).render(indent=1)
    assert rendered.startswith("  FILTER(EXISTS {")
    assert rendered.endswith("})")


# --- Mutation hardening: default indent, empty groups, variable predicates ---


def test_group_pattern_empty_renders_as_empty_string() -> None:
    """An empty group has no braces to render — it contributes nothing."""
    assert GroupPattern(children=()).render() == ""


def test_triple_pattern_renders_variable_predicate() -> None:
    """A variable predicate (cascade ``?p``) renders as a term, not a path."""
    triple = TriplePattern(
        subject=Variable("s"), predicate=Variable("p"), object=Variable("o")
    )
    assert triple.render() == "?s ?p ?o ."


def test_raw_graph_pattern_renders_unindented_by_default() -> None:
    assert RawGraphPattern("?s ex:p ?o .").render() == "?s ex:p ?o ."


def test_raw_graph_pattern_preserves_blank_lines_when_indented() -> None:
    """Only non-blank lines pick up the indent — blank separators stay empty."""
    pattern = RawGraphPattern("?s ex:p ?o .\n\n?s ex:q ?r .")
    assert pattern.render(indent=1) == "  ?s ex:p ?o .\n\n  ?s ex:q ?r ."


def test_values_pattern_renders_unindented_by_default() -> None:
    values = ValuesPattern(var=Variable("v"), terms=(EX + "a",))
    assert values.render() == "VALUES ?v {\n  <http://example.org/a>\n}"


def test_optional_pattern_empty_renders_as_empty_string() -> None:
    """An optional over an empty group contributes nothing — the defensive
    guard mirrors ``GroupPattern``'s empty case."""
    assert OptionalPattern(child=GroupPattern(children=())).render() == ""
