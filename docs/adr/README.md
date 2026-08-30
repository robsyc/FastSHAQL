# ADR index

Architecture decision records: the **why** — decision, trade-off, alternatives rejected. Code, tests, and the [support matrix](../SUPPORT.md) are the source of truth for the *what* and the *which*.

## Conventions

- Every record begins with an H1 `# ADR-NNNN — Title`, followed by a `Status:` line.
- Status vocabulary is exactly: **Active** (in force, shipped), **Active (provisional)** (in force, pending later evaluation), **Proposed** (in design, not yet shipped) and **Superseded** (replaced by a newer ADR; zero today).
- No dates or verbose amendment history — git is the record. Rewrite instead of only appending.
- Recommended body structure: Context / Decision / Consequences.


| ADR                                              | Title                                     | Summary                                                                                     | Status               |
| ------------------------------------------------ | ----------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------- |
| [0001](0001-core-adapter-split.md)               | Core/Adapter split                        | Structural (subpackages), not abstract; three seams carry the boundary                      | Active               |
| [0002](0002-graphql-core-primary-output.md)      | graphql-core schema as primary output     | Directly executable `GraphQLSchema`; Strawberry an optional consumer                        | Active               |
| [0003](0003-enforced-module-boundaries.md)       | Enforced module boundaries (tach)         | Fine-grained module DAG gates the import graph; three pinned public seams                   | Active               |
| [0004](0004-shape-ir-vocabulary.md)              | Shape IR vocabulary and classification    | IR mirrors the shapes graph; classification on two axes, `value_type` × `source`            | Active               |
| [0005](0005-node-shape-inheritance.md)           | Node shape inheritance                    | Field-only, flattened at parse, cycles reject, own-beats-inherited override                 | Active               |
| [0006](0006-shacl-in-enums.md)                   | `sh:in` → GraphQL enums                   | Overlay classification, term-kind discrimination, collision numeric suffixes                | Active               |
| [0007](0007-description-language-selection.md)   | Parse-time description language selection | Frozen at parse; `en` default with `description_language=`; diverges from query chain       | Active               |
| [0008](0008-schema-visibility.md)                | Schema visibility                         | `graphql:Schema` container, closed-world, subclass-closed class publishing                  | Active               |
| [0009](0009-composable-filters-and-promotion.md) | Composable filters and promotion          | Hard filters via promotion; typed expression AST; root vs EXISTS dispatch contexts          | Active               |
| [0010](0010-entity-pagination.md)                | Entity pagination                         | Inner DISTINCT-iri sub-SELECT; membership conditions live inside it                         | Active               |
| [0011](0011-query-context-and-graph-scoping.md)  | QueryContext and graph scoping            | One frozen request context; `FROM`-only read scope; `write_graph` reserved                  | Active               |
| [0012](0012-language-preference-chains.md)       | Language preference chains                | Strict precedence, no implicit terminals; string-union untagged exception                   | Active               |
| [0013](0013-ast-driven-translation.md)           | AST-driven translation                    | Selection-AST walk into a composite pattern tree; scoped variable allocation                | Active               |
| [0014](0014-single-query-relationships.md)       | Single-query relationships                | One SELECT with nested OPTIONALs; documented pivot path to batched loads                    | Active               |
| [0015](0015-derived-fields-node-expressions.md)  | Derived fields and node expressions       | Merge-not-sub-SELECT (portability finding); `NodeExprIR` closed sum; named deviations       | Active               |
| [0016](0016-derived-targets.md)                  | Derived targets                           | `sh:targetNode` expressions; one declaration per shape; `instancesOf` promoted              | Active               |
| [0017](0017-sparql-injection-safety.md)          | SPARQL injection safety                   | Typed AST + one term-render chokepoint; trusted shapes graph vs untrusted operation         | Active               |
| [0018](0018-async-execution-and-extras.md)       | Async execution and extras                | Async at the I/O spine only; httpx extra with caller-owned client                           | Active (provisional) |
| [0019](0019-http-adapters-envelope-orjson.md)    | HTTP adapters, envelope, and orjson       | Hand-rolled adapters, no server library; POST-only always-200 envelope; orjson at two seams | Active               |
| [0020](0020-read-only-scope.md)                  | Read-only scope                           | Mutations/validation reversed; translator, not validator                                    | Active               |
| [0021](0021-declarative-fixture-testing.md)      | Declarative fixture testing               | Five tiers as contracts; explicit registries + drift guards; cases vs scenarios             | Active               |
| [0022](0022-evaluation-harness.md)               | Evaluation harness                        | Parity-first, order-independent comparison; `StoreSession`-pluggable; report-only perf      | Active               |
| [0023](0023-package-release-and-ci.md)           | Package release and CI                    | Tag-triggered attested OIDC publish; release notes extracted from CHANGELOG.md              | Active               |


