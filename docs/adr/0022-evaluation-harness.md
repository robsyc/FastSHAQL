# ADR-0022 — Evaluation harness

**Status:** Active

## Context

E2e goldens validate against the in-memory store (rdflib). Production deployments target real triple stores — and SPARQL engines may return the same bindings in different row order, so naive JSON equality false-positives on parity runs.

The outer query deliberately carries no `ORDER BY` (ADR-0010 documents why response order is engine-defined), which is what makes order-independent comparison the only sound parity oracle.

## Decision

- **Parity first.** The declarative e2e cases are reused verbatim against a real store: goldens stay in-memory-validated. Real-store runs compare **order-independently** — recursive canonicalization of all JSON lists, not just root entity lists
- **Store-pluggable via `StoreSession`.** The harness consumes a minimal protocol (query endpoint, container image, graph loading, teardown); GraphDB CE via testcontainers is the first adapter, and the store under test is the shipped one (`httpx` extra, ADR-0018) — test what we ship. Adding a store is a sibling adapter
- **Performance is report-only.** Generated scenarios (ADR-0021) probe Cartesian row explosion (ADR-0014) across a degradation sweep; per-phase latency and materialized row counts land in a report with no thresholds — numbers are environment-specific and not recorded in-tree
- **Evaluation stays out of the PR path** — marker-excluded; nightly and manual runs only

## Deferred: the second store

The `StoreSession` seam exists to make the extension path obvious, not because a second store exists. QLever (the next likely contender) supports the Graph Store HTTP Protocol and Update, so live per-case replace works — the divergence is in specifics, not a fundamentally different model: a seed-index build before the endpoint is usable, an access token, a different URL shape, post-update triples in less-optimised structures (the perf sweep would likely want an index rebuild per scale point). Discover those empirically when QLever is attempted — the seam can grow a method then, rather than being designed against assumptions now.

## Consequences

- Translate-phase latency stays flat regardless of data scale (selection-driven, ADR-0013); store and convert grow with row explosion — which dominates is environment-specific, which is exactly what the report exists to locate
- Docker is required for local evaluation runs
