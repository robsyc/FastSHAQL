"""Flat vs paginated WHERE clause assembly — ``core/translation/where_assembly.py`` (ADR-0010).

Unit tier: ``assemble_where`` routing of pattern bags into a flat ``WHERE``
versus a paginated inner sub-SELECT.

Order: flat ordering → paginated inner sub-SELECT.
"""

from __future__ import annotations

from rdflib import Literal, URIRef, Variable
from rdflib.namespace import RDF

from fastshaql.core.sparql import (
    CompareExpr,
    FilterPattern,
    PredicatePath,
    SelectQuery,
    TermExpr,
    TriplePattern,
)
from fastshaql.core.translation.where_assembly import WhereParts, assemble_where

EX = "http://example.org/"


# --- WHERE assembly ---


def test_assemble_where_flat_order() -> None:
    entity = TriplePattern(
        Variable("iri"), PredicatePath(RDF.type), Literal(EX + "Person")
    )
    selection = TriplePattern(
        Variable("iri"), PredicatePath(URIRef(EX + "name")), Variable("name")
    )
    promoted = TriplePattern(
        Variable("iri"), PredicatePath(URIRef(EX + "age")), Variable("age")
    )
    filters = FilterPattern(
        CompareExpr("=", TermExpr(Variable("name")), TermExpr(Literal("Alice")))
    )
    where = assemble_where(
        WhereParts(
            entity=(entity,),
            selection=(selection,),
            promoted=(promoted,),
            filters=(filters,),
        ),
        subject=Variable("iri"),
        paginate=False,
        limit=None,
        offset=None,
    )
    assert where.children == (entity, selection, promoted, filters)


def test_assemble_where_paginated_inner_subselect() -> None:
    entity = TriplePattern(
        Variable("iri"), PredicatePath(RDF.type), Literal(EX + "Person")
    )
    selection = TriplePattern(
        Variable("iri"), PredicatePath(URIRef(EX + "name")), Variable("name")
    )
    promoted = TriplePattern(
        Variable("iri"), PredicatePath(URIRef(EX + "age")), Variable("age")
    )
    filters = FilterPattern(
        CompareExpr("=", TermExpr(Variable("name")), TermExpr(Literal("Alice")))
    )
    where = assemble_where(
        WhereParts(
            entity=(entity,),
            selection=(selection,),
            promoted=(promoted,),
            filters=(filters,),
        ),
        subject=Variable("iri"),
        paginate=True,
        limit=10,
        offset=0,
    )
    assert len(where.children) == 2
    inner, outer_selection = where.children
    assert isinstance(inner, SelectQuery)
    assert inner.as_subquery is True
    assert inner.distinct is True
    assert inner.limit == 10
    assert inner.offset == 0
    assert inner.where.children == (entity, promoted, filters)
    assert outer_selection is selection
