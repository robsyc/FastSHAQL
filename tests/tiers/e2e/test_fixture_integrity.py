"""Fixture-graph integrity for the case sets under ``tests/fixtures/cases/``.

Two guards over the hand-authored RDF artifacts (ADR-0021): every ``*.ttl`` /
``*.trig`` file parses with rdflib, and every case group's data graph conforms
to its own shapes graph — a fixture that violates its declared constraints
would pin e2e goldens against impossible data. Conformance runs pyshacl, a
SHACL 1.1 validator, against a *validation copy* of the shapes graph in which
the SHACL 1.2 constructs pyshacl cannot evaluate are rewritten with
semantically exact 1.1 equivalents (``_validation_copy``); constructs pyshacl
handles natively (``sh:values`` expressions, ``shnex:*`` operands, implicit
``rdfs:Class`` targets) pass through untouched.

Order: parsing → SHACL 1.2 rewrite helper → conformance (parametrized by group).

See: https://www.w3.org/TR/shacl12-core/
"""

from __future__ import annotations

import pytest
from pyshacl import validate
from rdflib import RDF, BNode, Dataset, Graph, Namespace

from support.cases import CASES_ROOT, data_graph_for, graph_for

SH = Namespace("http://www.w3.org/ns/shacl#")
GROUPS = sorted(
    p.name
    for p in CASES_ROOT.iterdir()
    if (p / "shapes.ttl").exists()
    and ((p / "data.ttl").exists() or (p / "data.trig").exists())
)
"""Case groups that declare both a shapes graph and a data graph."""


def test_case_graphs_parse() -> None:
    """Every committed Turtle/TriG artifact parses with rdflib."""
    failures: list[str] = []
    for path in sorted(CASES_ROOT.rglob("*.*")):
        if path.suffix == ".ttl":
            graph: Graph | Dataset = Graph()
        elif path.suffix == ".trig":
            graph = Dataset(default_union=True)
        else:
            continue
        try:
            graph.parse(path)
        except Exception as error:  # noqa: BLE001 - report every parser failure verbatim
            failures.append(f"{path.relative_to(CASES_ROOT)}: {error}")
    assert not failures, f"RDF artifacts failed to parse: {failures}"


def _validation_copy(shapes: Graph) -> Graph:
    """Rewrite SHACL 1.2 constructs pyshacl (1.1) cannot evaluate into exact 1.1 form.
    This should be removed once pyshacl supports SHACL 1.2."""
    out = Graph()
    for s, p, o in shapes:
        if p == SH.targetNode and isinstance(o, BNode):
            continue  # node-expression targets are read-side constructs, not validation targets
        if p == SH.minCount and (
            any(shapes.objects(s, SH.values)) or any(shapes.objects(s, SH.defaultValue))
        ):
            continue  # the sh:values/sh:defaultValue arm is the source of the value (ADR-0015; Core §6.8.2)
        out.add((s, p, o))
    for prop, dt_list in shapes.subject_objects(SH.datatype):
        if not isinstance(dt_list, BNode):
            continue  # (Core §7.1.2) the datatype list form is the sh:or of its members
        out.remove((prop, SH.datatype, dt_list))
        head: object = RDF.nil
        for datatype in reversed(list(shapes.items(dt_list))):
            member, cell = BNode(), BNode()
            out.add((member, SH.datatype, datatype))
            out.add((cell, RDF.first, member))
            out.add((cell, RDF.rest, head))
            head = cell
        out.add((prop, SH["or"], head))
    return out


@pytest.mark.parametrize("group", GROUPS)
def test_case_data_conforms_to_shapes(group: str) -> None:
    """Each case group's data graph conforms to its (rewritten) shapes graph."""
    conforms, results, _ = validate(
        data_graph_for(group), shacl_graph=_validation_copy(graph_for(group))
    )
    focus_nodes = sorted({str(node) for node in results.objects(None, SH.focusNode)})
    assert conforms, f"{group}: data violates its shapes; focus nodes: {focus_nodes}"
