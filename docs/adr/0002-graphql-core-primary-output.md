# ADR-0002 — graphql-core schema as primary output

**Status:** Active

## Context

The original design produced Strawberry-native output — `@strawberry.type` classes built directly from Shape IR — which hard-coupled every consumer of fastshaql to Strawberry. Three options were evaluated for the Core/Adapter boundary:

| | A: Core emits graphql-core schema | B: Core emits only Shape IR | C: Core emits graphql-core types (no resolvers) |
|---|---|---|---|
| Directly executable? | Yes | No | No |
| Framework-neutral? | Yes | Yes (each adapter reimplements schema gen) | Partially |
| Unit-testable in Core? | Yes — `graphql()` against the `GraphQLSchema` | Only parser/IR tests | No |

## Decision

**Option A.** Core produces a graphql-core `GraphQLSchema` with resolvers that invoke the translation pipeline; the schema is directly executable via `await graphql()` (async per ADR-0018). Child fields use graphql-core's default dict-key resolver — the converter returns `list[dict]` keyed by GraphQL field names, so no per-field resolvers are generated.

`execute_query` owns the translate → render → store → convert pipeline and doubles as a **direct programmatic API**, bypassing graphql-core entirely when schema serving is not needed.

## Consequences

- graphql-core (already a dependency) becomes the shared schema representation
- Full queries are executable in Core tests without any adapter
- Strawberry becomes an optional consumer, not a required output format
