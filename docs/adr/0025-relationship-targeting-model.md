# ADR-0025 — Relationship targeting: `sh:node` names the target, `sh:class` types the binding

**Status:** Proposed (update this ADR and related docs when the implementation lands)

## Context

`sh:node` and `sh:class` both make a Property a relationship (ADR-0004), but their roles overlapped confusingly: `sh:class` resolved the target shape and silently overwrote any co-present `sh:node` (documented as "class beats node" in SUPPORT.md), linked bindings were typed only when `sh:class` was present (`sh:node` links emitted no `rdf:type` at all), and several spec-legal combinations rejected without guidance. Spec baseline: every constraint value is an individual constraint and all conjoin (SHACL Core §5); multiple `sh:class` values intersect while the SHACL 1.2 list form unions (§7.1.1); multiple `sh:node` values conjoin (§7.8.1).

The typing emissions had also drifted from the spec into an internal split: `sh:class` bindings, explicit `sh:targetClass` roots, and `sh:class` inside `shnex:filterShape` matched plain `rdf:type` triples, while `shnex:instancesOf` and implicit class targets closed over `rdfs:subClassOf`. The spec has only one semantics — all of these are defined via **SHACL instance**, which includes superclasses (Core §1.1; `sh:targetClass` §3.1.3.2, `sh:class` §7.1.1, implicit targets §3.1.3.3, node-expr §4.5.1; the SPARQL appendices spell it `rdf:type/rdfs:subClassOf*`).

## Decision

**Role split.** `sh:node` selects the linked shape — the GraphQL target type. `sh:class` types the binding — `rdf:type` constraints on the linked values, granular and conjunctive. The full dispatch:

| Property carries | GraphQL target | `rdf:type` emission |
|---|---|---|
| `sh:node S` | S | S's indexed class, if S is class-indexed (`sh:targetClass` / implicit class target) |
| `sh:node S` + `sh:class C` (one or more) | S | explicit classes **replace** the implicit (dedupe when equal); one path each — conjunction |
| `sh:class C` alone | shape targeting C (or synthetic, ADR-0004) | C's path |
| `sh:class C, C2` (no `sh:node`) | — | reject loudly, with guidance to add `sh:node` |
| `sh:class ( A B )` list + `sh:node S` | S | **union constraint**: values-in disjunction over A, B (`VALUES`-lowered; ships with ADR-0026 — shares its VALUES machinery) |
| multiple `sh:node` | — | reject loudly (conjoined node targets resolve to no single type) |

**Every rejected combination teaches the model** — error messages name the shape, the field, and the remedy ("multiple `sh:class` values intersect but name no shape — add `sh:node` to select the target").

**Typing closes (SHACL-instance semantics).** Every typing emission — binding typing (all rows above), explicit `sh:targetClass` roots, and `sh:class` constraints inside `shnex:filterShape` — lowers as the SHACL-instance path `rdf:type/rdfs:subClassOf*`, identical in form to the existing `shnex:instancesOf` lowering (ADR-0016). The remaining narrowing is **graph visibility, not match form**: subclass triples must be present in the queried data graphs (Core §6.3 observes they often live in shapes graphs; reading them from there stays the ADR-0016 deviation). This is a deliberate behavior change for existing graphs: values typed only through a subclass chain now match — and untyped values still drop, as before. Typing a binding from the target's class (`sh:node`-to-a-class-targeted-shape) becomes *identical in effect* to `sh:class` — the interchangeability that made the two operators hard to tell apart disappears.

## Consequences

- Intersection (multiple `sh:class` values) is lowerable as conjunctive paths but never selects the target — GraphQL has no intersection types; the shape always comes from `sh:node`
- Parse pass 2 stops deriving `value_shape_iri` from `value_class` (the overwrite that implemented "class beats node"); Shape IR grows plural class constraints to mirror the shapes graph (ADR-0004 mirror principle)
- Typing unification retires the last plain-`rdf:type` emissions: explicit `sh:targetClass` roots and `shnex:filterShape` class constraints join bindings on the SHACL-instance path, making root and link semantics uniform per class; `shnex:instancesOf` lowering is unchanged (it already closed)
- SUPPORT.md rows for `sh:class`, `sh:node`-on-property-shapes, and `sh:targetClass` rewrite when the code lands; the changelog carries both behavior changes — typing closes over `rdfs:subClassOf`, and `sh:node` links to class-indexed shapes become typed
