# ADR-0009 — Composable filters and promotion

**Status:** Active

## Hard-filter semantics

Root query fields accept a `where` argument typed as a per-shape `{TypeName}Filter` — one operator input per scalar property, the target shape's filter input per relationship property, and recursive `AND`/`OR`/`NOT` combinators. GraphQL `where` clauses are **hard filters**: `where: {subtitle: {eq: "X"}}` means "return only things where subtitle is X", not "return all things, optionally including the subtitle if it matches" — matching every major GraphQL API framework. SPARQL offers three OPTIONAL/FILTER patterns:

| Pattern | Entities without the field |
|---|---|
| `OPTIONAL { P FILTER(F) }` | Returned, binding absent — soft filter |
| `OPTIONAL { P } FILTER(F)` | Excluded — hard filter |
| `P FILTER(F)` (promotion) | Excluded — hard filter, bound triple |

**Promotion is the mechanism.** A Property targeted by a filter is emitted as a bound triple instead of inside `OPTIONAL`, so the `FILTER` can bind its variable; the `OPTIONAL` + `FILTER(BOUND(?var))`-guard alternative is rejected unless profiling shows a benefit. Deep nesting requires it: for `company: {city: {name: {eq: …}}}` the entire `thing → company → city → name` chain must be bound — any `OPTIONAL` in the chain errors the outer filter on unbound variables.

**Promotion scope is per level.** The promoted set is computed once per shape from that level's `where` argument and never propagates into child selections — a root-level promoted `name` never binds an unrelated optional `name` on a child shape; relationship filters are handled independently via `FILTER EXISTS`, not by inheriting the parent's promoted set.

**OR/NOT + optional relationships — documented semantics.** An optional relationship appearing in only one `OR` branch is promoted across the whole query, so entities without that relationship are excluded even though the other branch could logically match; `NOT { employer: {name: {eq: "Acme"}} }` likewise excludes entities with no employer, though the intuitive reading would include them. Hard-filter semantics apply uniformly across combinators; this exclusion is documented behavior, not a promotion bug.

**The one gap:** existence filters (`where: {subtitle: {exists: false}}`) need `FILTER NOT EXISTS { … }` rather than promotion — a future filter operator, not a design flaw in promotion.

## Expression AST

Filter values translate to a typed expression AST (frozen dataclasses, one `render()` per node): `CompareExpr`, `FunctionCall`, `InExpr` (negation expressed as `NotExpr(InExpr(…))` — no negated field), `AndExpr`/`OrExpr`/`NotExpr`, `ExistsExpr` (the sole EXISTS node — relationship filters and combinator branches compose through it), `TermExpr`. **Parenthesization is parent-decided**: `OrExpr` wraps AND children, `NotExpr` wraps its child — minimal, SPARQL-precedence-correct output. Informed by rdf-sparql-builder (JS), which uses a similar composite but lacks expression-level AND/OR/NOT and EXISTS — both required here.

## Relationship filters and dispatch contexts

Relationship fields accept the target shape's filter type directly; a filtered relationship is always promoted (bound join triple) and renders as `FILTER(EXISTS { … })` containing only child triples — no join duplication. Scalar + relationship constraints at the same level combine into one `FILTER(scalar && EXISTS { … })`. Quantifier operators (`some`/`every`/`none`) are deferred — `FILTER EXISTS` semantics (at least one matching related resource) is the shipped contract.

One `walk_where` walk feeds both the promotion pre-scan and filter translation. Two contexts adapt field dispatch to scope: **`RootFilterContext`** (root level — flat query or the paginated inner sub-SELECT, ADR-0010; re-emits bind triples for selected fields when isolated) and **`ExistsContext`** (inside `FILTER EXISTS`; allocates fresh `_rf_`-prefixed variables namespaced per relationship filter, so multiple EXISTS blocks filtering homonymous fields cannot collide). The split is why entity-determining patterns had a home to move into when pagination arrived.

Language-typed filter comparisons use `STR()` over the resolved variable (ADR-0012) — the value the client would see, language-agnostic comparison.
