# fastshaql demo

**fastshaql** turns a SHACL shapes graph into a GraphQL schema and translates GraphQL queries into SPARQL — a typed, read-only API over any RDF knowledge graph. This demo runs it against a small library domain knowledge graph (works, authors, members, loans, SKOS topics, spread across named graphs) so you can see nearly every feature in one place. For the library itself, see the [main README](../README.md).

One module, three jobs:

- **Quickstart playground** — `just demo` and open GraphiQL.
- **Reference wiring** — `server.py` as the FastAPI path.
- **Smoke check** — `smoke.py` runs every tour query against the fixture.

Not published — an unpublished uv workspace member (`fastshaql-demo`).

## Run

```bash
just sync   # or: uv sync --all-extras --all-groups --all-packages
just demo   # GraphiQL: http://127.0.0.1:8000/graphql
```

With no flags the server serves the bundled [quickstart fixture](./quickstart).

| Flag | Purpose |
|---|---|
| `--shapes` | SHACL shapes file or directory (default: the bundled quickstart shapes) |
| `--data` | RDF data for `InMemoryStore` (mutually exclusive with `--endpoint`) |
| `--endpoint` | SPARQL query URL for `HttpxSparqlStore` to connect a real triple store |
| `--fake-latency` | Artificial per-query delay (seconds), for load tests |

### Headers in GraphiQL

Graph selection and language selection are **per request**, carried by HTTP headers — and GraphiQL can send them: open the Headers pane and add:

```jsonc
{
  "Accept-Language": "fr, en;q=0.8",
  "X-Default-Graph": "http://example.org/graphs/catalog, http://example.org/graphs/loans"
}
```

## The guided tour

Fourteen stops, progressively fancier. Every query lives in [`quickstart/queries/`](quickstart/queries/) — paste into GraphiQL, or run them all headlessly with `just smoke`.

| # | Stop | What it shows |
|---|---|---|
| 01 | [First query](quickstart/queries/01-first-query.graphql) | a `sh:ShapeClass`, scalars, the built-in shape of every response |
| 02 | [Nesting](quickstart/queries/02-nesting.graphql) | relationship traversal, a sequence path (`authorName`), an inverse path (`stockedAt`), an alternative path (`isbn`) |
| 03 | [Language](quickstart/queries/03-language.graphql) | `rdf:langString` fields + the `Accept-Language` header as a fallback chain |
| 04 | [Enums & scalar filters](quickstart/queries/04-enums-and-scalar-filters.graphql) | `sh:in` enums (IRI- and literal-backed) filtering like scalars; implicit AND |
| 05 | [Logic](quickstart/queries/05-logic.graphql) | `OR` over branches, `NOT` around a relationship |
| 06 | [Relationship filters](quickstart/queries/06-relationship-filters.graphql) | `where` through relationships (`FILTER EXISTS`), enum values in filters, three-level nesting |
| 07 | [Pagination](quickstart/queries/07-pagination.graphql) | `limit`/`offset` paginate entities, compose with filters |
| 08 | [Inheritance & override](quickstart/queries/08-inheritance-and-override.graphql) | `sh:node` field reuse (Member/Author ← Person), child-wins override, `sh:codeIdentifier` |
| 09 | [Recursion](quickstart/queries/09-recursion.graphql) | a self-relationship, nested twice |
| 10 | [Transitive paths](quickstart/queries/10-transitive-paths.graphql) | `sh:oneOrMorePath skos:broader`: one field walks the topic tree |
| 11 | [Derived values](quickstart/queries/11-derived-values.graphql) | `shnex:exists`, derived enums (`shnex:if` + `sh:in`), a raw `sh:select` walking the class tree, `sh:defaultValue` |
| 12 | [Derived relationships](quickstart/queries/12-derived-relationships.graphql) | `shnex:nodes` + `shnex:filterShape`: computed relationships that traverse and filter like real ones |
| 13 | [Derived targets](quickstart/queries/13-derived-targets.graphql) | `shnex:instancesOf` computes a root set from the class tree |
| 14 | [Named graphs](quickstart/queries/14-named-graphs.graphql) | `X-Default-Graph` scoping: single graph, merged graphs, union default |

## Reference wiring

The production SPARQL client ships with the library: `pip install fastshaql[httpx]`. It wraps a shared `httpx.AsyncClient` you own — pooling, transports, time-outs, and any caching are configured on that client — and decodes through the core `decode_sparql_results` seam (ADR-0018). `server.py` shows the full FastAPI assembly: `load_shapes` → `parse_shapes` → `build_executable_schema` once at startup, one `AsyncClient` created in `build_app` and closed in the lifespan, `ResolverContext` per request, `build_graphql_router` for POST + GraphiQL.

`throughput.py` drives the app in-process (no socket) and reports latency percentiles:

```bash
uv run --package fastshaql-demo python -m demo.throughput \
  --shapes demo/quickstart/shapes.ttl \
  --data demo/quickstart/data.trig \
  --query demo/quickstart/queries/06-relationship-filters.graphql \
  --requests 200 --concurrency 20 --latency 0.05
```
