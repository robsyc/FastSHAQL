# ADR-0025 — Relationship targeting: `sh:node` names the target, `sh:class` types the binding

**Status:** Proposed (update this ADR and related docs when the implementation lands)

## Context

`sh:node` and `sh:class` both make a Property a relationship (ADR-0004), but their roles overlapped confusingly: `sh:class` resolved the target shape and silently overwrote any co-present `sh:node` (documented as "class beats node" in SUPPORT.md), linked bindings were typed only when `sh:class` was present (`sh:node` links emitted no `rdf:type` at all), and several spec-legal combinations rejected without guidance. Spec baseline: every constraint value is an individual constraint and all conjoin (SHACL Core §5); multiple `sh:class` values intersect while the SHACL 1.2 list form unions (§7.1.1); multiple `sh:node` values conjoin (§7.8.1).

## Decision

**Role split.** `sh:node` selects the linked shape — the GraphQL target type. `sh:class` types the binding — `rdf:type` constraints on the linked values, granular and conjunctive. The full dispatch:

| Property carries | GraphQL target | `rdf:type` emission |
|---|---|---|
| `sh:node S` | S | S's class, if S is class-indexed (`sh:targetClass` / implicit class target) |
| `sh:node S` + `sh:class C` (one or more) | S | explicit classes **replace** the implicit (dedupe when equal); one triple each — conjunction |
| `sh:class C` alone | shape targeting C (or synthetic, ADR-0004) | C's triple |
| `sh:class C, C2` (no `sh:node`) | — | reject loudly, with guidance to add `sh:node` |
| `sh:class ( A B )` list + `sh:node S` | S | **union constraint**: values-in disjunction over A, B (`VALUES`-lowered) |
| multiple `sh:node` | — | reject loudly (conjoined node targets resolve to no single type) |

**Every rejected combination teaches the model** — error messages name the shape, the field, and the remedy ("multiple `sh:class` values intersect but name no shape — add `sh:node` to select the target").

**Typing narrows.** Typing a binding from the target's class excludes values that conform structurally but carry no `rdf:type` — a narrowing in the same documented family as `sh:targetClass`'s plain-triple lowering (no `rdfs:subClassOf*` closure). This is a deliberate behavior change for existing graphs: typed retrieval by default, in exchange for `sh:node`-to-a-class-targeted-shape becoming *identical in effect* to `sh:class` — the interchangeability that made the two operators hard to tell apart disappears.

## Consequences

- Intersection (multiple `sh:class` triples) is lowerable as conjunctive triples but never selects the target — GraphQL has no intersection types; the shape always comes from `sh:node`
- Parse pass 2 stops deriving `value_shape_iri` from `value_class` (the overwrite that implemented "class beats node"); Shape IR grows plural class constraints to mirror the shapes graph (ADR-0004 mirror principle)
- SUPPORT.md rows for `sh:class`, `sh:node`-on-property-shapes rewrite when the code lands; changelog carries the narrowing as a behavior change
