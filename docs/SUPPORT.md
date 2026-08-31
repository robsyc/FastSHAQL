# fastshaql support matrix

How fastshaql interprets the W3C SHACL 1.2 and SPARQL 1.2 specifications, written for readers who already know them: one row per spec term, its disposition, and its GraphQL/SPARQL effect — deviations are named, not explained (the reasoning lives in the linked ADRs). The code and the W3C specs are the single source of truth; when this matrix and the code disagree, the code wins — fix the matrix. Spec snapshots: [references/shacl12/](references/shacl12/) and [references/sparql12/](references/sparql12/).

Dispositions:

- **Supported** — behaves as the spec defines it.
- **Supported-with-interpretation** — works, with a named narrowing or reinterpretation.
- **Rejected-loudly** — raises at parse or translation time, naming the offending term or shape.
- **Recognised-and-inert** — parses without error; no schema or query effect.
- **Deferred** — not implemented; tracked on the [roadmap](ROADMAP.md) or in an ADR's deferred list.

## 1. SHACL Core

fastshaql recognises shapes only by explicit typing — subjects of `rdf:type sh:NodeShape` or `sh:ShapeClass`. The spec also recognises shapes structurally (§3.1: target declarations, parameter triples, values of shape-expecting parameters), so an untyped shape carrying declarations is a spec shape fastshaql never sees. Blank-node shapes are skipped with a warning (not addressable by IRI).

### Shapes and property shapes

| Term | Disposition | Interpretation |
|---|---|---|
| Named `sh:NodeShape` (§3.2) | Supported | One GraphQL type per shape |
| `sh:property` (§7.8.2) | Supported | Inline blank-node Properties get synthesised IRIs; duplicate field names within a shape dedupe (first wins, warning); a standalone named `sh:PropertyShape` is never parsed |
| `sh:deactivated` (§3.1.6) | Supported-with-interpretation | Constant `true` only — no type, no field. The 1.2 generalisations (node-expression values, reifier-based per-constraint deactivation) are never read; non-`true` values leave the shape active, silently; multiple values reject (at most one, §3.1.6) |
| `sh:severity` (§3.1.4) / `sh:message` (§3.1.5) | Recognised-and-inert | Never read — validation-report vocabulary; no schema or query effect |
| `sh:node` on node shapes (§7.8.1) | Supported-with-interpretation | Read as field-only inheritance: a reinterpretation of the spec's conjunction semantics (the spec's own analogy is `rdfs:subClassOf`); flattened at parse, transitive, multiple parents merge in IRI order ([ADR-0005](adr/0005-node-shape-inheritance.md)) |
| Inherited-field override | Supported-with-interpretation | The child's whole property shape replaces the inherited one wholesale, with a warning naming both property shapes |
| Inheritance failure cases | Rejected-loudly | Two parents defining the same field name (child silent), cycles (recursion is spec-undefined, §6.5.3), blank-node parents, and unknown or deactivated parents all raise |

### Property paths (§4)

| Term | Disposition | Interpretation |
|---|---|---|
| Predicate path (§4.1) | Supported | Field name defaults to the predicate's local name; rendered `<iri>` (`a` for `rdf:type`) |
| Inverse path (§4.4) | Supported | Rendered `^`; composite operands parenthesised per SPARQL `PathPrimary` |
| Sequence path (§4.2) | Supported | Rendered `/`; well-formed SHACL list and must carry ≥2 members (§4.2); an empty list *is* `rdf:nil` (an IRI) and rejects as an empty list |
| Alternative path (§4.3) | Supported | Rendered `\|`; the operand list is walked strictly and must carry ≥2 members (§4.3) — including the empty list |
| `sh:zeroOrMorePath` / `sh:oneOrMorePath` (§4.5–4.6) | Supported | Rendered `*` / `+` |
| `sh:zeroOrOnePath` (§4.7) | Supported | Rendered `?` |
| Path acyclicity (§4) | Rejected-loudly | A blank-node path referencing itself rejects with a named error (§4 requires acyclic paths); a cyclic `rdf:rest` chain rejects inside the strict list walk |
| Non-predicate path without `sh:codeIdentifier` | Rejected-loudly | The spec strongly recommends one for complex paths (§8.4); fastshaql requires it — there is no derivable field name |
| Missing or unrecognised `sh:path` | Rejected-loudly | Both errors name the property-shape node itself — unrecognised structures include literals under `sh:path`; for inline properties the id is the raw blank-node id, since the error fires before IRI synthesis; multiple `sh:path` values reject (§3.3: at most one) |

`NegatedPropertySet` is not a SHACL term (1.1 or 1.2 — §4.1–§4.7 is the whole grammar), so a negated structure is simply an unrecognised `sh:path` and rejects; there is nothing to defer. The same full path grammar parses `shnex:pathValues` operands and `shnex:filterShape` conjunct paths.

### Targets (§3.1.3)

| Term | Disposition | Interpretation |
|---|---|---|
| `sh:targetClass` (§3.1.3.2) | Supported-with-interpretation | Lowers to a direct `rdf:type` triple — the spec's SHACL-instance closure (`rdf:type` + `rdfs:subClassOf*`, subclass instances included) is not applied; non-IRI values reject; a class targeted by two shapes rejects at registry build |
| `sh:targetNode` (§3.1.3.1) | Supported-with-interpretation | Exactly one node expression (the spec unions all values), parsed by the shared node-expression grammar; the shape IRI is the focus term; a literal-yielding target is accepted by design and can never match ([ADR-0016](adr/0016-derived-targets.md)) |
| Implicit class target (§3.1.3.3) | Supported-with-interpretation | `sh:ShapeClass` alone, or `rdfs:Class` alongside `sh:NodeShape`, targets the shape's own IRI, lowered `rdf:type/rdfs:subClassOf*`; recognition is direct typing only — no SHACL-type closure in the shapes graph; `rdfs:Class` alone (untyped as a shape) and `owl:Class` are never enumerated |
| `sh:targetSubjectsOf` / `sh:targetObjectsOf` (§3.1.3.4–5) | Rejected-loudly | Named by full IRI, even alongside a valid supported target |
| `sh:targetWhere` (§3.1.3.6) | Rejected-loudly | 1.2 conformance-based targets are not statically enumerable from the shapes graph |
| `sh:shape` (§3.1.3.7) | Rejected-loudly | A `sh:shape` triple in the shapes graph rejects with a data-graph hint; the spec's actual data-graph declarations are invisible to a shapes-graph parser, so such a shape simply behaves as untargeted |
| Any other `sh:target*` predicate | Rejected-loudly | SHACL-namespace scan on the local-name prefix `target`, case-insensitive — typos, case variants, future or unvendored additions |
| Multiple or mixed declarations | Rejected-loudly | Exactly one target declaration per shape; the spec unions all declarations (§3.1.3) — a documented narrowing ([ADR-0016](adr/0016-derived-targets.md)) |
| Union of multiple declarations | Deferred | [roadmap](ROADMAP.md) |
| Target-less shape | Recognised-and-inert | Parses; no root query field is published; a public shape demotes to protected with a warning; translating such a root raises |

### Constraint vocabulary (§7)

fastshaql consumes a schema subset of §7 as GraphQL typing. Value-type precedence is relationship > enum > scalar; overlaps are resolved by that order, not rejected.

| Term | Disposition | Interpretation |
|---|---|---|
| `sh:class` (§7.1.1) | Supported-with-interpretation | Single IRI → relationship typing; resolves to a targeting shape, else a synthetic protected shape is created with a warning; multiple IRI values reject (the spec ANDs them), literal values reject as ill-formed, and the list form rejects as unsupported (below); when both are present `sh:class` beats `sh:node` |
| `sh:class` list form (1.2 union) | Rejected-loudly | Union semantics are not lowered at property level — the list (including the empty list, the vacuous union) rejects by name; the list form is consumed inside `shnex:filterShape` (§2) |
| `sh:node` on property shapes (§7.8.1) | Supported-with-interpretation | Relationship typing by sole IRI; multiple values reject (the spec conjoins them), blank-node values reject (inline node shapes — matching the node-shape host, above), and literal values reject as ill-formed; unknown IRI targets raise at schema build (registry), not parse |
| `sh:datatype` (§7.1.2) | Supported | Single IRI or 1.2 list form; multiple triples (spec: at most one), empty lists, malformed lists, and non-IRI members reject loudly; unknown IRIs fall back to `String` |
| String-union Property | Supported | `xsd:string` ∪ `rdf:langString` ∪ `rdf:dirLangString` — the only multi-entry set permitted (any other rejects); `String` output; the language chain applies with an implicit untagged terminal (§3) |
| `sh:or` (§7.7.3) | Supported-with-interpretation | The datatype-only form (each member exactly `sh:datatype` with one IRI) normalises into the datatype tuple; any other `sh:or` warns once and is inert; `sh:datatype` + `sh:or` together and multiple `sh:or` values reject |
| `sh:in` (§7.9.3) | Supported-with-interpretation | Homogeneous literal or IRI lists become enums; mixed lists and blank-node members reject (the spec permits mixed — a narrowing); duplicates warn and get distinct names mapping to one value; an empty list excludes the field with a warning (no values are allowed — the `sh:deactivated` reading, §3.1.6); relationship overlays are ignored with a warning; literals are never cross-checked against `sh:datatype` |
| `sh:minCount` / `sh:maxCount` (§7.2.1–2) | Supported-with-interpretation | FieldKind: `minCount >= 1` → required, `maxCount == 1` → scalar else list; values must be single `xsd:integer` literals — anything else, and extra values, reject (§7.2); `maxCount` below 1 (zero capacity — the property can never hold values) excludes the field with a warning, the `sh:deactivated` reading; a defaulted field is non-null at any `minCount` |
| The other ~31 §7 components | Recognised-and-inert | Uniform boundary: never read at shape level — no warning, no schema or query effect. Covers `sh:nodeKind`, `sh:pattern`, the string/numeric range groups, the property-pair group, `sh:languageIn`, `sh:uniqueLang`, `sh:closed`, `sh:hasValue`, the logical group (`sh:and`/`sh:not`/`sh:xone`), the 1.2 list group, `sh:qualifiedValue*`, `sh:someValue`, `sh:reifierShape`, `sh:rootClass`, `sh:uniqueValuesFor`. Exception: inside `shnex:filterShape` a lowerable subset is consumed and everything else rejects loudly there (§2) |

Datatype → scalar mapping (the code-stated 23-entry set):

| Datatype | Output scalar | Filter input |
|---|---|---|
| `xsd:string`, `xsd:normalizedString`, `xsd:token`, `xsd:anyURI`, `rdf:langString` | `String` | `StringFilter` |
| `xsd:boolean` | `Boolean` | `BooleanFilter` |
| `xsd:integer`, `xsd:int`, `xsd:short`, `xsd:byte`, `xsd:long`, `xsd:unsignedInt` | `Int` | `IntFilter` |
| `xsd:decimal`, `xsd:float`, `xsd:double` | `Float` | `FloatFilter` |
| `xsd:date`, `xsd:dateTime`, `xsd:time`, `xsd:dateTimeStamp`, `xsd:duration`, `xsd:dayTimeDuration`, `xsd:yearMonthDuration`, `xsd:gYear` | `String` | `DateTimeFilter` |

Unknown or missing datatypes fall back to `String`/`StringFilter`; `rdf:dirLangString` is covered by that fallback (it is not a table entry) yet counts as a language datatype in the string-union family.

### Non-validating characteristics (§8)

| Term | Disposition | Interpretation |
|---|---|---|
| `sh:codeIdentifier` (§8.4) | Supported | Field and type names (the spec names GraphQL as the use case); predicate-local-name fallback for predicate paths; validated at parse — an `xsd:string` literal matching `^[a-zA-Z_][a-zA-Z0-9_]*$`, else a named rejection (§8.4's grammar is the GraphQL name grammar); at most one value — multiples reject |
| `sh:name` / `sh:description` (§8.1) | Supported | Field descriptions on property shapes (`sh:description` first, then `sh:name`); unread on node shapes, where the spec says not to use them |
| `rdfs:label` / `rdfs:comment` | Supported | Node-shape descriptions (`rdfs:comment` first, then `rdfs:label`); per-predicate language selection at parse time — predicate priority beats language ([ADR-0007](adr/0007-description-language-selection.md)) |
| `sh:order` (§8.6), `sh:group` (§8.7), `sh:intent` (§8.2), `sh:agentInstruction` (§8.3), `sh:unit` (§8.5) | Recognised-and-inert | Never read — no schema or query effect |

## 2. SHACL 1.2 node expressions

Hosts (Core §3.3): `sh:values` and `sh:defaultValue` at property level — at most one each, predicate paths only — and `sh:targetNode` at shape level. One shared expression grammar serves all hosts, but per-host boundaries differ: `sh:defaultValue` is scalar-only (multi-valued arms, relationships, list cardinality, missing datatype reject) and non-relationship `sh:values` requires `sh:datatype`.

Value semantics: the spec (§6.8.2) unions path values with `sh:values` output and falls back to `sh:defaultValue` only when both are empty. fastshaql **replaces** the path triple with the derived emission — no real shapes graph asserts both — and lowers the default scalar-only, non-null at any `minCount` (SD-6) ([ADR-0015](adr/0015-derived-fields-node-expressions.md)).

| Function | Disposition | Interpretation |
|---|---|---|
| Constants — IRI / literal (Core §5.1–5.2) | Supported | `BIND(<term> AS ?var)`; node-expression triple terms (node-expr §3.1.3) are not accepted |
| `shnex:ListExpression` (§4.1.3) | Supported | Constants only — spec-exact; `()` is the constant `rdf:nil`, not the empty expression |
| `shnex:pathValues` (+ `shnex:focusNode`, §4.1.4) | Supported-with-interpretation | Full §4 path grammar as operand; `focusNode` must be a constant IRI — anything else rejects loudly (silent row multiplication otherwise) |
| `shnex:exists` (§4.1.5) | Supported | `BIND(EXISTS { … } AS ?v)` — never null, never errors |
| `shnex:if` / `then` / `else` (§4.1.6) | Supported-with-interpretation | Conditions must be statically single-valued — set-valued conditions reject (flat per-row binding could take different branches per row); strict `cond = true`; at least one branch required; an erroring condition takes the else branch (`COALESCE` routing) where the spec fails the expression |
| `shnex:filterShape` (+ `shnex:nodes`, §4.2.5) | Supported-with-interpretation | Lowerable conjuncts: `sh:hasValue`, `sh:class` (IRI or list — union within one value, conjunction across values), `sh:rootClass`, `sh:datatype`, `sh:pattern` + `sh:flags`, the four numeric bounds, `sh:minCount 1` inside `sh:property`, nested `sh:property`; every other predicate except `rdf:type` (tolerated, no conjunct) rejects loudly there (incl. `sh:maxCount`, `sh:deactivated`). Inline blank-node shapes only; `sh:property` conjuncts are existential (SHACL conformance is universal — exact lowering is future work); `sh:class` joins plain `rdf:type` while `sh:rootClass` walks `rdfs:subClassOf*` |
| `shnex:instancesOf` (§4.5.1) | Supported-with-interpretation | Constant folding only (constant IRI or all-IRI list); lowers `rdf:type/rdfs:subClassOf*` reading the queried graphs only — the spec's optional shapes-graph subclass lookup (§6.3) is a named deviation ([ADR-0016](adr/0016-derived-targets.md)) |
| `sh:select` (shacl12-sparql §6.1) | Supported-with-interpretation | Merge-able bodies only: the WHERE body dissolves into the enclosing query, never a verbatim sub-SELECT (portability, [ADR-0015](adr/0015-derived-fields-node-expressions.md)); exactly one projected variable; `DISTINCT`/`REDUCED` head modifiers, head expressions, `SELECT *`, top-level `GROUP BY`/`ORDER BY`/`LIMIT`/`OFFSET`/`HAVING`, and any trailing SPARQL after the WHERE block reject; `SERVICE` is allowed; `$this` substitution is code-position-only (string literals, IRIREFs, comments protected); the Appendix A scan rejects `MINUS`, `AS ?this`, and `VALUES` over `this` (scoped to `this` only) |
| `sh:sparqlExpr` (§6.2) | Supported-with-interpretation | `BIND(expr AS ?var)` at the enclosing scope — a named deviation from the spec's `SELECT ($EXPR$ AS ?result) WHERE {}` wrapper; an erroring expression leaves the variable unbound, as under SPARQL assignment semantics |
| `sh:prefixes` (§2) | Supported-with-interpretation | Direct `sh:declare` on the referenced node only — the spec's `owl:imports`/`owl:versionIRI` traversal is a permanent exclusion; no shapes-graph fallback of any kind (absent `sh:prefixes` means no prefixes); incomplete declarations are silently skipped and duplicate `sh:prefix`/`sh:namespace` values silently pick one; prefix conflicts raise as ill-formed |
| Empty expression `[]` (§4.1.1) | Rejected-loudly | Blank nodes that are subject of no triple reject as empty node expressions |
| All remaining functions | Rejected-loudly | By name, inventory-pinned: the sub-SELECT tier (`shnex:orderBy`, `shnex:limit`, `shnex:offset`), aggregates (`shnex:count`/`min`/`max`/`sum`), `shnex:distinct`/`intersection`/`concat`/`remove`, `shnex:flatMap`/`findFirst`/`matchAll`, `shnex:nodesMatching`/`conformsToShape`, `shnex:var`, `shnex:arg`, `sparql:`* list-parameter functions, and custom functions |

Blank-node functions must follow the key-parameter model (§3.2.1): exactly one key parameter, used once, plus only that function's declared parameters — violations reject loudly.

Named deviations — the full reasoning lives in [ADR-0015](adr/0015-derived-fields-node-expressions.md):

- **Bind-then-filter** — a derived field is `BIND`-bound once at the enclosing scope; filters compare the bound variable (single evaluation, even when selected and filtered).
- **Derived relationships** — `sh:values` + `sh:class`/`sh:node` is a full relationship: nested selection, row grouping, filters (pagination is root-only, §3).
- **Derived enums** — `sh:values` + `sh:in` serialises through the enum NAME mapping; values outside `sh:in` raise at serialisation, naming the value.
- **List cardinality needs a multi-valued arm** — a list-typed field on a single-valued arm rejects at parse; `sh:minCount` on a derived field warns and is ignored for validation but still drives cardinality emission.
- **Derived parse boundary** — `sh:values`/`sh:defaultValue` require a bare predicate `sh:path` (composite paths raise); a non-relationship `sh:values` field requires `sh:datatype` (a string-union set satisfies it).
- **Rule chaining rejected** — `shnex:pathValues` targeting a derived property rejects, at every position a path can occupy in the expression grammar.
- **`filterShape` over `if`** — normalised at parse into `if` over two filtered branches (filtering distributes over branch selection).

`sh:select`/`sh:sparqlExpr` bodies are trusted author content; the only runtime substitution into them is the fastshaql-generated `$this` → focus term ([ADR-0017](adr/0017-sparql-injection-safety.md)).

## 3. SPARQL 1.2

### Dataset (§13)

| Term | Disposition | Interpretation |
|---|---|---|
| `FROM` (§13.2; grammar [9] — top-level only, [10] has no dataset clause) | Supported | One clause per read graph; the default graph becomes the RDF merge of the listed graphs, used in place of the store default ([ADR-0011](adr/0011-query-context-and-graph-scoping.md)) |
| No `FROM` | Supported-with-interpretation | The dataset is store-defined (§13.2) — fastshaql sets no store global; what the default graph contains is the loader's decision |
| `FROM NAMED` / `GRAPH` | Deferred | [roadmap](ROADMAP.md) |
| `write_graph` (a fastshaql `QueryContext` slot, not a spec term) | Rejected-loudly | Reserved for the writes era — translation rejects a set value; reads never consume it |

### Pagination (§15)

| Term | Disposition | Interpretation |
|---|---|---|
| `LIMIT` / `OFFSET` (§15.5 / §15.4; grammar [27]–[29]) | Supported | Either argument wraps an inner `SELECT DISTINCT ?iri … ORDER BY ?iri LIMIT n OFFSET m`; entity-membership conditions sit inside, selection triples outside; `LIMIT 0` is a valid empty page; offset without limit is legal (second alternative of [27]); negative arguments reject |
| `SELECT DISTINCT` (§15.3; production [11]) | Supported | Emitted on the pagination sub-SELECT only; duplicates are eliminated before limit or offset is applied |
| Sub-SELECT ordering | Supported-with-interpretation | The inner `ORDER BY` fixes page membership only; outer row order is engine-defined — spec-consistent, since `ToMultiset` discards sub-SELECT order (§18.3.2.6 applies it; the definition is §18.6). Lists are documented unordered ([ADR-0010](adr/0010-entity-pagination.md)) |
| `totalCount`, nested pagination, keyset, client `orderBy` | Deferred | Client `orderBy` on the [roadmap](ROADMAP.md); the rest in [ADR-0010](adr/0010-entity-pagination.md)'s deferred list |

### Language resolution

| Term | Disposition | Interpretation |
|---|---|---|
| `langMatches` (§17.4.3.11) | Supported | RFC 4647 basic filtering — `"en"` serves `en-US`; sentinels lower to `LANG(?v) = ""` (untagged) and `langMatches(LANG(?v), "*")` (any); exact-tag-only chains are not expressible; emitted only by the chain machinery, never client-exposed |
| Language preference chain | Supported-with-interpretation | Per-step `OPTIONAL` + `BIND(COALESCE(…))`; the first step with a value wins; no implicit terminals, except the untagged terminal appended in string-union space; a required scalar (or one promoted into a filter) additionally emits `FILTER(BOUND(…))`; list fields use one variable under a disjunctive filter; derived and defaulted fields reuse the skeleton with the default as the last `COALESCE` argument; plain literal space ignores the chain entirely; filters compare `STR()` of the resolved value ([ADR-0012](adr/0012-language-preference-chains.md)) |
| `Accept-Language` parsing | Supported | See [ADR-0012](adr/0012-language-preference-chains.md) § *Accept-Language resolution* |
| `sh:languageIn` (Core §7.4.5); per-field `lang` override; `rdf:dirLangString` base-direction matching | Deferred | [roadmap](ROADMAP.md) |

### Constructs emitted

One SPARQL query per operation: relationships lower to inline join triples and `OPTIONAL`s (no per-relationship sub-queries; rows group into entities post-hoc, [ADR-0014](adr/0014-single-query-relationships.md)). Emitted grammar: `FILTER` incl. `EXISTS` (§17.4.1.4; negation renders `!(…)`, never the `NOT EXISTS` keyword; `EXISTS` also appears as a `BIND` argument from `shnex:exists`, §2); `OPTIONAL` (LeftJoin, §18.6); `BIND` (§10.1) with `COALESCE` (§17.4.1.3); `VALUES` (§10.2); `IF`, `BOUND`, `LANG`, `datatype()`, `REGEX` (2-arg client and unflagged `sh:pattern`; 3-arg only when `sh:flags` is present); the property-path forms (SPARQL §9; SHACL §4 grammar); `STR` (§17.4.2.7) wrapping language-typed filter operands and IRI string operations; author text passed through verbatim (`sh:select`/`sh:sparqlExpr`). Client filter operators: `eq`/`neq`, ordering comparisons (numeric and temporal types only), `in`/`notIn` (rendered `!(x IN (…))`), and string patterns (`contains`/`startsWith`/`endsWith`/`regex` → `CONTAINS`/`STRSTARTS`/`STRENDS`/`REGEX`); enum filters carry `eq`/`neq`/`in`/`notIn` only and booleans `eq`/`neq` only; several operators on one field AND-combine (`&&`); the OR combinator lowers to `||`.

## 4. Not consumed

- **SHACL Rules (`sh:rule`, Inference Rules spec)** — never parsed or executed today. The writes-era design ([ADR-0024](adr/0024-mutations-via-shape-rules.md), Proposed).
- **SHACL UI** — never read.
- **ShEx** — no bridge.
- **SPARQL Update / Graph Store Protocol** — reserved for the writes era.
- **Validation as such** — read-only scope ([ADR-0020](adr/0020-read-only-scope.md)).
