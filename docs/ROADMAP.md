# Roadmap

fastshaql is a **read-only** SHACL → GraphQL → SPARQL translator. Writes are a [future tier](#future-writes), not a permanent boundary; knowledge-graph writes tend to require strict contracts and governance, which go against the flexibility of GraphQL queries — that tension is what the future-writes items have to resolve.

## How we work

Every feature track is **research- and spec-led, then E2E-test-driven**. Before implementation we (1) read the relevant spec sections, (2) survey prior art in other GraphQL/RDF libraries, (3) add a failing E2E fixture (`data.ttl` + `shapes.ttl` + `query.graphql` + `expected.json` + `expected.sparql`), and only then implement. See ADR-0021 (declarative fixture testing) and ADR-0022 (evaluation harness).

## Shipped (0.1.0)

**Schema derivation**

- SHACL shapes graph → graphql-core `GraphQLSchema` via `build_executable_schema` (ADR-0002); `sh:codeIdentifier` / IRI-local-name resolution (SHACL 1.2 §8.4)
- **Node-shape inheritance** via `sh:node` — field-only, flattened at parse-time (ADR-0005)
- `sh:in` → GraphQL enum per property (ADR-0006)
- **GraphQL-schema visibility** — `publicShape`/`protectedShape`/`privateShape` (ADR-0008)
- `sh:deactivated true` → schema-level exclusion (no type / no field; SHACL Core §3.1.6)

**Querying**

- Per-shape `{TypeName}Filter` input types with a `where` argument on root query fields
- **Composable filters** (ADR-0009): AND/OR/NOT, scalar operators per datatype, relationship filters via `FILTER EXISTS`, filter promotion; expression AST for `FILTER` rendering
- Query-level **language preference chains** via `QueryContext.lang_tags` — ordered BCP 47 ranges plus the `""`/`"*"` sentinels (ADR-0012)
- Per-request default-graph scoping via `QueryContext.read_graphs` → `FROM` (ADR-0011)
- **Entity-correct pagination** via an inner `SELECT DISTINCT ?iri` sub-SELECT on root fields (ADR-0010)

**Translation & SPARQL**

- AST-driven translation with a composite pattern-tree output (ADR-0013)
- **Single-query relationship reads** with post-process grouping (ADR-0014)
- **SHACL property paths**: predicate, inverse, sequence, alternative; cardinality modifiers `*`/`+`/`?`
- `sh:values` **derived fields** — SHACL-SPARQL escape tier (`sh:select`, `sh:sparqlExpr`, constants, `sh:prefixes`); bind-then-filter everywhere (ADR-0015)
- **Derived relationships** — `sh:values` + `sh:node`/`sh:class` behaving as full relationships: nested selection, row grouping, relationship filters (ADR-0015)
- **Derived targets** — `sh:targetNode` node expressions compute the root entity set (`shnex:instancesOf`, `shnex:pathValues`, `shnex:filterShape`, `sh:select`) (ADR-0016)

**Integration & foundation**

- FastAPI and Django adapters; shared GraphQL-over-HTTP envelope (ADR-0019)
- **Async HTTP SPARQL store as the** `httpx` **extra** — `fastshaql.stores.http.HttpxSparqlStore` over a caller-owned `httpx.AsyncClient`; one extra per optional dependency (`fastapi`/`django`/`httpx`) with `all` as the recursive union (ADR-0018)
- Declarative fixture test harness — cases vs scenarios (ADR-0021); GraphDB-CE evaluation harness for parity/perf (ADR-0022)

## Future: writes

The reserved `QueryContext.write_graph` slot (read scope and write target stay separate fields, ADR-0011) anchors this tier.

- **SPARQL Update surface / Graph Store Protocol** — a write path addressing one graph per operation (`WITH` / GSP addressing), flowing through the reserved `write_graph` slot. The reversal lesson stands: a per-field eager-validation library cannot match the staged-transaction control model KG writes demand (ADR-0020) — any write interface must be built around explicit transactions, not per-field validation.
- **SHACL Rules execution** — rules *materialise* triples into the data graph (recursive, stratified, with negation), upstream of reads; node expressions derive values at query time. Executing rules as part of a fastshaql write/materialisation path is a potential feature proper in this tier; today fastshaql consumes rules' output but never runs them.
- **TopBraid-style limited write interface** — `create`, `addTo`, `update`, `delete` mirroring [TopBraid's GraphQL write model](https://docs.topquadrant.com/latest/graphql/index.html) as a compromise between full mutation freedom and staged-transaction control. Reconsider after query-type consolidation.

## Bugs

Found during the support-matrix audit. Each is a silent degradation or a dead guard — the fix is a loud error or correct handling, not new design.

- **Blank `sh:node` on property shapes silently dropped** — the `NotImplementedError` guard is unreachable (`object_uri` returns `None` for blank nodes); the field degrades to a String scalar with no warning. The node-shape host (inheritance parent) raises correctly.
- **`sh:class` list form silently dropped at property level** — the SHACL 1.2 union syntax (§7.1.1) is ignored; alongside an IRI value the list is dropped, alone it degrades the field to a String scalar.
- **`sh:path ()` parses as a predicate path on `rdf:nil`** — an empty list *is* `rdf:nil`, an IRI, so the predicate branch wins before any list check; the dedicated empty-sequence error is dead code.
- **Silent arbitrary picks** — multiple `sh:node` values on one property shape and multiple `sh:path` values resolve by graph iteration order (a nondeterminism source), no warning.
- **`sh:codeIdentifier` unvalidated** — §8.4 requires `^[a-zA-Z_][a-zA-Z0-9_]*$`; any string is accepted and flows into GraphQL type/field names.
- **No path-acyclicity check** — cyclic blank-node paths crash with `RecursionError` at parse (the spec requires acyclic paths; a parse-time check is the fix).
- **List well-formedness unenforced** — single-member sequence/alternative lists are accepted (the spec requires ≥2 members); the path parser uses the lenient list walk where a strict one exists.
- **Non-integer `sh:minCount`/`sh:maxCount` silently ignored** — cardinality falls back to the optional-list defaults.
- **`sh:maxCount 0` yields a list-kind field** — a zero-capacity property still emits an always-empty list field instead of being dropped or rejected.

## Backlog

Each needs deep understanding and a dedicated design decision before any implementation.

### GraphQL query expressiveness

- `$variables` — currently coerced by graphql-core then dropped in `executable.py`; restore via AST substitution before translation (`graphql.utilities.replace_variables`). Unlocks `$where`/`$limit`/`$offset`. GraphQL Oct2021 §5.8/§6.1.2. *(Pre-impl: spec analysis + verify at the pinned* `graphql-core>=3.2` *floor.)*
- **More filters** — quantifier operators on relationships (`every` = double-negation — vacuously true on an empty target set, documented rather than silently redefined; `none` = single negation; `some` already ships as `FILTER EXISTS`); `exists`/`isNull` on scalars (`BOUND`/`!BOUND`, SPARQL §17.4.2.7); case-insensitive string patterns (`REGEX` `i` flag). SPARQL §17.3-17.4.3.7. ADR-0009.
  - **Open design decision:** the public `where` schema shape. Either **additive** sibling fields (`every`/`none` alongside today's bare-object-as-`some`) or a **breaking wrapper** (`FooRelationshipFilter { some, every, none }`, Hasura/PostGraphile convention). Decide via a survey of other GraphQL-over-RDF/SQL libraries, not a quick patch.
- **Client-facing ordering** — an `orderBy` argument on root fields. Today the response order is engine-defined and the list contract is unordered (the pagination sub-SELECT's inner `ORDER BY ?iri` fixes page *membership* only, ADR-0010); a client-facing `orderBy` needs sortable-field enums, asc/desc, langString/datetime handling, and engine-testing for non-projected sort keys (§18.3.5 allows them, but engine support is uneven). A candidate for the 1.0 gate — the bar being that no known real gap survives.
- **Per-field language filtering** (ADR-0012) — a per-field `lang` argument overriding the request-level chain (Ontotext applies per-selection-level overrides); query-side, complements `$variables`. The request-level preference chain is shipped.
- `sh:languageIn` **consumption** (SHACL Core §7.4.5) — the shape-side language constraint becomes a parse-side input to language-awareness alongside datatypes: basic ranges through the same `langMatches` machinery as the chain (GraphDB's GraphQL generator consumes it the same way). `is_language_typed` is the design hook (ADR-0012 deferred remainder).

### SHACL 1.2 node expressions — Sub-SELECT tier

The shipped Flat tier (everything lowerable into the single merged query body) is inventoried in [SUPPORT.md §2](SUPPORT.md#2-shacl-12-node-expressions); what remains:

- **Sub-SELECT tier (later):** `shnex:orderBy` first (expression keys incl. `sh:select` keys, `shnex:desc`), then `limit`/`offset` — all over one sub-SELECT head-rewrite base projecting the focus var; aggregates (`Count`/`Min`/`Max`/`Sum`, NE §4.4, `GROUP BY`) deferred — no consumer use case pulls their weight yet.
  - **Order survival through the outer join is formally unguaranteed** (SPARQL §15/§18.3.2/§18.6) — accepted as a documented engine contract (values always correct); outer key hoisting (`ORDER BY ?focus ?rank` on the outer query) is the future strict fix.
  - **Acceptance criteria:** declared order pinned in JSON list order + SPARQL golden showing the sub-SELECT; nested selection preserves order; pagination interplay unchanged (inner pagination sub-SELECT untouched).
- **Union semantics — pre-staged, not lowered:** the spec unions asserted-path with `sh:values` values (core §6.8.2) and unions all target declarations (§3.1.3); fastshaql keeps replace-not-union and one-target-per-shape as named narrowings. Feasibility is recorded in ADR-0015 (renderer-trivial `UnionPattern`; converter already set-faithful) — zero demand anywhere in prior art; widen when a real shapes graph asks.
- **Rejected loudly by name:** `FlatMap`/`FindFirst`/`MatchAll`, `distinct`/`concat`/`intersection`/`remove`, `nodesMatching`/`conformsToShape`, `shnex:var`, `sparql:`* functions, custom functions, `pathValues`-targeting-derived-property (rule chaining), multi-valued `sh:defaultValue` (not flat-SPARQL-expressible — prototype-verified), mixed/multiple target declarations.

## Cleanup, documentation & playground site

- **Hardening of release workflow:** using `just`, changeset and versioning conventions and setting up branch protections.
- **Points of discussion:** Request header conventions — the language header is settled (`Accept-Language`, resolved via `lang_tags_from_accept_language`); is `X-Default-Graph` the right name for the graph scope?
- **Mature the documentation and the test fixtures into a browsable site** — every E2E case and scenario as a worked example (SHACL in → GraphQL query → SPARQL → response), feature pages derived from the same fixtures, and an interactive playground against a live store. The pieces already line up: declarative cases are self-describing (`shapes.ttl` + `query.graphql` + goldens), the node-expression operator inventory in [SUPPORT.md §2](SUPPORT.md#2-shacl-12-node-expressions) is the feature-matrix seed, and the evaluation harness (ADR-0022) already runs real stores. First steps when picked up: per-feature docs pages generated from (or validated against) the case registry, then the site skeleton, then the playground. Potential generator: `Zensical`.

### Evaluation infrastructure & bottleneck location

Research before any structural change. We are currently **in the dark** on where costs actually sit.

- The evaluation tier (`tests/tiers/evaluation/`, ADR-0022) is store-agnostic via `StoreSession` with **GraphDB only** today. **Widen it:** add stores (QLever, rdflib, Jena, Oxigraph) and a profiling scenario set covering wide+deep cartesian selections, large result sets, derived-field-heavy shapes, and deeply-nested relationship trees (recursive converter grouping).
- **Locate the bottleneck:** graphql-core execution vs. our translation vs. query-execution vs. result processing (`decode_sparql_results` vs. `convert_rows`). `ExecutionMetrics` already splits `translate_ms`/`store_ms`/`convert_ms` — extend the harness to aggregate and report across scenarios.
- **Language-chain lowering efficiency:** per-step `OPTIONAL`s re-scan the path once per chain entry; measure against single-pass alternatives (priority `BIND` over `LANG()`) on the evaluation harness, folding an `expected.sparql` pattern review into the same pass. The question is essentially whether we can serialize our SPARQL in a more triple-store efficient way.
- **Gate:** no architectural change to the result pipeline (streaming store, `ResultUnpacker`, DataLoader/GROUP_CONCAT relationship strategy) lands until this evidence exists. The converter's O(rows × fields + rows × relationships × depth) and double-materialization are intrinsic to ADR-0014, not a converter bug.
- **Rust core rewrite** is on the table *contingent on* the profiling results — not before.

### Named graphs & nanopublications use-case

- `GraphPattern` AST node + `from_named` field (grammar [62]/[9]; planned in ADR-0013).
- **graph-valued properties** — a Property whose `sh:class` resolves to `rdfg:Graph`. Read-translation switches the active graph (`GRAPH ?bound { … }`) and runs a recursive nested query. Needs no root-in-named-graph (Head metadata can live in the default graph per SPARQL §13.1).
- **Key research outcome:** SHACL 1.2 has *no* graph-targeting concept, and no SHACL→SPARQL/RDF→GraphQL tool models "a property whose value is a graph's contents" — fastshaql invents the lowering (the `rdfg:Graph` marker is reused).
- **Pagination inside a graph scope:** the ADR-0010 inner `SELECT DISTINCT ?iri` sub-SELECT moves inside `GRAPH ?bound { … }` (grammar [55]→[10] permits; the active graph carries in) — intricate but feasible; needs its own analysis.
- **Spec surface:** SPARQL §13.2.2 (`FROM NAMED`), §13.3/§13.3.1 (`GRAPH`, graph-as-variable); grammar [9]/[10]/[55]/[62]. Requires the `GraphPattern` AST node (absent from `core/sparql/patterns.py`). ADR-0011 for levels (b)/(c).

### Reification & edge metadata (RDF 1.2)

- Triple terms (`<< >>`), `rdf:reifies`, `sh:TripleTerm` node-kind, `sh:reifierShape`/`sh:reificationRequired` (SHACL Core §1.1, §7.1.3, §7.8.5).
- **Framing question:** what is the GraphQL "edge object"? (`{ node, edge }` wrapper vs. flattened vs. opt-in wrapper — Relay-like edge shapes). This is the hard design question and the prerequisite for any code. Needs a dedicated design decision.
- Bundles: `rdf:dirLangString` (carried as a language datatype — direction ignored), `sh:memberShape` (ordered-list reads).

### Datatype-set scalars (`sh:or` on datatypes)

- The string-family half is **shipped** (ADR-0012): the union recognition (`sh:datatype` list form and datatype-only `sh:or`, both syntaxes normalizing into `PropertyShapeIR.datatypes`), one GraphQL scalar accepting either lexical form, `where` operators valid across both, and the language-preference machinery engaging with an implicit untagged terminal.
- Remaining: **converter discrimination** — distinguishing tagged from plain values in results, which binds to the future `{value, lang}` return structs (ADR-0012 deferred remainder); an all-languages exposure mode (Ontotext `ALL`, TopBraid's `LangString {lang, string}`) rides the same structs and serves language pickers.

### Query-type consolidation

- **Vision:** all SPARQL query forms — `SELECT`, `CONSTRUCT`, `ASK`, `DESCRIBE`, `INSERT`, `DELETE` — share one common WHERE/graph-pattern builder. Today `SelectQuery` is the only form (`core/sparql/queries.py`); the translation core already produces a form-agnostic `GroupPattern`, so the seam exists but is unexploited.
- **Reference:** shape-to-query models its lowering output as a near-monoid (`emptyPatterns`/`flatten`/`union`) of `(where, template, children)` and lowers straight into an AST — a useful structural contrast.
- A read-only shaped-CONSTRUCT *export* (an `Accept: text/turtle` RDF-out contract) is cheap *once* the shared builder exists — the `GroupPattern` is the reusable core, a CONSTRUCT template is synthesized from the `VariableMap`. **Important:** CONSTRUCT is a *new output contract*. It re-opens the ADR-0020 boundary and wants its own ADR. Not started until the shared builder exists.

### SPARQL AST transform passes

- Adopt a composable post-translation pass framework (dedupe, OPTIONAL-lifting, `PREFIX`-prologue extraction) only when the first real simplification need appears — most likely `PREFIX` extraction (the renderer currently emits full IRIs) or alpha-renaming of author variables in merged `sh:select` bodies (one shape's bodies share a variable namespace — a reused name silently captures across bodies). shape-to-query's `Processor` visitor pipeline is the reference. Do not build speculatively.
- **Translation hardening** (from ADR-0017's deferred list): validate IRIs at the translation edge (edge-case IRIs currently fail at render time, not validation); make a negative `limit` a GraphQL validation error rather than a translation-time `ValueError`; a configurable max-limit. All three ride the pass framework once it exists.

### Stores & extras remainder

- `aiohttp` **store extra** — an alternative async HTTP store alongside the shipped `httpx` one, following the one-extra-per-optional-dependency model (ADR-0018). No demand yet; the `httpx` store covers the remote-store case.
- `mcp` **extra interface** — optionally expose the GraphQL interface over MCP for agents to query the knowledge graph.

## Likely out of scope

- **ShEx (Shape Expressions)** — no bridge from SHACL 1.2; semantic-model mismatch; target ecosystems publish SHACL. Separate front-end project if ever.
- `sh:and`**/**`sh:not`**/**`sh:xone`,** `sh:or` **over shapes/constraint operands** — validator territory; the datatype-union case is promoted to the Backlog (*Datatype-set scalars*). `sh:and`/`sh:not` and the SHACL 1.2 validate-only components `sh:someValue` (§7.8.3), `sh:rootClass` (§7.9.4), `sh:uniqueValuesFor` (§7.9.5) already sit at **Recognised-and-inert** in the support matrix — shapes carrying them parse silently today (`sh:rootClass` is already consumed inside `shnex:filterShape`); any future work here is consumption, not recognition.
