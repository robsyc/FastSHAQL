"""SPARQL property path AST (§9).

See: https://www.w3.org/TR/sparql12-query/#propertypaths

This is the SPARQL emission side. The SHACL input side lives in ``core/ir/shacl_path.py``.
Translation maps between the two at translation time.
"""

from __future__ import annotations

import dataclasses

from rdflib import RDF, URIRef

from .terms import render_term

# Precedence ranks — lower binds looser; parenthesize child when child.rank < parent.rank.
_RANK_ALTERNATIVE = 1
_RANK_SEQUENCE = 2
_RANK_INVERSE = 3
_RANK_MODIFIER = 3
_RANK_PREDICATE = 4


type SparqlPropertyPath = (
    PredicatePath
    | InversePath
    | SequencePath
    | AlternativePath
    | ZeroOrMorePath
    | OneOrMorePath
    | ZeroOrOnePath
)


def _render_path_part(part: SparqlPropertyPath, parent_rank: int) -> str:
    """Render *part*, parenthesizing when its precedence is lower than *parent_rank*."""
    rendered = part.render()
    if part.rank() < parent_rank:
        return f"({rendered})"
    return rendered


def _render_modifier(path: SparqlPropertyPath, symbol: str) -> str:
    """Render a cardinality modifier ``operand{symbol}``, parenthesizing the operand
    unless it is a ``PathPrimary`` (grammar [97], PathElt, constrains the operand to PathPrimary)."""
    return f"{_render_path_part(path, _RANK_PREDICATE)}{symbol}"


@dataclasses.dataclass(frozen=True)
class PredicatePath:
    """Degenerate property path: a single IRI (SPARQL §9)."""

    iri: URIRef
    """The predicate IRI."""

    def rank(self) -> int:
        """Return precedence rank for parenthesization (lower binds looser)."""
        return _RANK_PREDICATE

    def render(self, _indent: int = 0) -> str:
        """Render as ``a`` for ``rdf:type``, else full IRI via :func:`render_term`."""
        if self.iri == RDF.type:
            return "a"
        return render_term(self.iri)


@dataclasses.dataclass(frozen=True)
class InversePath:
    """Inverse property path: ``^`` (SPARQL §9)."""

    path: SparqlPropertyPath
    """The inverted sub-path."""

    def rank(self) -> int:
        """Return precedence rank for parenthesization (lower binds looser)."""
        return _RANK_INVERSE

    def render(self, _indent: int = 0) -> str:
        # `^` operand must be a PathPrimary (SPARQL [98]); only a bare predicate
        # qualifies, so parenthesize every composite child (rank < _RANK_PREDICATE).
        inner = _render_path_part(self.path, _RANK_PREDICATE)
        return f"^{inner}"


@dataclasses.dataclass(frozen=True)
class SequencePath:
    """Sequence property path: ``/`` (SPARQL §9)."""

    elements: tuple[SparqlPropertyPath, ...]
    """Ordered path elements joined by ``/``."""

    def rank(self) -> int:
        """Return precedence rank for parenthesization (lower binds looser)."""
        return _RANK_SEQUENCE

    def render(self, _indent: int = 0) -> str:
        return "/".join(
            _render_path_part(element, self.rank()) for element in self.elements
        )


@dataclasses.dataclass(frozen=True)
class AlternativePath:
    """Alternative property path: ``|`` (SPARQL §9)."""

    alternatives: tuple[SparqlPropertyPath, ...]
    """Branch paths joined by ``|``."""

    def rank(self) -> int:
        """Return precedence rank for parenthesization (lower binds looser)."""
        return _RANK_ALTERNATIVE

    def render(self, _indent: int = 0) -> str:
        return "|".join(
            _render_path_part(alternative, self.rank())
            for alternative in self.alternatives
        )


@dataclasses.dataclass(frozen=True)
class ZeroOrMorePath:
    """Cardinality modifier ``*`` (SPARQL §9 / grammar [97]). Operand must be PathPrimary."""

    path: SparqlPropertyPath
    """The operand path."""

    def rank(self) -> int:
        """Return precedence rank for parenthesization (lower binds looser)."""
        return _RANK_MODIFIER

    def render(self, _indent: int = 0) -> str:
        return _render_modifier(self.path, "*")


@dataclasses.dataclass(frozen=True)
class OneOrMorePath:
    """Cardinality modifier ``+`` (SPARQL §9 / grammar [97]). Operand must be PathPrimary."""

    path: SparqlPropertyPath
    """The operand path."""

    def rank(self) -> int:
        """Return precedence rank for parenthesization (lower binds looser)."""
        return _RANK_MODIFIER

    def render(self, _indent: int = 0) -> str:
        return _render_modifier(self.path, "+")


@dataclasses.dataclass(frozen=True)
class ZeroOrOnePath:
    """Cardinality modifier ``?`` (SPARQL §9 / grammar [97]). Operand must be PathPrimary."""

    path: SparqlPropertyPath
    """The operand path."""

    def rank(self) -> int:
        """Return precedence rank for parenthesization (lower binds looser)."""
        return _RANK_MODIFIER

    def render(self, _indent: int = 0) -> str:
        return _render_modifier(self.path, "?")
