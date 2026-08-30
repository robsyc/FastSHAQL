# ADR-0004 — Shape IR vocabulary and classification

**Status:** Active

## Decision

**Shape IR mirrors the shapes graph.** The frozen dataclass hierarchy — `ShapeIR` base; `NodeShapeIR` (target, GraphQL type name, nested properties); `PropertyShapeIR` (exactly one path plus value constraints) — records what the shapes graph declares and nothing else. Named shapes use their IRI; blank-node shapes get a synthesized IRI at parse time. Downstream consumers trust the IR to be well-formed (a malformed IR is a parser bug). This mirror principle is why later cross-cutting state (visibility, ADR-0008) lives on the registry, never on the IR. SHACL property paths (`ShaclPropertyPath`) are likewise separate from the SPARQL path AST (ADR-0013); translation maps between them, the IR does not render.

**GraphQL names are explicit artifacts.** `graphql_type_name` and `graphql_field_name` (from `sh:codeIdentifier` or IRI local name) are not SHACL terms — they are generated-API surface, resolved once at parse and stored on the IR.

**Two-pass parse with synthetic shapes.** Pass 1 parses every shape with relationship references left raw; pass 2 resolves `sh:class` cross-references via target-class lookup, creating a synthetic empty `NodeShapeIR` (plus a warning) for untargeted classes — so every relationship always has a target shape to resolve against.

**Classification: two axes, not one enum.** Property classification was boolean `@property`s (`is_relationship`, `is_enum`) that defensively negated each other — O(n²) in variants, with every consumer's `if/elif` chain re-encoding the precedence. Derived fields made it three-way. The fix is two computed properties:

- `value_type` (scalar | enum | relationship) — what the values *are*; the axis every dispatching consumer matches on, with static exhaustiveness
- `source` (asserted | derived) — how values are *obtained*; read only by the value-binding splice sites (exactly two, by design)

A `DERIVED_RELATIONSHIP` cross-product variant was rejected: it decomposes losslessly into `(RELATIONSHIP, DERIVED)` and re-introduces the variant-per-combination growth the two axes kill — worst symptom being a *negative* read (`is not RELATIONSHIP`) that a new variant silently breaks. No recomposed convenience property: there is no second way to ask the same question.

## Consequences

- Future absorptions (derived enums, aggregate scalars, graph-valued properties) cost parse rules and at most one new `value_type` — not edits to every consumer site
- The boolean properties were removed outright, safe in a young library with no external callers
