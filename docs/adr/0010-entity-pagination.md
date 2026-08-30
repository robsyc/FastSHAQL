# ADR-0010 — Entity pagination

**Status:** Active

## Context

The single-query relationship strategy (ADR-0014) makes one entity span many SPARQL rows (a person with 2 employers × 3 `knows` produces up to 6 rows). A flat `LIMIT`/`OFFSET` paginates *rows* and can slice an entity mid-relationship — `LIMIT 10` returns one or two arbitrarily cut persons. Pagination must operate on the distinct entity-IRI set, never the result rows.

## Decision

When either `limit` or `offset` is present, translation emits a two-layer query instead of the flat SELECT: an inner `SELECT DISTINCT ?iri … ORDER BY ?iri LIMIT n OFFSET m` holding **all entity-membership conditions**, with field bindings and relationship traversal in the outer query:

```sparql
SELECT ?iri ?name ?employer_iri … WHERE {
  { SELECT DISTINCT ?iri WHERE { … } ORDER BY ?iri LIMIT n OFFSET m }
  ?iri <name> ?name . OPTIONAL { … }    # fields + relationship joins stay outer
}
```

Both arguments absent → the flat query, byte-identical (existing fixtures unchanged). The one `SelectQuery` node serves both the top-level and the nested role; dataset clauses are legal only on the top level, which suits the `FROM` scoping in ADR-0011.

**Filter placement is the one real complexity.** Entity-membership conditions — target-class triple, scalar filters, relationship `FILTER EXISTS`, promoted join triples (ADR-0009) — must live *inside* the inner subquery so they constrain the paginated set, not merely which outer rows display. This is exactly what the `RootFilterContext`/`ExistsContext` split (ADR-0009) provides: entity-determining patterns already had a home and are emitted into the inner subquery. Variable isolation is automatic — a subquery's projection hides its helper variables from the outer scope.

## Rejected alternatives

- **Always wrap (uniform sub-SELECT):** correct but rewrites every golden fixture and adds a join layer for zero benefit when not paginating
- **Flat `LIMIT`, row-safe queries only:** the row-safety analysis is fragile and rejects legitimate pagination
- **`GROUP_CONCAT` row collapse:** a row-reducer, not a paginator — returns `xsd:string`, cannot represent nested objects, destroys datatypes and language tags, undefined in-group order
- **Post-fetch slice in Python:** always correct but a full scan every request — a performance anti-pattern on any real store
- **graphql-to-sparql.js's approach:** slices a projection of *all* in-scope variables without `DISTINCT` — it has the row-slicing bug this design avoids

## Deferred

`totalCount` (wants a Relay-shaped response) · nested/relationship pagination (per-edge sub-SELECTs + recursive converter) · keyset/cursor pagination (the escape hatch for deep-offset cost) · client `orderBy` · stable response order — the outer row stream follows the engine's iteration order, and the response is documented as an unordered list.
