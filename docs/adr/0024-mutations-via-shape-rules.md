# ADR-0024 — Mutations via shape-attached rules (or SPARQL templates)

**Status:** Proposed

## Context

ADR-0020 reverted a CRUD mutation surface and left a revisit lesson: writes demand staged-transaction control, not per-field validation. The SHACL 1.2 rules family — the **Inference Rules** spec (`sh:rule` shape rules, executed per conforming target node with `$this` pre-bound; snapshot `references/shacl12/inference-rules.md`) and its sibling **SPARQL-RL (SRL)** text-syntax language (no shape linkage; snapshot `references/shacl12/rules.md`) — plus prior art (TopBraid, GraphDB, Ontotext SO: none couple shapes-as-interface with rules-as-process). Prior art caps out at single-entity CRUD once relationships enter.

The differentiating use case is the **process contract**: a mutation whose effect crosses multiple nodes — minting entities, linking references, deriving values — as one governed unit. Single-entity CRUD without traversal and without SHACL-conformance-guarantees (Create, Update, AddTo, Delete) is tractable without rules.

Another candidate approach is to use SPARQL templates per https://www.datashapes.org/templates.html -- a minimal vocabulary but one that looks promising.

## Decision (candidate design)

- **Commands, not records.** A mutation is a named shape rule/construct template; the unit of mutation is the rule, not the shape. TopBraid-style CRUD may join as a second surface by v1.0.
- **Request-resource inputs** *(provisional)*. Input objects are typed by a dedicated request shape's properties (or a sh:Parameter on a template); the mutation materializes a request node and rules construct the entity graph from it (the Input→Answer idiom).
- **Translator, not engine.** fastshaql compiles rules to SPARQL; the store executes; fastshaql processes results. No fixpoint iteration, no in-library conformance checking, no background materialization service.
- **The author owns correctness.** No in-library validation and no store-validation dependency; the rule process (its WHERE clause; `sh:condition` when that tier lands) encodes the guards.
- **Phased by dependency.** Consolidation subset + triples-response land first; dry-run mutations (return the CONSTRUCT triples) second; commit (`INSERT…WHERE` against `write_graph`) last. However, the template-based approach may be much easier to implement and test, so it may be the first tier.
- **Closed-by-default write visibility** *(provisional)*. Mutations appear only for shapes declared mutating in the `graphql:Schema` container (ADR-0008 model); no declaration → no mutation, even with rules present. Strong visibility control is important.
- **Per-mutation atomicity + `dryRun` flag.** GraphQL's serial mutation root fields give one transaction unit per field.
