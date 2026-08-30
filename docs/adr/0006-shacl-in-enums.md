# ADR-0006 — `sh:in` → GraphQL enums

**Status:** Active

## Context

`sh:in` (SHACL Core §7.9.3) constrains a property to a closed value set — exactly what a GraphQL enum expresses.

## Decision

**`sh:in` is an overlay, not a property flavor.** A non-relationship Property carrying `sh:in` classifies as an enum (ADR-0004); it does not introduce a new kind of field. The raw rdflib terms are preserved on the IR, and the list's actual **term kind** — not `sh:nodeKind` — decides rendering: all-IRI members render `<iri>` objects (the field stays scalar-flavored, no traversal), all-literal members render typed literals. Mixed-kind lists, blank-node members, and more than one `sh:in` per shape raise at parse: an enum is inherently one term kind, and exact-term-equality validation makes mixed lists incoherent as a GraphQL enum.

**Collision suffixes, not errors.** Two members that mangle to the same GraphQL name are disambiguated with numeric suffixes in member order — the later colliding member keeps the mangled base plus the first free number. Raising was the original stance and was reversed when real shapes broke: FHIR Quantity comparators (`"<" "<=" ">=" ">"`) all mangle to the same name, so raising rejected a legitimate value set. Rejected alternatives: silent last-wins (hides values), positional names `VALUE_1` (unreadable). No surveyed prior art auto-suffixes (TopBraid rejects; PostGraphile errors; Dgraph requires manual names), and there is no spec mechanism for per-value naming — `sh:codeIdentifier` applies to shapes, not list members. Names are order-dependent (reordering `sh:in` swaps which member keeps the bare name) — an accepted API-stability cost.

**Relationship-overlay `sh:in` is read-ignored.** `sh:in` alongside `sh:class`/`sh:node` narrows valid related resources for validators; reads ignore it and traverse normally, with one warning per shape. Enforcement is off-library (ADR-0020).

## Consequences

- One enum type per property shape (`{TypeName}{FieldName}`), no cross-shape deduplication — deferred
- Duplicate terms in `sh:in` are SHACL-legal: one warning at parse; serialization is first-name-wins
