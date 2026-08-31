# fastshaql — SHACL-to-GraphQL Bridge

A Python library that reads SHACL shapes, generates a GraphQL schema, and translates GraphQL queries into SPARQL. Read-only: shapes are a schema-definition language here, never a validation contract (ADR-0020).

## Language

### Shapes

**Shape**:
A `sh:NodeShape` definition in a shapes graph — describes the structure and constraints of a class of RDF resources.
_Avoid_: "node shape" as a generic synonym (reserved for the IR dataclass)

**Property**:
A `sh:PropertyShape` within a Shape — describes one field: its path, datatype or target class, cardinality, and constraints.
_Avoid_: "property shape" as a generic synonym; "field" (the GraphQL artifact)

**Shape IR**:
The frozen dataclasses produced by the parser (`ShapeIR`, `NodeShapeIR`, `PropertyShapeIR`, `ShaclPropertyPath`) — the canonical record of what the shapes graph declares.
_Avoid_: model, data model, "the IR" without qualifier

**Shape registry**:
The lookup returned by `parse_shapes` (`ShapeRegistry`). Indexes shapes by GraphQL type name, shape IRI, and target class; exposes visibility-scoped views for schema building and translation.

**Node shape**:
A Shape in Shape IR (`NodeShapeIR`): carries a target, the GraphQL type name, and nested property shapes. Must not have `sh:path`.

**Property shape**:
A Property in Shape IR (`PropertyShapeIR`): exactly one path; a scalar if `sh:datatype` is set, a relationship if `sh:class` or `sh:node` is set. Overlap resolves by value-type precedence: relationship > enum > scalar.
_Avoid_: conflating with Node shape

**Node shape inheritance**:
Field reuse via a `sh:node` triple: a child shape includes its parents' properties among its fields. Fields only — never node-level constraints (ADR-0005/0020). Transitive; multiple parents allowed. A child redefining an inherited field name is an **override**; two parents defining the same field raises (ADR-0005).
_Avoid_: mixin, extends, subtype, subclass (imply `rdfs:subClassOf`)

**Parent shape / Child shape**:
The inherited / inheriting side of a `sh:node` triple.
_Avoid_: base shape, superclass / subclass, derived shape

**Deactivated shape**:
A Shape or Property carrying `sh:deactivated true` — schema-level exclusion: no GraphQL type, no field (SHACL Core §3.1.6).
_Avoid_: disabled, hidden (conflicts with Visibility)

**Shacl path**:
A property path in Shape IR (`ShaclPropertyPath`), parsed from `sh:path` (SHACL §4): predicate, inverse, sequence, alternative, and cardinality-modifier forms.
_Avoid_: "path" without context — SHACL, SPARQL, and GraphQL paths are different things

### Names and descriptions

**GraphQL type and field name**:
Adapter-facing names resolved from `sh:codeIdentifier` or IRI local names (SHACL 1.2 §8.4). A Shape's root field is its GraphQL type name with the first letter lowercased — singular, never pluralized.
_Avoid_: type_name (ambiguous with GraphQL output types); pluralized root field names

**Description**:
Human-readable text on a Shape, propagated to the generated schema; one preferred language selected at parse time (ADR-0007).
_Avoid_: doc, comment, label

**Non-validating characteristic**:
A SHACL §8 metadata predicate (names, descriptions, ordering) that validators ignore; fastshaql consumes e.g., `sh:codeIdentifier`.
_Avoid_: annotation, metadata predicate

### Fields — value type × value source

Every Property classifies on two independent axes (ADR-0004). Dispatching consumers (schema build, filters, converter) read the type axis; only the value-binding splice sites read the source axis.

**Value type**:
What a Property's values *are*: scalar, enum, or relationship.
_Avoid_: kind (taken by FieldKind), classification

**Value source**:
How values are *obtained*: asserted (triples at the path) or derived (a node expression).
_Avoid_: derived flag, is-derived

**FieldKind**:
Cardinality enum (REQUIRED_SCALAR, OPTIONAL_SCALAR, REQUIRED_LIST, OPTIONAL_LIST) derived from `sh:minCount`/`sh:maxCount` — and from `sh:defaultValue` (a Defaulted field is non-null at any minCount, SD-6).
_Avoid_: cardinality (the SHACL constraint pair)

**Scalar**:
A Property whose value is a literal (`sh:datatype`).
_Avoid_: literal field, datatype field

**Literal space**:
A scalar Property's classification on the datatype axis — plain, language, or union (`LiteralSpace`); the parse-side input to chain semantics.
_Avoid_: value type (taken by the type axis), datatype set (the raw parse artifact)

**String-union Property**:
A scalar Property whose declared datatypes span `xsd:string` and a language-tagged string type (`sh:datatype` list form or datatype-only `sh:or`) — `String` output, chain applies with an implicit untagged terminal.
_Avoid_: "or property" (sh:or is the syntax, not the concept)

**Enum property**:
A non-relationship Property constrained by `sh:in` to a fixed list of literals or IRIs (ADR-0006).
_Avoid_: enum field, closed value set

**Enum value**:
A member of an enum property's `sh:in` list — homogeneous in term kind. GraphQL serializes a derived name (`ACTIVE`); colliding names get numeric suffixes (ADR-0006).
_Avoid_: enum member, code

**Relationship**:
A Property whose value is another RDF resource (`sh:class` or `sh:node`).
_Avoid_: link, reference, association

**Derived field**:
A Property whose values are computed by a node expression (`sh:values`), not read from asserted triples (ADR-0015).
_Avoid_: computed/virtual/calculated field

**Derived relationship**:
A derived Property typed by `sh:node`/`sh:class`: behaves as a full relationship — nested selection, row grouping, filters, pagination (ADR-0015).

### Node expressions

**Node expression**:
A SHACL 1.2 function from a focus node to a list of values (ADR-0015). fastshaql hosts them at `sh:values` (property level) and `sh:targetNode` (shape level).
_Avoid_: expression (ambiguous with the filter AST), value function

**Focus node**:
The RDF resource whose derived values are being computed. At `sh:targetNode` the focus is the shape itself (SHACL Core §3.1.3.1).
_Avoid_: current node, context node

**Filter shape**:
An inline blank-node shape for `shnex:filterShape` — keeps only candidate values that conform; fastshaql accepts the lowerable subset: hasValue/class (IRI or class list — union within one value, conjunction across values)/rootClass/datatype/pattern/numeric ranges/minCount 1/nested property (ADR-0015).
_Avoid_: validation shape

**If expression**:
`shnex:if` + `shnex:then`/`shnex:else` — chooses a branch per focus node. Conditions restricted to statically single-valued expressions (ADR-0015 deviation).

**Exists expression**:
`shnex:exists` — true/false test of whether its inner expression yields any value; never null.

**List expression**:
An RDF list of constants (`shnex:ListExpression`) — its members are the output values.

**Flat tier**:
Node-expression operators lowerable into the single merged query body (BGP + FILTER/BIND/OPTIONAL/VALUES). Formerly "Tier 1".
_Avoid_: bare "Tier 1" (collides with NG tiers, ADR-0011)

**Sub-SELECT tier**:
Operators needing a projecting sub-SELECT head-rewrite — `orderBy`, `limit`/`offset`, aggregates, top-N `sh:select` bodies. Formerly "Tier 2".

### Targets

**Target**:
The set of RDF terms a shape's target declarations produce in the data graph — the union of all declarations (SHACL Core §3.1.3). fastshaql accepts exactly one supported declaration per shape; spec-union is a documented later widening (ADR-0016).

**Target class**:
A `sh:targetClass` declaration — the RDF class whose SHACL instances the shape describes. Root query fields come from public shapes with a target (ADR-0008).
_Avoid_: resource class, entity class

**Node target**:
A `sh:targetNode` declaration — each value is a node expression evaluated against the data graph with the shape as focus node (SHACL Core §3.1.3.1).

**Derived target**:
A node target whose expression computes the root entity set (e.g. `shnex:instancesOf`, `shnex:pathValues`) instead of asserting it via `rdf:type` (ADR-0016).

**Implicit class target**:
A shape typed `rdfs:Class` (alongside `sh:NodeShape`) or `sh:ShapeClass` — targets the SHACL instances of its own IRI (Core §3.1.3.3), lowered as the instances-of expression at the shape IRI. The shape is class-indexed under its own IRI (ADR-0016).
_Avoid_: shape class (the `sh:ShapeClass` type), implicit target

### Querying

**Operation**:
A GraphQL query from a client, parsed into a selection tree before translation.
_Avoid_: request (HTTP), query (SPARQL)

**Selection**:
A node in the operation's selection tree — field, fragment spread, or inline fragment.
_Avoid_: field (ambiguous with Property), node (ambiguous with RDF)

**Filter**:
The composable input type per Shape (`{TypeName}Filter`) passed as `where` on root query fields (ADR-0009).
_Avoid_: search criteria, filter input

**Relationship-filter variable**:
Fresh `_rf_`-prefixed SPARQL variables inside `FILTER EXISTS` blocks — avoid colliding with selection-walk variables.

**Pagination**:
Root-level `limit`/`offset` paginating root entities — never SPARQL result rows (ADR-0010).

**Language preference chain**:
The ordered `QueryContext.lang_tags` tuple — BCP 47 basic ranges plus the sentinels `""` (untagged) and `*` (any language); each language-accepting field resolves to the first step with a value.
_Avoid_: lang_tag (retired single-tag name), language list (order is the point)

**Untagged sentinel / Any-language sentinel**:
The `""` / `"*"` chain entries.
_Avoid_: "empty language" (`LANG()` returns `""` but it is not a language), "wildcard" outside Accept-Language parsing

**Resolved value**:
The single value a scalar field carries after chain resolution (`BIND(COALESCE(...))` target) — what filters compare and serializers emit.
_Avoid_: coalesced value (mechanism, not concept)

### SPARQL and datasets

**Store**:
The triple-store abstraction (`SparqlStore` protocol) behind execution; `InMemoryStore` wraps rdflib.
_Avoid_: database, backend

**QueryContext**:
Cross-cutting request parameters scoped to one operation (`lang_tags`, `read_graphs`) (ADR-0011, ADR-0012).

**RDF Dataset**:
The query target per SPARQL §13: one default graph plus zero or more named graphs.
_Avoid_: store (the dataset is the query-time view)

**Default graph**:
The unnamed graph unqualified patterns match against; populated by `FROM` as the RDF merge of listed graphs. Has no IRI — once any `FROM` is present, the store's own unnamed default graph is unreachable (ADR-0011).
_Avoid_: base graph, union graph

**Named graph**:
An IRI-identified graph, reachable only via `GRAPH` (fed by `FROM NAMED`).

**Dataset clause**:
A `FROM <iri>` or `FROM NAMED <iri>` clause on a top-level SELECT; fastshaql emits `FROM` only, from `QueryContext.read_graphs`.

**No-`FROM` default graph**:
Store-defined, not spec-mandated: stores diverge between union-of-all-named-graphs and truly-unnamed-only; explicit `FROM` is identical under either contract (ADR-0011).

**Active graph**:
The graph a basic pattern matches against (SPARQL §18.1) — initially the default graph; `GRAPH` switches it.

**read_graphs**:
The `QueryContext` read-scope field: per-request graph IRIs → `FROM` clauses; the queried default graph is their RDF merge — the IRIs are never addressed *as* named graphs. Composing an always-present TBox graph with request ABox graphs is the `context_getter`'s job (ADR-0011).
_Avoid_: named_graphs (wrong — `FROM` never populates the named pool); graph_iris (the retired name)

### Translation

**Translation scope**:
Per-level shared state during translation (`TranslationScope`): subject variable, allocator, registry, language preference chain, projections, bindings (ADR-0013).
_Avoid_: query state, builder

**Variable map**:
The field-name → SPARQL-variable mapping consumed by row conversion.

**Variable allocator**:
Scoped SPARQL variable naming during the selection walk.

### Architecture

**Core**:
The framework-neutral subpackage (`fastshaql.core`) — parser, Shape IR, translation, rendering, execution.

**Adapter**:
A thin framework wrapper (FastAPI, Django) around graphql-core execution; injects `ResolverContext` per request.
_Avoid_: renderer, integration

**Public API**:
The layered facade contract: root `fastshaql` exports the three entry points (`parse_shapes`, `build_executable_schema`, `load_shapes`); `fastshaql.core` the advanced surface; each Adapter its builder. Subpackage modules are internal regardless of importability.
_Avoid_: reaching into subpackage modules from adapters or the demo

**Support matrix**:
The spec-facing record in `docs/SUPPORT.md` — one row per SHACL/SPARQL spec term, stating its disposition: supported, supported-with-interpretation (a named deviation), rejected-loudly, recognised-and-inert, or deferred. The source code and the W3C specs are the single source of truth; the matrix describes how the library interprets them, for readers who already know the specs.
_Avoid_: treating the matrix as authoritative over code or the specs; "feature list" (the ROADMAP is future-facing, the matrix is spec-facing)

**Test tier**:
The level of the test pyramid a test belongs to — unit, integration, e2e, evaluation, or adapter — auto-stamped from its `tests/tiers/` directory. Persistent harness structure.
_Avoid_: bare "tier" for node-expression lowering (Flat tier and Sub-SELECT tier own that sense)

**Store matrix**:
The set of triple stores the evaluation tier runs — one `StoreSession` adapter per store, selected by name (ADR-0022).
_Avoid_: backend ("database, backend" is the retired Store synonym); store list

**Envelope**:
The GraphQL-over-HTTP shaping contract: POST-only, always-200 `{data, errors}` (ADR-0019).

**GraphQL schema**:
A `graphql:Schema` instance in the shapes graph declaring which shapes are public, protected, or excluded for an API view. Distinct from the generated graphql-core `GraphQLSchema`.
_Avoid_: "the schema" (ambiguous)

**Visibility**:
Whether a Shape is published as a root field (public), reachable only via traversal (protected), or excluded (private) — declared by a GraphQL schema against shapes and classes, not intrinsic to the shape (ADR-0008).
_Avoid_: access control, permission

### Designed, not yet shipped

**write_graph**:
The reserved `QueryContext` slot for the future writes era — the write *target* (SPARQL Update `WITH` / Graph Store Protocol addressing, one graph). Rejected at query translation today; reads never consume it. Read scope (`FROM`/`USING`) and write target (`WITH`) are separate concepts in the spec and stay separate fields (ADR-0011).
_Avoid_: folding into read_graphs; reusing one polymorphic graphs field

**Graph-valued property**:
A Property whose value is a named graph (`sh:class` resolving to `rdfg:Graph`); read-translation switches the active graph and runs a nested query inside it. See the *Named graphs & nanopublications* backlog (docs/ROADMAP.md).

**Graph content shape**:
A Node shape targeting an `rdfg:Graph` subclass — a type marker for a graph scope, not a field source. The linkage to shapes queryable inside the graph is an open design fork.

**SHACL rule**:
A rule from the SHACL 1.2 Inference Rules spec (`sh:rule`) that infers triples from the data graph. Distinct from a node expression, which derives values at query time.
_Avoid_: inference rule (imprecise); mixing with node expressions; "SRL rule" for a `sh:rule` rule

**Process contract**:
A mutation whose effect crosses multiple nodes — minting entities, linking references, deriving values — as one governed unit; the writes era's differentiating use case (ADR-0024). Single-entity CRUD is its degenerate case.
_Avoid_: write model, business logic

**Dry-run**:
The designed mutation mode returning the would-be triples (a CONSTRUCT result) without committing — the staged-transaction preview (ADR-0024).
_Avoid_: preview query, plan
