"""Translate ``FilterShapeIR`` into SPARQL patterns (ADR-0015).

Each conjunct lowers against the candidate-value variable: equality filters,
type triples, ``datatype()`` checks, ``REGEX(STR(?v), p[, f])`` for
``sh:pattern``, numeric range comparisons, and nested ``sh:property``
conjunction via a path triple plus the nested conjuncts on a fresh value
variable. ``sh:minCount 1`` inside a property conjunct is satisfied by the
mandatory path triple itself (non-optional join).
"""

from __future__ import annotations

from itertools import count
from typing import assert_never

from rdflib import RDF, RDFS, Literal, URIRef, Variable

from fastshaql.core.ir.filter_shape import (
    FilterClass,
    FilterCompare,
    FilterConstraintIR,
    FilterDatatype,
    FilterHasValue,
    FilterMinCountOne,
    FilterProperty,
    FilterRegex,
    FilterRootClass,
    FilterShapeIR,
)
from fastshaql.core.sparql import (
    CompareExpr,
    Expression,
    FilterPattern,
    FunctionCall,
    Pattern,
    PredicatePath,
    TermExpr,
    TriplePattern,
    ValuesPattern,
    ZeroOrMorePath,
)

from .paths import map_shacl_path_to_sparql_path

_SUBCLASS_STAR = ZeroOrMorePath(PredicatePath(RDFS.subClassOf))
"""``rdfs:subClassOf*`` — the ``sh:rootClass`` walk (Core §7.9.4): the value
node is the root (zero-length) or a transitive subclass."""


def translate_filter_shape(ir: FilterShapeIR, value_var: Variable) -> list[Pattern]:
    """Lower every conjunct against *value_var* (conjunction)."""
    counter = count()
    return [
        pattern
        for conjunct in ir.conjuncts
        for pattern in _translate_conjunct(conjunct, value_var, counter)
    ]


def _translate_conjunct(
    conjunct: FilterConstraintIR,
    node_var: Variable,
    counter: count,
) -> list[Pattern]:
    match conjunct:
        case FilterHasValue(value=value):
            return [
                FilterPattern(CompareExpr("=", TermExpr(node_var), TermExpr(value)))
            ]
        case FilterClass(classes=classes):
            return _union_patterns(
                node_var, PredicatePath(RDF.type), classes, counter, "cls"
            )
        case FilterRootClass(roots=roots):
            return _union_patterns(node_var, _SUBCLASS_STAR, roots, counter, "root")
        case FilterDatatype(datatype=datatype):
            return [
                FilterPattern(
                    CompareExpr(
                        "=",
                        FunctionCall("datatype", (TermExpr(node_var),)),
                        TermExpr(datatype),
                    )
                )
            ]
        case FilterRegex(pattern=pattern, flags=flags):
            args: list[Expression] = [
                FunctionCall("STR", (TermExpr(node_var),)),
                TermExpr(pattern),
            ]
            if flags is not None:
                args.append(TermExpr(flags))
            return [FilterPattern(FunctionCall("REGEX", tuple(args)))]
        case FilterCompare(op=op, value=value):
            return [FilterPattern(CompareExpr(op, TermExpr(node_var), TermExpr(value)))]
        case FilterProperty(path=path, nested=nested):
            inner_var = Variable(f"{node_var}_p{next(counter)}")
            patterns: list[Pattern] = [
                TriplePattern(
                    node_var,
                    map_shacl_path_to_sparql_path(path),
                    inner_var,
                )
            ]
            for inner_conjunct in nested.conjuncts:
                if isinstance(inner_conjunct, FilterMinCountOne):
                    continue  # the mandatory path triple already requires >= 1 value
                patterns.extend(_translate_conjunct(inner_conjunct, inner_var, counter))
            return patterns
        case FilterMinCountOne():  # pragma: no cover — parser rejects node-level minCount
            raise TypeError(
                "FilterMinCountOne is only meaningful inside a property conjunct"
            )
        case _ as unreachable:  # pragma: no cover — unreachable: closed union
            assert_never(unreachable)


def _union_patterns(
    node_var: Variable,
    path: PredicatePath | ZeroOrMorePath,
    terms: tuple[URIRef, ...],
    counter: count,
    role: str,
) -> list[Pattern]:
    """One class/rootClass conjunct: a path join over its terms — a single
    term directly, several as a ``VALUES`` union (Core §7.1.1/§7.9.4); an
    empty term list matches nothing."""
    if not terms:
        return [FilterPattern(TermExpr(Literal(False)))]
    if len(terms) == 1:
        return [TriplePattern(node_var, path, terms[0])]
    term_var = Variable(f"{node_var}_{role}{next(counter)}")
    return [
        TriplePattern(node_var, path, term_var),
        ValuesPattern(term_var, terms),
    ]
