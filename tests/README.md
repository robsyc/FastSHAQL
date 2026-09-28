# Tests

The single reference for the test suite: layout, tiers, fixtures, evaluation, and coverage. Design rationale: [ADR-0021](../docs/adr/0021-declarative-fixture-testing.md) (fixture model), [ADR-0022](../docs/adr/0022-evaluation-harness.md) (evaluation). Terms are defined in the glossary ([CONTEXT.md](../CONTEXT.md): Case, Scenario, Fixture, Test tier, Store matrix).

The suite is declarative where it can be: inputs are `.ttl` / `.graphql` / `.json` artifacts, not imperative setup.

## Run

```bash
just test        # default suite (excludes evaluation)
just eval        # store matrix: parity + perf (requires Docker)
just test -m e2e # one tier: unit | integration | e2e | adapter | evaluation
just test-cov    # with coverage
```

Tier markers are auto-stamped from the test's directory (`conftest.py`) — no per-test `@pytest.mark` needed. Default `pytest` excludes evaluation (`pyproject.toml`); `just eval` overrides.

## Layout

```
tests/
├── conftest.py    # tier auto-marking + shared fixtures (delegates to support.cases)
├── tiers/         # test code by tier (see Tiers)
├── fixtures/
│   ├── cases/     # hand-authored, committed
│   └── scenarios/ # generated; data.ttl gitignored
└── support/       # shared infrastructure, imported as `support.X`
    └── eval/      # evaluation-only: store adapters, parity, report
```

Per-file detail lives in the module docstrings. Place a helper at the `support/` root only when two or more tiers use it.

## Tiers

Two axes: pipeline stages composed × what is asserted.

| Tier          | Composes                                                                    | Asserts                                            |
|---------------|-----------------------------------------------------------------------------|----------------------------------------------------|
| `unit`        | one stage; programmatic inputs (`unit/stores/`: the shipped store packages) | inline / programmatic                              |
| `integration` | ≥2 stages on real case inputs                                               | produced SPARQL, VariableMap                       |
| `e2e`         | full pipeline: GraphQL op → SPARQL → store → JSON                           | golden files (`expected.json` + `expected.sparql`) |
| `evaluation`  | full pipeline against the **store matrix**                                  | goldens + scale (order-independent)                |
| `adapter`     | framework HTTP shim (FastAPI, Django; optional-dep gated)                   | inline; may reuse a golden case read-only          |

The adapter tier boots `demo.server` (the `demo/` package) end to end.

## Fixtures

- A **case** (`fixtures/cases/<set>/`) is hand-authored and committed: `shapes.ttl` + `data.ttl` (or `data.trig` — a named-graph set) plus per-case subdirectories. The correctness unit, validated against `InMemoryStore` (rdflib). Registry: `CASES`.
- A **scenario** (`fixtures/scenarios/<name>/`) is generated: committed `shapes.ttl` plus a correctness anchor (`smoke/`); data is produced in memory at any scale (`Scenario.data_at(scale)`). Each names its own flat `params` and a `sweep` — the ordered scales the perf probe runs. Registry: `SCENARIOS`.

Both satisfy the `CaseSource` Protocol, so the same runners (`run_case`, `run_case_on_store`) serve both. Each registry has a drift guard (`test_case_registry`, `test_scenario_registry`): a directory with no registration, or a registration with no directory, fails.

## Metadata contract

Fixtures are self-describing ([ADR-0021](../docs/adr/0021-declarative-fixture-testing.md)) — the metadata doubles as GraphQL schema documentation and is the seed of the docs/playground site:

| Level                           | Vehicle                                | Surfaces as                                          |
|---------------------------------|----------------------------------------|------------------------------------------------------|
| Set — `graphql:Schema` resource | `rdfs:comment`                         | the built `GraphQLSchema` description                |
| Node shape                      | `rdfs:comment`                         | GraphQL type + root-field descriptions               |
| Property shape                  | `sh:description` (one line each)       | GraphQL field descriptions                           |
| Shape bullets (optional)        | `sh:intent`                            | site callouts or bullets — inert for now             |
| Case                            | `"""description"""` in `query.graphql` | failure output on golden mismatches; site case index |
| Data                            | `data.ttl` `#` comments                | informal — no rules                                  |

Authoring rules for metadata:
- **Visitor voice** — write for a non-maintainer: behavior first, plain terms, no fixture-ese. A case docstring may end with one optional `In the SPARQL:` sentence flagging what the golden shows.
- **No ADR references** — name the behaviour, not the decision record; ADR citations live in source docstrings, which the site does not render.
- **Realism wins** — when a trivial fixture and a realistic one exercise the same machinery, write the realistic one. E2E cases showcase real use; realism is what makes them intuitive.

Every case carries all of: `query.graphql` (named operation + description), `expected.json`, `expected.sparql` (byte-asserted), and `config.json` — the request-scoped envelope (`lang_tags` / `read_graphs`, strict keys, `{}` when empty). Criticism of a fixture embeds where it applies as a greppable `REVIEW:` marker (in `sh:intent` or a case description) — `grep -rn "REVIEW:" tests/fixtures/` surfaces every flag.

## Evaluation tier

`just eval` swaps `InMemoryStore` for the shipped `HttpxSparqlStore` against real triple stores via [testcontainers](https://testcontainers.com) — Docker required. `EVAL_STORE` (comma-separated) selects the legs; the default is the license-free set (`oxigraph`, `fuseki`, `qlever`), with `graphdb` as the opt-in license-gated leg. Nightly CI runs one job per store, each uploading its report.

- **Parity** — real-store JSON must equal the golden, compared order-independently (`support.goldens.canonicalize`; the outer query has no `ORDER BY`, so lists may permute — ADR-0010). Results are never normalized (ADR-0022): a store legitimately deviating on a case gets a `KNOWN_DIVERGENCES` entry (`support/eval/divergences.py`), which xfails it at collection and records `divergence` in the report.
- **Performance** — whole-operation latency per sample (`total` = `core` + translate / store / convert, with http / decode the store split for HTTP stores; definitions in `support/eval/report.py`) and row counts across each scenario's `sweep`; median + p95; report-only, no thresholds. Written to `evaluation-report.json` (`EVAL_REPORT_PATH`) and rendered into the CI summary.

To add a store: implement the `StoreSession` Protocol (`support/eval/session.py`) in a sibling module and register a `StoreSpec` in `STORES` (`support/eval/stores.py`) — runners, fixtures, and the report are store-agnostic.

**GraphDB Free** needs a license (GraphDB 11+; request at <https://graphdb.ontotext.com/>). Drop the **verbatim** license file at `tests/tiers/evaluation/graphdb.license` (gitignored) or set `GRAPHDB_LICENSE_FILE` — don't strip whitespace or reformat, GraphDB validates strictly. In CI it's the base64 `GRAPHDB_LICENSE` secret; without it the leg skips while the OSS legs run.

## Coverage

Branch coverage, gated at 100% (`pyproject.toml`, CI via `just test-cov`). The deliverable is 100% **accounted-for**, not 100% executed: every uncovered line is either covered by a test or annotated with a rationale — `# pragma: no cover` plus a short *why* (`unreachable — graphql-core validates …`, `defensive — direct-call contract only`); a bare pragma is not accepted.

`just mutate` gates on the committed mutation floor (`mutmut-floor.json`); raising it is deliberate, with recorded rationale. Nightly regenerates the coverage and mutation badges and pushes them to the `badges` branch.
