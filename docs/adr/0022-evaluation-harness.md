# ADR-0022 — Evaluation harness

**Status:** Active

## Context

E2e goldens validate against the in-memory store (rdflib). Production deployments target real triple stores — and SPARQL engines may return the same bindings in different row order, so naive JSON equality false-positives on parity runs.

The outer query deliberately carries no `ORDER BY` (ADR-0010 documents why response order is engine-defined), which is what makes order-independent comparison the only sound parity oracle.

## Decision

- **Parity first.** The declarative e2e cases are reused verbatim against every store: goldens stay in-memory-validated. Real-store runs compare **order-independently** — recursive canonicalization of all JSON lists, not just root entity lists. Store-specific behavioral deviations (literal canonicalization, numeric type normalization) become known divergences: recorded per case with a reason, never normalized away in comparison — the matrix exists to surface portability gaps, not to be green everywhere.
- **Store matrix via `StoreSession`.** One adapter per store (query endpoint, container image, graph loading, teardown), selected by name at collection time — `EVAL_STORE`, comma-separated, defaulting to the license-free set; nightly CI runs one job per store. Shipped legs: Oxigraph, Fuseki (Jena), QLever, and GraphDB Free (license-gated: skips cleanly without its license file). The store under test remains the shipped one (`httpx` extra, ADR-0018) — test what we ship. Adapters load graphs individually as Turtle (bulk TriG/N-Quads to a Graph Store Protocol target is rejected or silently lossy on some stores) and **configure stores toward SPARQL 1.1 semantics where a supported knob exists**; deviations without a knob — QLever's numeric datatype rewriting, zero-length-path behavior on absent terms — are known-divergence material when a case exercises them.
- **Whole-flow metrics, report-only.** Per sample: `total` (whole graphql-core operation) plus `core` (the per-sample residual) and the translate / store / convert phases inside `execute_query`, with http/decode the store split for HTTP stores; the envelope stays unmeasured (ADR-0019). Generated scenarios (ADR-0021) probe degradation sweeps; latency and row counts land in the report.
- **Report carries the store dimension.** Per-store metadata (image, license tier), a parity conformance matrix (per case set, with failures and known divergences named (if needed); per-case detail in the JSON artifact), cross-store perf comparison, and the in-memory store as baseline rows.
- **Evaluation stays out of the PR path** — marker-excluded; nightly and manual runs only.

## Consequences

- Translate-phase latency stays flat regardless of data scale (selection-driven, ADR-0013); store and convert grow with row explosion — which dominates is environment-specific, which is exactly what the report exists to locate
- Docker is required for local evaluation runs; the OSS legs (Oxigraph, Fuseki, QLever) run for any contributor, while license-gated GraphDB Free skips cleanly without its license (acquisition and CI wiring: tests/README.md)
- Live matrix runs (pinned images): QLever's union default graph *matches* the harness contract (in-memory `Dataset(default_union=True)`), so the named-graph cases pass there; the registered divergences cluster on the no-`FROM` default-graph contract plus one engine-defined tie-break (ADR-0010) — `support/eval/divergences.py` is the live record
