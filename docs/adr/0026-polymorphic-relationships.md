# ADR-0026 — Polymorphic relationships (`sh:or` over `sh:class`/`sh:node` → union types)

**Status:** Proposed (update this ADR and related docs when the implementation lands)

> NOTE: This ADR is a bit too wordy and could be simplified and trimmed down.

## Context

Only the datatype-only `sh:or` is consumed today (normalised into `datatypes`, ADR-0012); every other `sh:or` — including the spec's own property-shape example `sh:or ( [sh:class ex:Address] … )` (Core §7.7.3) — is parse-recognized-and-inert, so a field linking heterogeneous object types (an `Article.block` pointing at a paragraph, an image, or a table) never reaches the schema. GraphQL fragments are rejected outright in translation. Prior art converges: TopBraid and GraphDB generate **unions** from `sh:or`; **interfaces** come from inheritance, never from `sh:or` (PostGraphile's shared-fields rule requires explicit user declaration); graphql-to-sparql.js lowers inline fragments as type-guarded OPTIONAL lanes; shape-to-query lowers `sh:or` as UNION branches. Prototypes validated the mechanics with graphql-core 3.2 and rdflib.

## Decision

**Recognition.** A polymorphic relationship arises from `sh:or` whose members each carry exactly one value constraint — `sh:class IRI` or `sh:node IRI`; members may be mixed. The `sh:class` **list form** (`sh:class ( A B )`, SHACL 1.2 §7.1.1 union) normalises into the same lane as `sh:or` class members, exactly as the two datatype syntaxes normalise today. Heterogeneous members (datatype + class in one `sh:or`) **reject loudly** — GraphQL unions cannot contain scalars; members carrying any other constraint (`sh:pattern`, `sh:minCount`, …) stay parse-recognized-and-inert (validator territory). Direct shape-IRI members (`sh:or ( ex:ShapeA ex:ShapeB )`) stay inert — detection needs registry-aware parsing; defer until demand.

**Member discriminator.** Every member must resolve to a class — an `sh:class` member has one trivially; an `sh:node` member needs its target shape class-indexed (ADR-0025). The class is the lane guard and the source of the `__typename` stamp. A member whose target has only a derived target rejects loudly at registry build, naming the member and the remedy. Duplicate members (same shape, or two shapes resolving the same class) reject loudly. Single-target relationships are exempt — `sh:node` to a class-less shape remains supported (ADR-0025 row 1 emits nothing).

**Union type.** The schema derives a `GraphQLUnionType` over the member shapes' object types. The converter stamps each row's concrete type as a `__typename` key on the entity dict; graphql-core's *default* type resolver reads it and `default_field_resolver` already works inside member selections — no custom resolvers. Naming: `{ParentType}{FieldName}` (`Article.block` → `ArticleBlock`), numeric suffix on collision with a real shape name (ADR-0006 precedent), one union per (parent, field) — no cross-field dedupe by member-set, no user override in v1 (SHACL offers no clean anchor for a union name). This follows the industry *convention* (deterministic, field-scoped, collision-escaped — Contentful field-wrappers, SOML/Strapi member-joins) without an exact precedent; TopBraid's auto-union name is undocumented.

**Overlap and membership.** A value conforming to several members resolves to exactly one GraphQL type: **member-order priority** — the first declared member whose lane matched stamps the row; authors control specificity by ordering (mirrors value-type precedence and enum-collision suffixes). Values matching *no* member are dropped — `sh:or`/`sh:class` are membership constraints, so this is the spec-correct reading, documented beside the plain-triple narrowing family.

**Lowering (hybrid, revisitable).** One emission of the link path, then a `VALUES ?member { A B … }` membership guard binding the discriminator, then one OPTIONAL lane per member carrying its type triple and branch field patterns. This needs **no new SPARQL AST nodes** (`ValuesPattern` + `OptionalPattern` suffice), never repeats a complex `sh:path` per branch (the UNION-branch alternative would), and keeps row multiplication bounded by member-types-per-child — merged by the existing group-by-child-var conversion. Required/optional join semantics are unchanged (`wrap_if_unbound` restores child-less parents). If the evaluation harness (ADR-0022) later shows engines prefer UNION shapes, only `joins.py` changes — the choice is translation-internal; IR, registry, schema, and stamping do not move.

**Boundaries.** Filters reaching into a polymorphic field reject loudly at translation until the filter slice designs member-keyed inputs and the **type-discrimination operator** (inline fragments select fields, never members — "only Employees" is a `where` concern). Derived unions (`sh:values` + union targets) stay inert-with-warning: expressible-but-unbuilt is never a loud rejection (the spec-first philosophy: users never revise shapes to fit the library). Inline fragments become supported; **named fragment spreads keep today's rejection** (they need operation-level definitions plumbed through `translate_query` — follow-up, resolvable by pre-translation spread inlining). Visibility is strictest-wins: a private member inside a published union rejects loudly at registry build (unions are introspectable).

## Consequences

- Interfaces remain a future derivation from node-shape inheritance (ADR-0005 parents → candidate interface), not from common-field detection — the ROADMAP item is re-pointed accordingly
- The converter gains per-row type discrimination (today purely static) — the one structural change to ADR-0014's row contract
- `sh:in` overlays on relationships stay read-ignored with a warning (ADR-0006) — instance-restricted relationships are a designed follow-up
- SUPPORT.md `sh:or` row splits: the datatype-only interpretation gains the polymorphic sibling
