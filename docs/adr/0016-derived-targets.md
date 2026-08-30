# ADR-0016 — Derived targets

**Status:** Active

## Decision

SHACL 1.2 generalizes `sh:targetNode`: each value is a node expression evaluated against the data graph with **the shape itself as focus node** — the root entity set of a shape becomes computable ("all subclasses of some top parent as one root field" is not expressible with `sh:targetClass`, which matches direct `rdf:type` only).

- **Loud rejection.** Unsupported target declarations reject at parse, naming the predicate — no target declaration is silently dropped (the six-kind inventory lives in the [support matrix](../SUPPORT.md)). **Implicit class targets are supported**, not rejected: a shape typed `rdfs:Class` (alongside `sh:NodeShape`) or `sh:ShapeClass` targets the SHACL instances of its own IRI, lowered through the instances-of expression; the implicit shape is class-indexed under that IRI so `sh:class` references and class-keyed visibility declarations resolve to it.
- **One declaration per shape.** `sh:targetClass` or exactly one `sh:targetNode` expression; multiple values and mixed kinds reject as a *named narrowing*. The spec unions all target declarations; that union is deliberately not lowered, with the `UnionPattern` widening pre-staged (ADR-0015) so a future widening starts from a solved design.
- **Term focus.** Any flat-tier node-expression arm may sit at `sh:targetNode`; the translator generalizes from a variable to a *term* focus — the shape-IRI constant — through the same dispatcher as property position (ADR-0015).
- **`shnex:instancesOf` promoted** to supported at both host positions (`sh:values` and `sh:targetNode`), lowering `?v rdf:type/rdfs:subClassOf* ?c` with the class parameter constant-folded. Subclass closure reads the **queried graphs only** — the spec's option to read `rdfs:subClassOf` from the shapes graph is a documented deviation, consistent with the read-only stance (ADR-0020).

Root emission gains a source dispatch symmetric to the property-level splice; pagination and `where` filters compose unchanged. A shape whose target expression yields literals produces a root field that can never match — accepted: rejected-loudly applies to *ill-formed* declarations, not to empty results.
