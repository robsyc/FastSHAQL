# ADR-0015 — Derived fields and node expressions

**Status:** Active

## Context

A Property carrying `sh:values` is a **derived field**: its values are computed at query time by a SHACL node expression, not read from asserted triples. Translation emits the expression where the `?subject sh:path ?var` triple would sit. This record pins the boundary decisions and the IR/dispatcher architecture; the operator inventory and interpretation detail live in the [support matrix](../SUPPORT.md).

## Boundary decisions

- **Replace, not union.** The spec unions asserted-path triples with `sh:values` outputs; fastshaql drops the asserted triples. No real shapes graph asserts both. The widening is pre-staged — a renderer-trivial `UnionPattern` at the two splice sites, with the converter's existing dedup already set-faithful — and deferred on zero demand, not on feasibility.
- **Merge, not verbatim sub-SELECT** — the portability finding below is the why.
- **Bind-then-filter, one mode.** Every derived field binds its expression to the value variable once (`BIND`); filters compare that variable. The expression is evaluated once even when the field is both selected and filtered — inlining into the `FILTER` would double-evaluate, worst for `EXISTS` booleans — and no case requires it (a `FILTER` sees variables bound by a `BIND` in the same group).
- **Key-parameter model.** An expression blank node carries exactly one function-identifying key parameter plus only that function's declared parameters; anything else — duplicate keys, a second function, a foreign predicate — rejects loudly. Unsupported functions reject **by name**, naming the carried predicates; SHACL validation-constraint parameters (`sh:minLength`, …) are a different vocabulary position, silently ignored like every other validation constraint.
- **No silent wrong cardinality.** A list-typed derived field on a single-valued arm (expression, constant, `exists`, all-single-branch `if`) rejects at parse, naming the arm — only multi-valued arms can honour list cardinality, and a silent ≤1-element list violates the declared shape.

## The portability finding (why merge)

SPARQL makes a sub-SELECT a scope barrier, so a verbatim `sh:select` sub-SELECT relies on its inner focus variable correlating with the outer row — a non-standard extension that rdflib performs and strict endpoints do not. Confirmed empirically (5-entity dataset, `CONCAT` and `COUNT` derivations):

| Emission | rdflib | GraphDB/RDF4J |
|---|---|---|
| verbatim sub-SELECT, focus var not projected | 5 rows (correct — rdflib correlates) | **25 rows = 5×5 Cartesian** |
| merged body | 5 rows (correct) | 5 rows (correct) |
| sub-SELECT projecting the focus var | 5 rows (correct) | 5 rows (correct) |

The trap is concrete: the rdflib test suite passes while a strict endpoint silently returns wrong values. Merging the author's WHERE body into the enclosing query needs no parse of the SELECT head and joins on the outer focus variable exactly as the single-query relationship strategy (ADR-0014) already does. The projecting sub-SELECT form is also portable — but it requires rewriting the author's projection, which is why aggregates and top-N bodies (a genuine head-rewrite) are deferred rather than silently broken.

## Architecture

**`NodeExprIR` — a closed typed union** (frozen dataclasses plus shared structural predicates), mirroring the existing path/expression/pattern precedent. New operators are new arms; an open plugin registry was rejected — the codebase has no precedent for one, and static exhaustiveness is the safety property.

**Dispatcher.** `translate_node_expr(ir, focus_term, value_var)` matches over the IR and returns graph patterns. `focus_term` is a structural term — the subject variable, or the shape-IRI constant at target position (ADR-0016) — never a string-substitution site at the dispatcher level. `value_var` is caller-allocated (the selection walk, promotion, or EXISTS context owns it). Adding an operator never touches the consumer. `$this` substitution is confined to the two SPARQL-text handlers and is **code-position-only**: string literals, IRIREFs, and comments are left untouched — a `$this` inside a string is a literal value, not a focus-node reference.

**Trusted text nodes.** `RawGraphPattern` / `RawSparqlExpr` carry author SPARQL verbatim — the only nodes whose `render()` returns a stored string. Author SPARQL is trusted content (ADR-0017); the sole runtime substitution into it is the focus variable, which is fastshaql-generated, never client-controlled. The explicitly-raw names are the audit signal that this is trusted-text-by-design, not a missing-escaping bug.

## Named deviations

| Deviation | One-line reason |
|---|---|
| Replace, not union | no real graph asserts both; union pre-staged |
| Merge, not sub-SELECT | portability (finding above) |
| Aggregate / top-N `sh:select` bodies reject | portable emission needs a projection head-rewrite |
| `shnex:if` conditions restricted to statically single-valued expressions | a per-row-varying condition would take different branches within one entity |
| `shnex:if` failure routes to else, not failure | "failure" has no clean lowering; else-on-error is what SPARQL FILTER error semantics yield |
| `shnex:pathValues` targeting a derived property rejects | recursive inlining at an arbitrary pattern position is undesigned |
| `filterShape` `sh:property` conjuncts are existential | SHACL conformance is universal; a conformance-exact double-negation lowering remains a future option |
| `sh:class` conjuncts join plain `rdf:type` | "we join, we don't validate" — no subclass entailment |
| `filterShape` takes inline blank-node shapes only | a named reference would need registry resolution at node-expression parse time |
| `sh:defaultValue` scalar-only | the spec gates on set-emptiness; faithful set-level gating needs deferred aggregate machinery |
