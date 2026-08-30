# Tests

The single reference for the test suite: layout, the tier model, fixtures, the evaluation harness, and coverage. For the *design rationale* behind the tier model, see [ADR-0021](../docs/adr/0021-declarative-fixture-testing.md).

The suite is declarative where it can be: inputs are `.ttl` / `.graphql` / `.json` artifacts, not imperative setup.

## Run

```bash
just test            # default suite (excludes evaluation)
just eval            # GraphDB CE parity + perf (requires Docker)
uv run pytest -m e2e # one tier only (unit | integration | e2e | adapter | evaluation)
just test-cov        # with coverage
```

Default `pytest` excludes `-m evaluation` (`pyproject.toml` `addopts`); `just eval` overrides it. Tier markers are **auto-stamped from the test's directory** by a `pytest_collection_modifyitems` hook in `conftest.py` — no per-test `@pytest.mark.<tier>` is needed or wanted.

## Layout

```
tests/
├── conftest.py          # tier auto-marking + shared per-set fixtures (delegates to support.cases)
|
├── tiers/               # test code, grouped by tier
│   ├── unit/            # one pipeline stage; inline/programmatic inputs
│   │                    # (unit/stores/ covers the shipped store packages)
│   ├── integration/     # ≥2 stages on real case inputs
│   ├── e2e/             # full pipeline → golden files
│   ├── adapters/        # FastAPI/Django HTTP shims (optional-dep gated)
│   └── evaluation/      # full pipeline against a real triple store (GraphDB CE)
|
├── fixtures/
│   ├── cases/           # hand-authored: shapes.ttl + data.ttl|data.trig + e2e cases (committed)
│   └── scenarios/       # generated: shapes.ttl + anchor cases; data.ttl gitignored
|
└── support/             # shared test infrastructure (imported as `support.X`)
    │                    # (everything at this root is shared across ≥2 tiers)
    ├── cases.py         # CaseSet + CASES registry + CaseSource Protocol + path-keyed caches
    ├── scenarios.py     # Scenario / Scale / SCENARIOS (generated-data)
    ├── runners.py       # run_case / run_case_on_store / translate_case / RecordingStore
    ├── builders.py      # Shape-IR construction factories (unit + integration)
    ├── graphql_utils.py # root_field_node / shape_for_root_field
    ├── goldens.py       # canonicalize — order-independent JSON compare
    ├── converter_helpers.py  # converter unit-test factories
    ├── schema_helpers.py     # schema type-introspection asserts (integration/schema)
    ├── translation.py        # translation_scope factory (unit/translation)
    ├── sparql_goldens.py     # shared SPARQL golden string (filter tests)
    ├── import_guard.py       # no-extras import check (run via `just import-guard`)
    ├── architecture/         # module_graph.py — mermaid DAG for ARCHITECTURE.md
    ├── mutation/             # floor.py — mutation-score floor gate
    └── eval/            # evaluation-only (consumed solely by tiers/evaluation/)
        ├── session.py   # StoreSession Protocol — the store contract
        ├── graphdb.py   # GraphDbSession — the GraphDB adapter
        └── report.py    # EvalReport — JSON sidecar + CI summary renderer
```

Everything at the `support/` root is shared across ≥2 tiers; `support/eval/` is the only evaluation-specific subgroup.

## Tiers

Defined by two axes — *pipeline-stages-composed* × *assertion medium* — auto-marked by directory.

| Tier | Composes | Asserts |
|---|---|---|
| `unit` | one stage; programmatic/inline inputs | inline / programmatic |
| `integration` | ≥2 pipeline stages on real case inputs | produced SPARQL inline, VariableMap |
| `e2e` | full pipeline: GraphQL op → SPARQL → store → JSON | **golden files** (`expected.json` + `expected.sparql`) |
| `evaluation` | full pipeline against a **real** triple store (GraphDB CE) | golden + scale (order-independent) |
| `adapter` | framework adapter HTTP shim (FastAPI/Django) | inline; may reuse a golden case read-only |

## Fixtures: cases vs scenarios

- A **case** (`fixtures/cases/<set>/`) is hand-authored: committed `shapes.ttl` + `data.ttl` (or `data.trig` for named-graph sets — `Dataset.parse` infers the format from the extension) + e2e case subdirs (`query.graphql` + `expected.json` + optional `expected.sparql` / `config.json`). The correctness-e2e unit; validated against `InMemoryStore` (rdflib). Registry: `CASES`.
- A **scenario** (`fixtures/scenarios/<name>/`) is synthetically generated: committed `shapes.ttl` + a correctness anchor (`smoke/`); its data is produced in-memory by a generator in `support.scenarios` (`Scenario.data_at(scale)`). Carries a **scale** axis (a flat `params` map, so each scenario names its own parameters) and a **sweep** — the ordered scale tuple the perf probe runs. Registry: `SCENARIOS`.

Both satisfy the `CaseSource` Protocol, so the same `run_case` / `run_case_on_store` runners serve them. Each registry has its own drift guard (`test_case_registry`, `test_scenario_registry`) that fails if a directory is unregistered or a registered entry has no directory.

> "pytest fixture" is never abbreviated to "fixture" in prose — that overloads the fixture-set meaning above.

## Evaluation tier (real triple store)

`just eval` starts GraphDB CE via [testcontainers](https://testcontainers.com), creates one repository, and reuses the e2e golden cases — swapping `InMemoryStore` for the shipped `HttpxSparqlStore` (`fastshaql.stores.http`, `httpx` extra — test what we ship). Two axes:

- **parity** — real-store JSON == golden, compared order-independently via `support.goldens.canonicalize` (the outer query has no `ORDER BY`, so entity lists and multi-valued fields may permute — ADR-0010, ADR-0022).
- **performance** — per-phase latency (translate / store / convert) and materialised row counts across each scenario's `sweep`; report-only (no thresholds), written to `evaluation-report.json` and rendered into the CI job summary.

The harness consumes the `StoreSession` Protocol (`support/eval/session.py`); `graphdb.py` is the GraphDB adapter. To add a store (e.g. QLever), implement `StoreSession` in a sibling module + a session-scoped fixture — runners and the report are store-agnostic. See [ADR-0022](../docs/adr/0022-evaluation-harness.md).

Requires Docker **and a GraphDB license**. GraphDB 11+ needs a license even for the Free edition — request one at <https://graphdb.ontotext.com/>. Then:

- drop the **verbatim** license file at `tests/tiers/evaluation/graphdb.license` (gitignored; or set `GRAPHDB_LICENSE_FILE`) — don't strip whitespace or reformat it, GraphDB validates the formatting strictly;
- in CI it's the `GRAPHDB_LICENSE` secret (base64 of the binary file; the workflow decodes it to the path); when absent the run skips.

Not PR-gated; nightly in CI ([.github/workflows/nightly.yml](../.github/workflows/nightly.yml)) plus `workflow_dispatch`.

## Coverage

Branch coverage in CI; gate at 100% (`pyproject.toml`). Exclusions follow [CONTRIBUTING — Testing](../CONTRIBUTING.md) — `# pragma: no cover` only for genuinely unreachable guards, each with rationale. The coverage badge is an endpoint JSON regenerated by nightly's `badges` job and pushed to the `badges` branch.

## `demo/` vs `tests/`

`demo/` is an unpublished workspace member combining the quickstart playground with the reference scalable-FastAPI wiring (a playground server over the shipped `httpx`-extra store, and a local load-test). It is **load-bearing for tests**: the adapter tier boots `demo.server` end to end. `tests/` never ships.
