# ADR-0001 — Core/Adapter split

**Status:** Active

## Context

fastshaql is a standalone library with a framework-neutral Core and thin framework Adapters; `fastshaql.core` has zero framework-specific imports.

## Decision

The separation is **structural** (separate subpackages), not abstract (protocols/interfaces) — the adapter is thin enough that a protocol layer would be over-engineering. Core owns parsing, Shape IR, schema building, translation, rendering, and execution; an Adapter is a thin wrapper (FastAPI, Django) around graphql-core execution. graphql-core is a direct shared dependency: Core reads its AST nodes, Adapter injects execution context.

Three seams carry the boundary:

- `SparqlStore` protocol — swap `InMemoryStore` for the httpx-extra store without touching Core
- `build_schema` output — any graphql-core consumer can execute the `GraphQLSchema` directly
- `ResolverContext` — Adapter constructs per-request; Core reads it via `info.context`

## Consequences

- Core is testable with only `rdflib`, `graphql-core`, and `orjson` (ADR-0019) — no HTTP, no framework
- Schema-level singletons (registry, shape) are captured in resolver closures; per-request state rides `ResolverContext`
- Adapters stay thin: construct the context, `await graphql()`
