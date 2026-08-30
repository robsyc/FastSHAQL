"""SHACL → SPARQL path bridge — ``core/translation/paths.py``.

Unit tier: ``map_shacl_path_to_sparql_path`` across every path form —
predicate, inverse, sequence, alternative, and the double-inverse
parenthesization case.

Order: predicate → inverse → sequence → alternative → inverse-of-inverse.
"""

from __future__ import annotations

import pytest

import fastshaql.core.ir.shacl_path as shacl
from fastshaql.core.sparql.paths import (
    AlternativePath,
    InversePath,
    OneOrMorePath,
    PredicatePath,
    SequencePath,
    ZeroOrMorePath,
    ZeroOrOnePath,
)
from fastshaql.core.translation.paths import map_shacl_path_to_sparql_path
from support.builders import EX


def test_map_predicate_path() -> None:
    result = map_shacl_path_to_sparql_path(shacl.PredicatePath(EX + "label"))
    assert isinstance(result, PredicatePath)
    assert result.iri == EX + "label"


def test_map_inverse_path() -> None:
    result = map_shacl_path_to_sparql_path(
        shacl.InversePath(shacl.PredicatePath(EX + "parent"))
    )
    assert isinstance(result, InversePath)
    assert result.render() == "^<http://example.org/parent>"


def test_map_sequence_path() -> None:
    result = map_shacl_path_to_sparql_path(
        shacl.SequencePath(
            (shacl.PredicatePath(EX + "a"), shacl.PredicatePath(EX + "b"))
        )
    )
    assert isinstance(result, SequencePath)
    assert result.render() == "<http://example.org/a>/<http://example.org/b>"


def test_map_alternative_path() -> None:
    result = map_shacl_path_to_sparql_path(
        shacl.AlternativePath(
            (shacl.PredicatePath(EX + "a"), shacl.PredicatePath(EX + "b"))
        )
    )
    assert isinstance(result, AlternativePath)
    assert result.render() == "<http://example.org/a>|<http://example.org/b>"


def test_map_inverse_of_inverse() -> None:
    result = map_shacl_path_to_sparql_path(
        shacl.InversePath(shacl.InversePath(shacl.PredicatePath(EX + "parent")))
    )
    assert isinstance(result, InversePath)
    assert result.render() == "^(^<http://example.org/parent>)"


# --- Cardinality modifiers ---


@pytest.mark.parametrize(
    ("shacl_node", "sparql_node", "symbol"),
    [
        (shacl.ZeroOrMorePath, ZeroOrMorePath, "*"),
        (shacl.OneOrMorePath, OneOrMorePath, "+"),
        (shacl.ZeroOrOnePath, ZeroOrOnePath, "?"),
    ],
)
def test_map_modifier_path(shacl_node, sparql_node, symbol) -> None:
    result = map_shacl_path_to_sparql_path(
        shacl_node(shacl.PredicatePath(EX + "parent"))
    )
    assert isinstance(result, sparql_node)
    assert isinstance(result.path, PredicatePath)
    assert result.render() == f"<http://example.org/parent>{symbol}"


def test_map_modifier_nested_in_sequence() -> None:
    # The sh:class composition: rdf:type/rdfs:subClassOf*.
    result = map_shacl_path_to_sparql_path(
        shacl.SequencePath(
            (
                shacl.PredicatePath(EX + "type"),
                shacl.ZeroOrMorePath(shacl.PredicatePath(EX + "subClassOf")),
            )
        )
    )
    assert isinstance(result, SequencePath)
    assert (
        result.render() == "<http://example.org/type>/<http://example.org/subClassOf>*"
    )
