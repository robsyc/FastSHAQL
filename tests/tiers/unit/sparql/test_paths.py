"""SPARQL property path rendering — ``core/sparql/paths.py``.

Unit tier: precedence-based parenthesization for composite paths.

Order: flat sequence/alternative → child-precedence parenthesization → inverse wrapping.
"""

from __future__ import annotations

from rdflib import RDF, RDFS, URIRef

from fastshaql.core.sparql.paths import (
    AlternativePath,
    InversePath,
    OneOrMorePath,
    PredicatePath,
    SequencePath,
    ZeroOrMorePath,
    ZeroOrOnePath,
)

EX = URIRef("http://example.org/")


def _pred(name: str) -> PredicatePath:
    return PredicatePath(EX + name)


def test_sequence_of_predicates_no_parens() -> None:
    path = SequencePath((_pred("a"), _pred("b"), _pred("c")))
    assert (
        path.render()
        == "<http://example.org/a>/<http://example.org/b>/<http://example.org/c>"
    )


def test_alternative_of_predicates_no_parens() -> None:
    path = AlternativePath((_pred("a"), _pred("b")))
    assert path.render() == "<http://example.org/a>|<http://example.org/b>"


def test_sequence_with_alternative_child_parenthesized() -> None:
    path = SequencePath((_pred("a"), AlternativePath((_pred("b"), _pred("c")))))
    assert (
        path.render()
        == "<http://example.org/a>/(<http://example.org/b>|<http://example.org/c>)"
    )


def test_alternative_with_sequence_child_no_parens() -> None:
    path = AlternativePath((SequencePath((_pred("a"), _pred("b"))), _pred("c")))
    assert (
        path.render()
        == "<http://example.org/a>/<http://example.org/b>|<http://example.org/c>"
    )


def test_inverse_of_alternative_parenthesized() -> None:
    path = InversePath(AlternativePath((_pred("a"), _pred("b"))))
    assert path.render() == "^(<http://example.org/a>|<http://example.org/b>)"


def test_inverse_of_sequence_parenthesized() -> None:
    path = InversePath(SequencePath((_pred("a"), _pred("b"))))
    assert path.render() == "^(<http://example.org/a>/<http://example.org/b>)"


def test_inverse_of_predicate_no_parens() -> None:
    path = InversePath(_pred("a"))
    assert path.render() == "^<http://example.org/a>"


def test_inverse_of_inverse_parenthesized() -> None:
    # `^` operand must be a PathPrimary (SPARQL [98]); a bare `^a` is not one,
    # so the inner inverse must be wrapped. `^^a` is not legal SPARQL.
    path = InversePath(InversePath(_pred("a")))
    assert path.render() == "^(^<http://example.org/a>)"


def test_inverse_in_sequence_no_parens() -> None:
    path = SequencePath((_pred("a"), InversePath(_pred("b"))))
    assert path.render() == "<http://example.org/a>/^<http://example.org/b>"


def test_inverse_in_alternative_no_parens() -> None:
    path = AlternativePath((InversePath(_pred("a")), _pred("b")))
    assert path.render() == "^<http://example.org/a>|<http://example.org/b>"


# --- Cardinality modifiers (* + ?) — grammar [97]: operand must be PathPrimary ---


def test_zero_or_more_of_predicate_no_parens() -> None:
    assert ZeroOrMorePath(_pred("p")).render() == "<http://example.org/p>*"


def test_one_or_more_of_predicate_no_parens() -> None:
    assert OneOrMorePath(_pred("p")).render() == "<http://example.org/p>+"


def test_zero_or_one_of_predicate_no_parens() -> None:
    assert ZeroOrOnePath(_pred("p")).render() == "<http://example.org/p>?"


def test_modifier_of_sequence_parenthesized() -> None:
    # A sequence is not PathPrimary (grammar [97]); the modifier operand must wrap.
    path = ZeroOrMorePath(SequencePath((_pred("a"), _pred("b"))))
    assert path.render() == "(<http://example.org/a>/<http://example.org/b>)*"


def test_modifier_of_inverse_parenthesized() -> None:
    # `^p` is not PathPrimary; the modifier operand must wrap.
    path = OneOrMorePath(InversePath(_pred("p")))
    assert path.render() == "(^<http://example.org/p>)+"


def test_modifier_of_modifier_parenthesized() -> None:
    # A modifier result is not PathPrimary; a nested modifier must wrap (avoids `p**`).
    path = ZeroOrMorePath(OneOrMorePath(_pred("p")))
    assert path.render() == "(<http://example.org/p>+)*"


def test_modifier_in_sequence_no_parens() -> None:
    # `*` binds tighter than `/`; no parens needed.
    path = SequencePath((_pred("a"), ZeroOrMorePath(_pred("b"))))
    assert path.render() == "<http://example.org/a>/<http://example.org/b>*"


def test_modifier_in_alternative_no_parens() -> None:
    path = AlternativePath((ZeroOrOnePath(_pred("a")), _pred("b")))
    assert path.render() == "<http://example.org/a>?|<http://example.org/b>"


def test_inverse_of_modifier_parenthesized() -> None:
    # InversePath operand must be PathPrimary; a modifier isn't, so it wraps.
    # `^(p*)` is valid and unambiguous (equivalent to `^p*`).
    path = InversePath(ZeroOrMorePath(_pred("p")))
    assert path.render() == "^(<http://example.org/p>*)"


def test_rdf_type_subclassof_canonical() -> None:
    # The motivating composition for sh:class (SHACL §7.1.1 / SPARQL C.4).
    path = SequencePath(
        (PredicatePath(RDF.type), ZeroOrMorePath(PredicatePath(RDFS.subClassOf)))
    )
    assert path.render() == "a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>*"
