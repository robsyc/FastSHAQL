# ADR-0021 — Declarative fixture testing

**Status:** Active

## Decision

RDF and GraphQL/SPARQL are declarative, so tests are data too. The mechanics (tier vocabulary, metadata contract, harness) live in `tests/README.md`; this record is the why.

- **Tests as data** — e2e cases are co-located shapes/data plus per-case `query.graphql` and expected JSON/SPARQL, driven by **explicit** pytest modules, not directory auto-discovery. Cases stay minimal, focused, readable.
- **Explicit registries** — which case/scenario directories run is an opt-in registry with a drift guard; a case can live on disk but stay opted out (work in progress).
- **Cases vs scenarios — the provenance/scale seam** — hand-authored committed correctness cases vs generated uncommitted at-scale scenarios: two roots, two registries, two guards, sharing only case-loading and execute-against-store primitives. Scenario axes are flat parameter mappings, so each scenario names its own (`entities`, `langs`, `depth`, …) without the harness knowing parameter names.
- **`data` is an explicit argument** to `run_case` — the caller controls provenance; case loading stays strictly read-only.
- **Self-describing fixtures** — a shapes graph declares what it is, a case declares what it proves (`rdfs:comment`, `sh:description`, `sh:intent`, the operation's `"""description"""`). One authoring pass, three consumers: GraphQL schema documentation, the docs/playground site (ROADMAP), and failure output.
- **Five tiers, each a contract** — unit, integration, e2e, evaluation, adapter; markers auto-stamped from the `tests/tiers/` directory, no per-test decoration.

## Consequences

- Adding a scenario is one directory, one generator function, one registry entry.
- Expected exceptions, parse/build failures, and behaviour without an operation or dataset stay in unit/integration — imperative tests, not fixtures.
- Scenarios carry shape-level metadata only; their smoke anchors are not cases and follow no case contract.
