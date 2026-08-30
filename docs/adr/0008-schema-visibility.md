# ADR-0008 — Schema visibility

**Status:** Active

## Context

A shapes graph must be able to declare which shapes are published for a given API view — visibility is a property of (schema, shape), never intrinsic to the shape.

## Decision

**Schema-container model.** Visibility is read from a `graphql:Schema` resource in the shapes graph holding `graphql:publicShape` / `protectedShape` / `privateShape` / `publicClass` / `protectedClass` declarations — not a per-shape attribute. The same shapes graph may declare multiple schemas, each a different API view.

**Zero or one schema.** No `graphql:Schema` present → every targeted shape is public (backward compatible, existing fixtures unchanged). Exactly one → resolve visibility against it. More than one → raise; multi-schema-per-graph is deferred (the map would need a schema dimension).

**Three states, excluded wins.** PUBLIC (root query field + reachable), PROTECTED (reachable via relationship traversal only, no root field), EXCLUDED (not built at all — no object, filter, or enum type). `graphql:privateShape` overrides public/protected declarations on the same shape.

**Closed-world.** When a schema exists, any shape it does not mention is EXCLUDED. A relationship on a non-excluded shape whose target is a *named, declared* excluded shape raises at parse — declare the target public or protected. Synthetic shapes (parser artifacts for untargeted `sh:class`, ADR-0004) are exempt: they register as reachable whenever referenced. A `publicShape` on a shape with no target class warns and degrades to protected — no root field is possible without a target.

**Class-keyed publishing via subclass closure.** `publicClass` / `protectedClass` resolve shapes whose target class is the named class or any transitive `rdfs:subClassOf` descendant.

Consumption is narrow: schema building emits root fields for public targeted shapes and registers object types for public + protected; translation and the converter are unchanged — relationship traversal resolves regardless of the target's visibility (the type exists because the closed-world check did not raise). The one other `graphql:` term read is `graphql:publicNamespace`: parsed and ignored with a warning — Recognised-and-inert, no schema effect.

## Considered options

- **Per-shape shortcut** (treat `graphql:publicShape` as a self-referential flag): rejected — incompatible with shapes graphs that author visibility against the Schema container; cannot express private overrides or class-keyed publishing
- **Open-world / reachable-by-default** (undeclared → protected-equivalent): rejected — a published schema is a contract; silent reachability violates the loud-error philosophy, and the no-schema case already provides "ship everything"
- **Visibility field on `NodeShapeIR`**: rejected — visibility is declared by the Schema container, not the shape's own triples; storing it on the IR would erode the mirror principle (ADR-0004) and recur for every future cross-cutting concern
