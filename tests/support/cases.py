"""Hand-authored case-set paths, the canonical case registry, and cached inputs.

Single source of truth for case locations and the parsed ``ShapeRegistry`` /
``Graph`` objects derived from them. ``CaseSet`` points at one co-located
directory per set (``tests/fixtures/cases/<set>/``): inputs (``shapes.ttl`` /
``data.ttl``) live at the set root and e2e cases live as subdirectories.

The ``*_for`` factories are ``lru_cache``-d so a case set's immutable inputs
are parsed exactly once per session, whether reached from a pytest fixture
(``tests/conftest.py``) or a runner (``support/runners.py``). No test mutates a
case-provided registry or graph (audited), so singleton sharing is safe.
Generated-data scenarios live under ``tests/fixtures/scenarios/`` and are
declared in ``support.scenarios`` — see ADR-0021 for the tier model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from rdflib import Dataset, Graph

from fastshaql.core.kernel.context import QueryContext
from fastshaql.core.kernel.io import load_shapes as _load_shapes
from fastshaql.core.parser import parse_shapes

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry

CASES_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "cases"

# Canonical case registry — single source of truth for hand-authored sets (ADR-0021).
CASES: dict[str, tuple[str, ...]] = {
    "minimal": ("smoke",),
    "cardinality": ("full",),
    "relationships": ("nested", "recursive", "full"),
    "filters": (
        "scalar_eq",
        "scalar_gt",
        "or_combinator",
        "or_relationship",
        "not_relationship",
        "relationship_filter",
        "relationship_selected_and_filtered",
        "scalar_and_relationship",
        "lang_filter",
    ),
    "enums": (
        "literal_select",
        "iri_select",
        "filter_eq_neq",
        "filter_in_not_in",
        "iri_filter_eq_neq",
        "iri_filter_in_not_in",
        "iri_filter_prefix",
        "integer_literal_enum",
        "integer_literal_filter",
        "mangled_enum_select",
        "relationship_overlay",
    ),
    "paths": (
        "inverse",
        "sequence",
        "alternative",
        "composite_scalar",
        "transitive",
    ),
    "pagination": (
        "row_vs_entity",
        "offset",
        "limit_zero",
        "offset_past_end",
        "filter_scalar",
        "relationship_filter",
        "relationship_filter_selected",
        "filter_promoted_scalar",
    ),
    "visibility": ("public_select", "protected_reachable", "public_class_closure"),
    "derived": (
        "select_derived",
        "optional_derived",
        "filter_derived",
        "filter_exists_boolean",
        "label_concat",
        "label_replace",
        "filter_label",
    ),
    "derived_clinical": (
        "most_specific_class",
        "applicable_protocol_titles",
        "filter_most_specific_class",
        "optional_summary_note",
        "paginated_derived_filter",
        "protocol_status",
        "select_arm_derived_relationship",
    ),
    "derived_relationships": (
        "derived_relationship_nested_selection",
        "shnode_anchored_derived_target",
        "derived_relationship_inside_filter_exists",
        "pagination_derived_relationship",
        "filter_shape_conjunction",
        "filter_shape_class_union",
        "filter_shape_numeric_range",
        "filter_shape_mincount_one",
        "path_values_focus_node",
        "derived_chain_three_hops",
        "constant_iri_relationship",
        "list_expression_relationship",
    ),
    "node_expr": (
        "path_values_scalar",
        "path_values_inverse",
        "derived_lang_tags",
        "if_exists_constant_branches",
        "if_branches_value_sets",
        "exists_boolean_scalar",
        "constants_and_list_expression",
        "derived_scalar_null_when_path_misses",
        "multiple_derived_fields_one_shape",
        "derived_enum_nested_if",
        "default_value_precedence",
        "default_value_filter",
        "default_value_filter_asserted",
        "default_value_filter_derived",
        "default_value_lang",
        "default_value_relationship",
    ),
    "inheritance": (
        "inherited_scalar",
        "inherited_relationship",
        "inherited_enum",
        "inherited_combined_filter",
        "override_own_beats_inherited",
    ),
    "derived_targets": (
        "instances_of_subclass_closure",
        "path_values_composite_subclass",
        "union_instances_dedup",
        "change_subclasses",
        "branch_prefix_pattern",
        "constant_node_target",
        "filter_shape_target",
        "select_target",
        "implicit_class_target_where",
        "instances_where_limit",
    ),
    "named_graphs": (
        "scope_single",
        "merge_multiple",
        "from_replaces_default",
        "no_iris",
    ),
    "language": ("no_chain", "en", "en_nl", "en_any", "en_us"),
}


@dataclass(frozen=True)
class E2eCase:
    """Loaded case files under a case set."""

    name: str
    query: str
    expected_json: object | None
    expected_sparql: str | None
    query_context: QueryContext | None = None


class CaseSource(Protocol):
    """Minimal read interface ``run_case`` / ``run_case_on_store`` need.

    Both ``CaseSet`` (hand-authored) and ``support.scenarios.Scenario``
    (generated) satisfy this structurally.
    """

    name: str

    def shapes_path(self) -> Path: ...

    def load_case(self, case: str) -> E2eCase: ...


def load_case_from(directory: Path, case: str) -> E2eCase:
    """Read case files (query/expected/sparql/config) from *directory*.

    Shared by ``CaseSet`` and ``Scenario`` so there is exactly one case-loading path.
    """
    query_path = directory / "query.graphql"
    expected_json_path = directory / "expected.json"
    expected_sparql_path = directory / "expected.sparql"
    config_path = directory / "config.json"

    expected_json: object | None = None
    if expected_json_path.exists():
        expected_json = json.loads(expected_json_path.read_text(encoding="utf-8"))

    expected_sparql: str | None = None
    if expected_sparql_path.exists():
        expected_sparql = expected_sparql_path.read_text(encoding="utf-8").strip()

    query_context: QueryContext | None = None
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        query_context = QueryContext(
            lang_tags=tuple(config.get("lang_tags", ())),
            read_graphs=tuple(config.get("read_graphs", ())),
        )

    return E2eCase(
        name=case,
        query=query_path.read_text(encoding="utf-8"),
        expected_json=expected_json,
        expected_sparql=expected_sparql,
        query_context=query_context,
    )


class CaseSet:
    """One co-located hand-authored case directory (ADR-0021): RDF inputs + e2e cases."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.root = CASES_ROOT / name

    def shapes_path(self) -> Path:
        return self.root / "shapes.ttl"

    def data_path(self) -> Path:
        # Prefer ``data.trig`` (named graphs) when present; fall back to ``data.ttl``
        # (default-graph-only). rdflib's ``Dataset.parse`` infers the format from the
        # extension, routing TriG correctly: bare triples → the default context,
        # ``GRAPH <iri> { … }`` blocks → named graphs. See ADR-0011.
        trig = self.root / "data.trig"
        return trig if trig.exists() else self.root / "data.ttl"

    def case_dir(self, case: str) -> Path:
        return self.root / case

    def load_shapes(self) -> Graph:
        return _load_shapes(self.shapes_path())

    def load_data(self) -> Dataset:
        # Read-only: parse committed data.trig/data.ttl if present, else an empty dataset.
        # (Scenario data is generated via ``support.scenarios`` — never written here.)
        # ``default_union=True`` makes the bare no-``FROM`` default graph the union of
        # all graphs — matching GraphDB (the parity target) and the majority of stores.
        # Explicit ``FROM`` isolates regardless (ADR-0011). See
        # ``test_named_graph_isolation.py`` for the truth-table evidence.
        ds = Dataset(default_union=True)
        path = self.data_path()
        if path.exists():
            ds.parse(path)
        return ds

    def load_case(self, case: str) -> E2eCase:
        return load_case_from(self.case_dir(case), case)


@cache
def _graph_for_path(shapes_path: Path) -> Graph:
    return _load_shapes(shapes_path)


@cache
def registry_for_path(shapes_path: Path) -> ShapeRegistry:
    """Parsed ``ShapeRegistry`` for a shapes file (cached by path).

    Path-keyed so it serves both ``CaseSet`` (under ``cases/``) and
    ``support.scenarios.Scenario`` (under ``scenarios/``) — name-keyed lookups
    would collide or miss the scenarios root.
    """
    return parse_shapes(_graph_for_path(shapes_path))


# Cases-only convenience wrappers for pytest delegates in ``tests/conftest.py``.
def graph_for(set_name: str) -> Graph:
    """Parsed shapes graph for a hand-authored case set (cached via path)."""
    return _graph_for_path(CaseSet(set_name).shapes_path())


def registry_for(set_name: str) -> ShapeRegistry:
    """Parsed ``ShapeRegistry`` for a hand-authored case set (cached via path)."""
    return registry_for_path(CaseSet(set_name).shapes_path())


@cache
def data_graph_for(set_name: str) -> Dataset:
    """Parsed data dataset for a hand-authored case set (cached singleton)."""
    return CaseSet(set_name).load_data()
