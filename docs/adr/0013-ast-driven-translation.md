# ADR-0013 — AST-driven translation

**Status:** Active

## Why an AST walk, not resolvers

Translation walks the graphql-core selection AST with recursive Python functions, building a composite pattern tree rendered once to a SPARQL string. This replaces the resolver-driven strategy of the reference implementation (one SELECT per root field, one batched SELECT per relationship wave): the latter cannot produce optimized multi-hop queries, merge filter logic across nesting levels, or avoid N round-trips for depth-N traversals.

## Composite tree

Three composite layers share `TriplePattern` leaves while keeping different structures: query patterns (group/optional/filter/select…), the SPARQL property-path AST (predicate, inverse, sequence, alternative, cardinality modifiers), and the filter expression AST (ADR-0009). SHACL paths are parsed into their own IR and mapped to SPARQL paths at translation time — the two vocabularies never merge. Every node implements `render(indent) → str`; the tree is the unit of SPARQL testing — assert on rendered output or structural equality. Informed by rdf-sparql-builder (JS), which uses a similar composite but lacks expression-level AND/OR/NOT and EXISTS.

**Unified `TriplePattern`.** Every triple carries a property-path predicate — there is no "simple triple" vs "path triple" split; a bare IRI is a `PredicatePath`.

## Variable allocation

Each operation translation constructs a fresh allocator assigning SPARQL variables from GraphQL field-name stems; the root subject is `?iri`, scalar bindings become `?{field_name}`, and each relationship level introduces a new subject variable. A scope stack prefixes nested stems (`employer` + `name` → `?employer_name`; nested `knows`/`knows` → `?knows_knows_iri`), with collision suffixes applied globally across scopes. A frozen snapshot per level (the variable map) maps field names to variables — produced by translation, consumed by the converter.

**`_rf_` namespacing.** Inside relationship-filter `FILTER EXISTS` blocks, variables use a separate `_rf_` prefix namespaced per relationship filter — multiple EXISTS blocks filtering homonymous fields would otherwise collide. EXISTS blocks are their own SPARQL scope, so these variables bypass the selection-walk allocator.

## Translation scope

Per-level shared state (subject variable, allocator, registry, language chain, projections, bindings) rides a `TranslationScope`; relationship children construct their own scope sharing the parent's allocator and registry. Flat vs paginated WHERE assembly is isolated in one module (ADR-0010); scalar binding, relationship joins, and promotion in another (ADR-0009). Translation holds no request-global mutable state across operations.

The result is a `TranslationResult` wrapping the `SelectQuery` plus the variable map — the converter's only input beside the rows.
