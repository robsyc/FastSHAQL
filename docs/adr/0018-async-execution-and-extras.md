# ADR-0018 — Async execution and extras

**Status:** Active (provisional)

## The narrowing insight

The originating service's async win was DataLoader fan-out to kill N+1 — fastshaql **has no N+1**: the single-query strategy (ADR-0014) collapses every selected relationship into one SPARQL query per root field, then post-processes. The intra-request concurrency that justified async machinery is already eliminated by design. What async still buys: request-level event-loop concurrency, frictionless adoption by async-first consumers, and httpx connection pooling.

## Decision

**Async at the execution spine (the I/O boundary) only; the CPU-bound core stays sync.**

| Layer | Status |
|---|---|
| Parser, Shape IR, translation, rendering, converter, schema builder | Sync — pure computation |
| `SparqlStore.query` protocol, `execute_query`, resolvers | `async`, awaiting exactly one `store.query` per root field — a single await point |
| Adapters | Native `async def` handlers + graphql-core async execution — no threadpool gymnastics |

**Provisional.** After the performance evaluation of the example server (ADR-0022), async may be reverted or altered; the seams are kept so a revert is mechanical — protocol `async`→`sync`, resolver, one `to_thread` removed. No DataLoader is introduced; async here is purely "the one store call becomes an await".

## The HTTP store as an extra

- **Core stays httpx-free.** The shipped store (`fastshaql.stores.http`, behind the `httpx` extra) consumes Core's public surface; the boundary is enforced by a static neutrality scan (frameworks *and* transports), not just convention. The protocol is the contract — the shipped store is one implementation, not a core dependency
- **Caller-owned client.** The store wraps an `httpx.AsyncClient` the caller owns and never constructs or closes one — pooling, transports, time-outs, and any caching layer are the caller's optimization surface. The store adds only SPARQL protocol shaping (POST, `application/sparql-query`); decoding goes through the shared wire-decode seam (ADR-0019)
- **`RemoteSparqlStore` removed outright** — the rdflib-`SPARQLStore`-in-a-thread convenience was a second, weaker remote path that nothing shipped depended on. The in-process story is `InMemoryStore`; the remote story is the extra. Clean pre-release slate, no deprecation path
- **Extras split by dependency, not capability** (`fastapi`, `django`, `httpx`, recursive `all`, no cross-coupling) — future growth composes at the same seams: an aiohttp backend would be its own module and its own extra, never a core dependency

## Consequences

- Base dependencies are `rdflib` + `graphql-core` + `orjson` (ADR-0019); httpx arrives only via the extra, and serving over an in-process `InMemoryStore` never installs an HTTP client
- The `graphql_sync` example gave way to `await graphql(…)`; ADR-0002's "schema as primary output" stance is unchanged
- The provisional posture is the arc, not an exception: ship behind narrow seams, confirm with evaluation, keep the seams so the revert stays mechanical
