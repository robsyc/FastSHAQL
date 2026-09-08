"""Filter-shape lowering — ``core/translation/filter_shape.py``.

Unit tier: ``translate_filter_shape``'s conjunct arms with their exact
SPARQL expression contracts, and the nested ``sh:property`` scoping rules
(counter-allocated value variables, ``sh:minCount 1`` absorption).

Order: flat conjuncts → nested property conjuncts → class unions.
"""

from __future__ import annotations

from rdflib import RDF, Literal, URIRef, Variable
from rdflib.namespace import XSD

from fastshaql.core.ir.filter_shape import (
    FilterClass,
    FilterDatatype,
    FilterHasValue,
    FilterMinCountOne,
    FilterProperty,
    FilterShapeIR,
)
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.sparql import (
    CompareExpr,
    FilterPattern,
    FunctionCall,
    TermExpr,
    TriplePattern,
)
from fastshaql.core.sparql import (
    PredicatePath as SparqlPredicatePath,
)
from fastshaql.core.translation.filter_shape import translate_filter_shape

EX = URIRef("http://example.org/")

# --- flat conjuncts (exact expression contracts) ---


def test_datatype_conjunct_compares_datatype_function() -> None:
    patterns = translate_filter_shape(
        FilterShapeIR(conjuncts=(FilterDatatype(XSD.date),)), Variable("v")
    )
    assert patterns == [
        FilterPattern(
            CompareExpr(
                "=",
                FunctionCall("datatype", (TermExpr(Variable("v")),)),
                TermExpr(XSD.date),
            )
        )
    ]


def test_has_value_conjunct_is_a_strict_equality() -> None:
    patterns = translate_filter_shape(
        FilterShapeIR(conjuncts=(FilterHasValue(EX + "Alpha"),)), Variable("v")
    )
    assert patterns == [
        FilterPattern(CompareExpr("=", TermExpr(Variable("v")), TermExpr(EX + "Alpha")))
    ]


# --- nested property conjuncts ---


def test_min_count_one_inside_property_is_absorbed_by_the_join() -> None:
    """``sh:minCount 1`` adds no pattern of its own — the mandatory path
    triple already requires at least one value — and must not stop the
    remaining nested conjuncts from lowering."""
    patterns = translate_filter_shape(
        FilterShapeIR(
            conjuncts=(
                FilterProperty(
                    path=PredicatePath(EX + "knows"),
                    nested=FilterShapeIR(
                        conjuncts=(
                            FilterMinCountOne(),
                            FilterClass((EX + "Disease",)),
                        )
                    ),
                ),
            )
        ),
        Variable("v"),
    )
    assert patterns == [
        TriplePattern(
            subject=Variable("v"),
            predicate=SparqlPredicatePath(EX + "knows"),
            object=Variable("v_p0"),
        ),
        TriplePattern(
            subject=Variable("v_p0"),
            predicate=SparqlPredicatePath(RDF.type),
            object=EX + "Disease",
        ),
    ]


def test_each_property_conjunct_gets_a_distinct_value_variable() -> None:
    patterns = translate_filter_shape(
        FilterShapeIR(
            conjuncts=(
                FilterProperty(
                    path=PredicatePath(EX + "a"), nested=FilterShapeIR(conjuncts=())
                ),
                FilterProperty(
                    path=PredicatePath(EX + "b"), nested=FilterShapeIR(conjuncts=())
                ),
            )
        ),
        Variable("v"),
    )
    assert [p.object for p in patterns if isinstance(p, TriplePattern)] == [
        Variable("v_p0"),
        Variable("v_p1"),
    ]


# --- class unions ---


def test_single_class_conjunct_sits_directly_as_path_object() -> None:
    patterns = translate_filter_shape(
        FilterShapeIR(conjuncts=(FilterClass((EX + "Disease",)),)), Variable("v")
    )
    assert patterns == [
        TriplePattern(
            subject=Variable("v"),
            predicate=SparqlPredicatePath(RDF.type),
            object=EX + "Disease",
        )
    ]


def test_empty_class_list_conjunct_matches_nothing() -> None:
    patterns = translate_filter_shape(
        FilterShapeIR(conjuncts=(FilterClass(()),)), Variable("v")
    )
    assert patterns == [FilterPattern(TermExpr(Literal(False)))]


def test_nested_property_conjuncts_advance_counter_through_depth() -> None:
    """A property conjunct inside a property conjunct draws the next
    counter-allocated variable — ``?v_p0`` then ``?v_p0_p1``."""
    patterns = translate_filter_shape(
        FilterShapeIR(
            conjuncts=(
                FilterProperty(
                    path=PredicatePath(EX + "a"),
                    nested=FilterShapeIR(
                        conjuncts=(
                            FilterProperty(
                                path=PredicatePath(EX + "b"),
                                nested=FilterShapeIR(conjuncts=()),
                            ),
                        )
                    ),
                ),
            )
        ),
        Variable("v"),
    )
    assert [p.object for p in patterns if isinstance(p, TriplePattern)] == [
        Variable("v_p0"),
        Variable("v_p0_p1"),
    ]
