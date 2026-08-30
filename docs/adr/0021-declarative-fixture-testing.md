# ADR-0021 — Declarative fixture testing

**Status:** Active

## Decision

**Tests as data.** RDF and GraphQL/SPARQL are declarative, so e2e test cases are defined as data — co-located shapes/data plus per-case `query.graphql` and expected JSON/SPARQL — driven by **explicit** pytest modules, not directory auto-discovery. Cases stay minimal, focused, readable; the tier vocabulary and harness mechanics live in `tests/README.md`.

**Five tiers, each with a contract** (what it tests / how it builds inputs / what it asserts):

| Tier | What | Inputs | Asserts |
|---|---|---|---|
| unit | one module's public interface | hand-built | direct values, error paths |
| integration | 2+ modules composed | shared fixtures | produced SPARQL, variable maps |
| e2e | full pipeline | declarative case files | GraphQL JSON + executed-SPARQL goldens |
| evaluation | parity + performance vs a real store | generated scenarios | order-independent comparison; report-only timings |
| adapter | HTTP contract per adapter | framework test clients | envelope behaviour |

Tier markers are stamped automatically from the `tests/tiers/` directory — no per-test decoration.

**Registries are explicit, not auto-discovered.** Which case directories run is an opt-in registry; a case can live on disk but stay opted out (work-in-progress) by being unlisted. Drift guards fail loudly if a directory exists unregistered (it would silently never run) or a registered case has no directory — one guard per registry.

**Cases vs scenarios — the provenance/scale seam.** Correctness cases are hand-authored, committed, small, run every CI against the in-memory store; evaluation scenarios generate data at scale against a real store. The two were originally fused through one fixture class, and the fusion rotted: a generated `data.ttl` written to disk inside a cached read path, evaluation concerns leaking into the correctness registry. What actually varies across the seam is exactly two things — data provenance (committed vs generated) and a scale axis (none vs degradation sweep) — so the split earns its keep: two roots, two registries, two guards, sharing only the low-level case-loading and execute-against-store primitives. Scenario axes are flat parameter mappings so each scenario names its own (`entities`, `multi_value`, `langs`, `depth`, …) without the harness knowing parameter names.

**`data` is an explicit argument** to `run_case` — the caller controls provenance; case loading stays strictly read-only.

## Consequences

- Adding a scenario is one directory, one generator function, one registry entry — the deferred taxonomy (lang-multiplicity, deep-offset, deep extraction) plugs in without harness edits
- Expected exceptions, parse/build failures, and behaviour without an operation or dataset stay in unit/integration — imperative tests, not fixtures
