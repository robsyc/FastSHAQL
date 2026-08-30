"""Filter-shape IR — the lowerable conjunct set of ``shnex:filterShape``
(ADR-0015).

A dedicated light module, not ``PropertyShapeIR`` reuse: a filter shape is a
conjunction of boolean single-value-node constraints (``sh:hasValue``,
``sh:class`` (IRI or IRI list — union), ``sh:rootClass``, ``sh:datatype``,
``sh:pattern``) plus numeric ranges, ``sh:minCount 1``, and nested
``sh:property`` — the lowerable subset of SHACL
constraints. Unknown constraints are rejected loudly at parse time, naming the
predicate; ``sh:maxCount`` and ``sh:minCount k>1`` are rejected as an
implementation narrowing (the spec permits any well-formed shape).

This module is inert data only — parsing lives in
``core/parser/node_expr/filter_shape.py`` and emission in
``core/translation/filter_shape.py``.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING
from typing import Literal as TypingLiteral

if TYPE_CHECKING:
    from rdflib import Literal, URIRef

    from .shacl_path import ShaclPropertyPath


@dataclasses.dataclass(frozen=True)
class FilterHasValue:
    """``sh:hasValue`` — the node equals a fixed term."""

    value: URIRef | Literal
    """URIRef or Literal (blank nodes cannot be matched in a filter)."""


@dataclasses.dataclass(frozen=True)
class FilterClass:
    """``sh:class`` — the node is a SHACL instance of any listed class.

    One conjunct per ``sh:class`` triple: the value is an IRI or an IRI
    SHACL list — union within one value, conjunction across repetitions
    (Core §7.1.1). An empty list matches nothing (the formal text's
    "instance of any of the classes" over an empty set).
    """

    classes: tuple[URIRef, ...]


@dataclasses.dataclass(frozen=True)
class FilterRootClass:
    """``sh:rootClass`` — the node *is* the root or a transitive subclass of
    it (Core §7.9.4): ``?v rdfs:subClassOf* root``. Same IRI-or-list syntax
    and union/conjunction rules as :class:`FilterClass`."""

    roots: tuple[URIRef, ...]


@dataclasses.dataclass(frozen=True)
class FilterDatatype:
    """``sh:datatype`` — the node is a literal of the datatype."""

    datatype: URIRef


FilterCompareOp = TypingLiteral[">", "<", ">=", "<="]
"""Numeric comparison operator a range bound lowers to (see the parser's
constraint table). A subset of :data:`ComparisonOp` — equality comes from
``sh:hasValue``, never a range bound."""


@dataclasses.dataclass(frozen=True)
class FilterCompare:
    """A numeric range bound — ``sh:minInclusive`` and friends.

    One conjunct per bound; the SHACL predicate determines the operator
    (see the parser's constraint table).
    """

    op: FilterCompareOp
    """SPARQL comparison operator: ``>=``, ``<=``, ``>``, or ``<``."""

    value: Literal
    """The numeric bound."""


@dataclasses.dataclass(frozen=True)
class FilterRegex:
    """``sh:pattern`` — the node's string form matches the regex (Core §7.4.3).

    The spec matches "the string representation as defined by the SPARQL
    str function" — IRIs included.
    """

    pattern: Literal
    """The regex (``xsd:string`` literal, SPARQL REGEX syntax)."""

    flags: Literal | None = None
    """Optional REGEX flags (SPARQL 1.2 §17.4.3.4, e.g. ``"i"``)."""


@dataclasses.dataclass(frozen=True)
class FilterMinCountOne:
    """``sh:minCount 1`` — the path has at least one value (nested only).

    Satisfied by the mandatory path triple itself; the translator skips it.
    """


@dataclasses.dataclass(frozen=True)
class FilterProperty:
    """``sh:property`` — conjunct applied to the path's values."""

    path: ShaclPropertyPath
    nested: FilterShapeIR


@dataclasses.dataclass(frozen=True)
class FilterShapeIR:
    """Conjunction of filter conjuncts (closed sum; ADR-0015)."""

    conjuncts: tuple[FilterConstraintIR, ...]


type FilterConstraintIR = (
    FilterHasValue
    | FilterClass
    | FilterRootClass
    | FilterDatatype
    | FilterRegex
    | FilterCompare
    | FilterMinCountOne
    | FilterProperty
)
"""Closed-sum filter conjunct — one arm per lowerable constraint."""
