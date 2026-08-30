# ADR-0005 — Node shape inheritance

**Status:** Active

## Context

A `sh:NodeShape` carrying `sh:node Parent` includes the parent's property shapes among its fields — field reuse via a DAG, never subtyping.

## Decision

**Field-only.** Only property shapes are inherited; the parent's node-level scalar constraints (`sh:datatype`, `sh:minLength`, node-level `sh:minCount`, `sh:closed`) are dropped. fastshaql is a query-schema generator, not a SHACL validator — node constraints have nothing to say about a generated GraphQL type (ADR-0020). This is a deliberate, documented narrowing of SHACL's all-constraints `sh:node` semantics.

**Flatten at parse.** A dedicated parse pass — after `sh:class` resolution, before visibility resolution — rewrites each child's `property_shapes` to the union of its own and its transitive parents', so every downstream consumer reads one flattened set and needs no inheritance awareness. Rejected alternative: an own-only IR plus a registry-derived effective-fields view — it would force every downstream read site (schema, translation, converter) through the view for no gain. Running before visibility resolution means closed-world checking (ADR-0008) naturally sees inherited relationship targets.

**Cycles reject at parse.** SHACL explicitly permits processors to fail on recursion, naming static-query architectures as the valid reason — fastshaql is exactly that. Authors factor shared constraints into a common base reached via a DAG. A field-name fixed-point cycle resolver was rejected as more permissive than the spec requires.

**Collisions.** A child redefining an inherited field name is an **override**: the child's own property shape replaces the inherited one wholesale, with a warning naming the route it came through. OO-intuitive authoring intent beats fail-loud here; compatibility policing (scalar-override-must-stay-scalar) is validator thinking, off-library per ADR-0020. Transitive nearest-definition-wins falls out of the topological merge.

- Two *parents* defining the same field while the child stays silent still raises — there is no principled tiebreaker, and deterministic-but-arbitrary (IRI-sort) resolution would be silent
- The same property shape reaching the child via two paths (shared-grandparent diamond) is one constraint applied once — deduped, not a collision
- Override/merge and strict-reject-all alternatives are rejected: silent override hides author intent only in the parent-vs-parent case (hence the raise), and merge (tighten cardinality etc.) diverges from SHACL's AND-semantics and is complex for a query generator

## Consequences

- A shapes graph without `sh:node` behaves byte-identically
- Inherited enum, derived, and composite-path fields work without special handling — they are `PropertyShapeIR`s like any other
