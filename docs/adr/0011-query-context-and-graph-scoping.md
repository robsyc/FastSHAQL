# ADR-0011 — QueryContext and graph scoping

**Status:** Active

## One context object

Language preference and graph read-scope are cross-cutting concerns scoped to a single GraphQL operation. They are bundled into one frozen `QueryContext` dataclass instead of being threaded as individual keyword arguments through the translation chain — each new cross-cutting parameter would otherwise touch every signature between the adapter and the SPARQL builder, and combinators would multiply. Two fields ship (`lang_tags`, ADR-0012; `read_graphs`, below); adapters construct the context per request via a `context_getter` convention, and Core stays oblivious to where the values came from.

## Graph scoping via `FROM`

**Decision.** `read_graphs: tuple[str, …]` translates into `FROM <iri>` dataset clauses on the outer `SelectQuery` only. The motivating use case is tenant/provenance isolation: a knowledge graph partitioned into named graphs, with a client scoping a whole operation to one graph or a merge of a few, per request. Empty tuple emits no `FROM` — the store's default dataset, unchanged. Each value is wrapped in `URIRef` at translation and rendered through the term-rendering chokepoint (ADR-0017), which raises on breakout characters at render time.

**Rejected options:**

- `GRAPH { }` wrapping / per-quad graph terms — serves per-*relationship* graph traversal (a different use case), needs a new AST node or quad emission, and interacts non-trivially with the pagination sub-SELECT (ADR-0010)
- `FROM NAMED` + `GRAPH` — fastshaql emits only unqualified triple patterns, so `FROM NAMED` would populate a named-graph pool that nothing reads
- Store-protocol dataset selection — the store contract is "execute this string"; baking `FROM` into the rendered SPARQL keeps `SparqlStore`, the in-memory store, and the HTTP store unchanged
- Single graph (`str | None`) — `FROM` is inherently repeatable (RDF merge) and the tenant-plus-shared-reference-data pattern needs at least two

A per-`graphql:Schema` default graph (ADR-0008 container, request overrides) is deferred; a deployment bakes defaults into its `context_getter`, which already covers the use case.

**`FROM` replaces, never augments, the default graph.** The unnamed default graph has no IRI and cannot be listed in a `FROM` clause — once any `read_graphs` entry is set, the store's unnamed default graph is invisible to that query. A deployment with an always-present TBox graph loads it into a *named* graph and prepends it via the `context_getter`; store-specific virtual default-graph IRIs exist but are non-portable and unsupported.

**Relationship traversal is graph-bound.** With `FROM` only, a relationship's target must live in the same default-graph merge — cross-graph relationships remain unsupported (per-relationship traversal is the deferred `GRAPH` option above).

**Deployment caveat.** Dataset clauses are baked into the rendered query string — remote deployments must confirm their endpoint permits in-query `FROM` (some disable or sandbox it); there is no out-of-band dataset selection in the store contract.

## `read_graphs` vs `write_graph`

Read scope and write target are separate concepts in SPARQL: `FROM` describes the graphs merged into a query's default graph, while Update's `WITH` / the Graph Store Protocol address the one graph being *modified*. `QueryContext` therefore reserves a single-valued `write_graph` slot for a future writes era; reads never consume it — translation rejects a set value, so the slot can flow through context plumbing (headers, config) today but can never silently masquerade as a read scope. One polymorphic graphs field would collapse the two at the API level, recreating exactly the wording bug the `read_graphs` rename fixed.
