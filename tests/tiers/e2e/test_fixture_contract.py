"""Fixture metadata contract gate (ADR-0021).

Self-describing fixtures, enforced over every registered case set and
scenario: exactly one described ``graphql:Schema``, ``rdfs:comment`` on every
node shape, ``sh:description`` on every property shape, and — cases only — a
named, described operation plus the required per-case files
(``expected.sparql``, ``config.json``). The loader enforces ``expected.sparql``
and strict ``config.json`` keys independently (``support.cases``).

Order: case sets (parametrized) → scenario shapes (parametrized).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from graphql import parse as gql_parse
from graphql.language.parser import OperationDefinitionNode
from rdflib import RDF, Graph, Namespace
from rdflib.namespace import RDFS

if TYPE_CHECKING:
    from rdflib.term import Node

from fastshaql.core.parser.visibility import GRAPHQL
from support.cases import CASES, CaseSet, graph_for
from support.scenarios import SCENARIOS

SH = Namespace("http://www.w3.org/ns/shacl#")


def _nonblank_literals(graph: Graph, subject: Node, predicate: Node) -> list[str]:
    return [
        str(value) for value in graph.objects(subject, predicate) if str(value).strip()
    ]


def _schema_violations(set_name: str, graph: Graph) -> list[str]:
    violations: list[str] = []
    schemas = list(graph.subjects(RDF.type, GRAPHQL.Schema))
    if len(schemas) != 1:
        return [
            f"{set_name}: expected exactly one graphql:Schema, found {len(schemas)}"
        ]
    if not _nonblank_literals(graph, schemas[0], RDFS.comment):
        violations.append(f"{set_name}: the graphql:Schema carries no rdfs:comment")
    return violations


def _node_shape_iris(graph: Graph) -> list[Node]:
    shape_iris: dict[Node, None] = {}  # ordered set — a shape may carry both types
    for shape_class in (SH.NodeShape, SH.ShapeClass):
        for shape_iri in graph.subjects(RDF.type, shape_class):
            shape_iris.setdefault(shape_iri, None)
    return list(shape_iris)


def _shape_violations(set_name: str, graph: Graph) -> list[str]:
    violations: list[str] = []
    for shape_iri in _node_shape_iris(graph):
        if not _nonblank_literals(graph, shape_iri, RDFS.comment):
            violations.append(
                f"{set_name}: node shape {shape_iri} carries no rdfs:comment"
            )
        violations.extend(
            f"{set_name}: property shape {prop} (on {shape_iri}) carries no sh:description"
            for prop in graph.objects(shape_iri, SH.property)
            if not _nonblank_literals(graph, prop, SH.description)
        )
    return violations


def _set_violations(set_name: str, graph: Graph) -> list[str]:
    return _schema_violations(set_name, graph) + _shape_violations(set_name, graph)


def _case_violations(set_name: str) -> list[str]:
    violations: list[str] = []
    case_set = CaseSet(set_name)
    for case in CASES[set_name]:
        where = f"{set_name}/{case}"
        if not (case_set.case_dir(case) / "expected.sparql").exists():
            violations.append(f"{where}: missing expected.sparql")
        if not (case_set.case_dir(case) / "config.json").exists():
            violations.append(f"{where}: missing config.json ({{}} when empty)")
        loaded = case_set.load_case(case)
        op = gql_parse(loaded.query).definitions[0]
        if not isinstance(op, OperationDefinitionNode):
            violations.append(f"{where}: expected a query operation definition")
        elif op.name is None:
            violations.append(f"{where}: the operation carries no name")
        if not (loaded.description or "").strip():
            violations.append(f"{where}: the operation carries no description")
    return violations


@pytest.mark.parametrize("set_name", sorted(CASES))
def test_case_set_meets_metadata_contract(set_name: str) -> None:
    """All violations for one set collected into a single report — the
    per-set worklist for the fixture-metadata wave."""
    failures = _set_violations(set_name, graph_for(set_name))
    failures.extend(_case_violations(set_name))
    assert not failures, f"fixture metadata contract violations: {failures}"


@pytest.mark.parametrize("scenario_name", sorted(SCENARIOS))
def test_scenario_shapes_meet_metadata_contract(scenario_name: str) -> None:
    """Scenarios carry the shape-level rules only — their smoke anchors are
    not cases (ADR-0021)."""
    graph = Graph().parse(SCENARIOS[scenario_name].shapes_path(), format="turtle")
    failures = _set_violations(scenario_name, graph)
    assert not failures, f"fixture metadata contract violations: {failures}"
