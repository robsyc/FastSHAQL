"""Shared fixtures across test tiers — graphs and registries.

Case inputs are co-located under ``tests/fixtures/cases/<set>/`` and parsed once
via path-keyed cached factories in ``support.cases`` (ADR-0021). Each
fixture below is a thin delegate so the call-site names are preserved; the
factories give singleton-per-set semantics regardless of fixture scope. Stores
stay function-scoped (mutable per-test state). A delegate is added per case set
only when unit/integration tests consume it directly; e2e-only sets (e.g.
``paths``, ``pagination``) are reached via ``CaseSet`` and need no delegate.
"""

from pathlib import Path

import pytest
import rdflib.plugins.sparql
from rdflib import Graph

from fastshaql.core.registry import ShapeRegistry
from support.cases import data_graph_for, graph_for, registry_for

# Prevent rdflib from HTTP-dereferencing ``FROM <iri>`` graphs absent from the
# local ``Dataset`` during in-process query evaluation. Without this, an absent
# named graph triggers a blocking network fetch (4 attempts per graph, even for
# ``urn:`` schemes). The ``InMemoryStore`` path is the only one that calls
# ``graph.query()`` locally; remote stores ship the string to an endpoint where
# this flag is irrelevant. See ADR-0011.
rdflib.plugins.sparql.SPARQL_LOAD_GRAPHS = False  # ty: ignore[invalid-assignment]


@pytest.fixture
def minimal_shapes_graph() -> Graph:
    return graph_for("minimal")


@pytest.fixture
def minimal_registry() -> ShapeRegistry:
    return registry_for("minimal")


@pytest.fixture
def minimal_data_graph() -> Graph:
    return data_graph_for("minimal")


@pytest.fixture
def minimal_schema():
    from fastshaql.executable import build_executable_schema

    return build_executable_schema(registry_for("minimal"))


@pytest.fixture
def minimal_store():
    from fastshaql.core.execution.store import InMemoryStore

    return InMemoryStore(data_graph_for("minimal"))


@pytest.fixture
def cardinality_shapes_graph() -> Graph:
    return graph_for("cardinality")


@pytest.fixture
def cardinality_registry() -> ShapeRegistry:
    return registry_for("cardinality")


@pytest.fixture
def visibility_shapes_graph() -> Graph:
    return graph_for("visibility")


@pytest.fixture
def visibility_registry() -> ShapeRegistry:
    return registry_for("visibility")


@pytest.fixture
def relationship_shapes_graph() -> Graph:
    return graph_for("relationships")


@pytest.fixture
def relationship_registry() -> ShapeRegistry:
    return registry_for("relationships")


@pytest.fixture
def relationship_data_graph() -> Graph:
    return data_graph_for("relationships")


@pytest.fixture
def filters_data_graph() -> Graph:
    return data_graph_for("filters")


@pytest.fixture
def filters_shapes_graph() -> Graph:
    return graph_for("filters")


@pytest.fixture
def filters_registry() -> ShapeRegistry:
    return registry_for("filters")


@pytest.fixture
def filter_person_shape(filters_registry: ShapeRegistry):
    return filters_registry.by_type_name["Person"]


@pytest.fixture
def enums_registry() -> ShapeRegistry:
    return registry_for("enums")


@pytest.fixture
def person_shape(relationship_registry: ShapeRegistry):
    return relationship_registry.by_type_name["Person"]


@pytest.fixture
def cardinality_thing_shape(cardinality_registry: ShapeRegistry):
    return cardinality_registry.by_type_name["Thing"]


@pytest.fixture
def inheritance_registry() -> ShapeRegistry:
    return registry_for("inheritance")


# ---------------------------------------------------------------------------
# Tier auto-marking — stamp the marker from the test's directory.
# See CONTRIBUTING.md "Tiers". Tiers are defined by directory; this keeps the
# marker in sync with location so `-m unit`/`-m integration`/`-m e2e` always work
# and per-test `@pytest.mark.<tier>` decoration can never drift.
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    tests_root = Path(__file__).resolve().parent
    tier_by_dir = {
        "unit": "unit",
        "integration": "integration",
        "e2e": "e2e",
        "evaluation": "evaluation",
        "adapters": "adapter",
    }
    for item in items:
        try:
            rel = Path(item.path).resolve().relative_to(tests_root)
        except ValueError:
            continue
        # Tier dirs live under tests/tiers/<tier>/; stamp the marker from parts[1].
        if (
            len(rel.parts) >= 2
            and rel.parts[0] == "tiers"
            and rel.parts[1] in tier_by_dir
        ):
            item.add_marker(getattr(pytest.mark, tier_by_dir[rel.parts[1]]))
