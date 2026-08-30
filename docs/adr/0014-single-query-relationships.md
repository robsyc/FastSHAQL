# ADR-0014 — Single-query relationships

**Status:** Active

## Context

The reference implementation used a hybrid strategy: a root SPARQL SELECT plus one batched DataLoader query per relationship wave at each nesting depth — 1 + N queries per operation.

## Decision

**Single SELECT with nested OPTIONALs.** One SPARQL query per root field, with relationship join triples and child patterns inlined into the WHERE clause; an optional relationship wraps the entire child sub-tree in `OPTIONAL`. One round-trip per operation — critical for remote SPARQL endpoints where network latency dominates. Multi-level filters compose naturally in a single pattern tree, and no DataLoader infrastructure is needed in Core, keeping adapters thin. The converter groups the flat result rows recursively using the variable map translation produced (ADR-0013); SPARQL-side `GROUP_CONCAT` row collapse is rejected as a paginator companion (ADR-0010).

## Risks

- Cartesian-product row explosion on deep nesting with multi-valued relationships at several levels. Mitigations: in-memory stores handle it; a configurable depth limit is detectable at translation time; profiling on real data before locking the design (the evaluation harness, ADR-0022)
- One large query may optimize worse than several small ones — an accepted trade-off

**Pivot path.** If row explosion becomes a problem on real data, the architecture pivots to the hybrid strategy: the recursive translation and variable map refactor into a per-relationship batch API with DataLoader-backed resolution. Schema building and Shape IR are strategy-independent.

## Industry alignment

The single-query approach is the industry consensus for systems backed by one capable data store:

- **Hasura** (GraphQL→SQL): single query with LEFT JOINs + JSON aggregation; explicitly evaluated and rejected DataLoader in favour of single-query
- **PostGraphile** (GraphQL→SQL): single query via look-ahead compilation; documented beating a DataLoader-based approach
- **graphql-to-sparql.js** (Comunica): single SPARQL query with chained patterns + OPTIONALs, flat rows converted to nested JSON — conceptually identical to fastshaql's converter
