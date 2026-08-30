# ADR-0020 — Read-only scope

**Status:** Active

## Context

An earlier iteration shipped a GraphQL mutation surface (`create`/`addTo`/`update`/`delete` → SPARQL Update) plus a fetch-then-validate layer (shapes-driven CONSTRUCT closure + pySHACL). The question was whether ad-hoc mutations belong in a library whose identity is *translator, not validator*. Two facts settled it:

1. **The reference proves the control concern.** TopBraid EDG — the only production-grade SHACL→GraphQL precedent — does not expose free-form per-field writes. It wraps mutations in a staged transaction: operations are a dry run until a terminal `commit`; `report` returns validation results *before* commit; the whole batch is validated then committed atomically, with change history and an escape hatch. A library can host, at best, per-field eager validation — which is weaker than that control bar.
2. **The complexity is intrinsic to *validated* writes, not accidental.** The materialiser was empirically unsound in its first iteration; orchestration for newly-linked targets, delete blast-radius validation, and nested creates each scale with SHACL coverage rather than being one-off costs. Satisfying "no SHACL-invalid data reaches the store" makes fastshaql fetch like a validator, depend on a validator, and gate like one — i.e. become one.

## Decision

**Revert the mutation and validation feature.** fastshaql is a read-only SHACL→GraphQL→SPARQL translator. Writes to the knowledge graph flow through the channels that already own governance and transactions — ETL/ingestion, application services, a dedicated write API, or a TopBraid-style platform that composes a read library like this one.

Salvaged from the reversal, independently read-valuable: the cardinality-modifier path nodes (`sh:path [ sh:oneOrMorePath ex:parent ]` now reads as `ex:parent+`) · the `_gql.py` graphql-core cast-wart consolidation · the `timed` phase-timing helper · graph scoping (ADR-0011).

## Consequences

- `build_executable_schema(registry)` takes no mutation or validator arguments; `SparqlStore` is query-only
- The "not a validator" stance of ADR-0005 now holds unambiguously — no validation path exists in-library
- **Revisit lesson:** if GraphQL writes ever return, the blocker is structural — a per-field eager-validation library cannot match the staged-transaction control model the use case demands (revisit conditions in the [ROADMAP](../ROADMAP.md))
