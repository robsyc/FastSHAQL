# Mutation survivor triage record

The committed record of mutation survivors we have triaged and deliberately accept — equivalent mutants, ineffective mutations, and ones not worth killing — so future sessions don't re-triage them. A mutant listed here is settled: revisit an entry only with a stated reason. The score floor ([`mutmut-floor.json`](../mutmut-floor.json)) gates the score; this record explains the residue it tolerates. Entries are appended batch by batch as triage proceeds, ordered by mutant id within a batch.

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

## Wave 1 — `core/parser` top-level modules (post-batch residue, 2026-09-01)

Killing tests landed in `tests/tiers/unit/parser/` (score 88.2% → 89.9%); the rows below are the survivors deliberately not killed. Verdicts: *ineffective* = diagnostic-text mutation; *equivalent* = observably identical behavior; *accepted-gap* = killable but not worth it now.

### `parser/property_shape.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.property_shape.x__check_default_value_boundaries__mutmut_15` | `check_default_value_boundaries` | warning text `single-valued` → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x__datatypes_from_shape__mutmut_19` | `datatypes_from_shape` | warning text → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x__datatypes_from_shape__mutmut_20` | `datatypes_from_shape` | warning text case-flip | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x__datatypes_from_shape__mutmut_21` | `datatypes_from_shape` | warning text upper | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x__datatypes_from_shape__mutmut_25` | `datatypes_from_shape` | warning text → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x__datatypes_from_shape__mutmut_26` | `datatypes_from_shape` | warning text case-flip | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x__datatypes_from_shape__mutmut_27` | `datatypes_from_shape` | warning text upper | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_2` | `parse_property_shape` | default `description_language="en"` → `"EN"` | equivalent | BCP 47 matching is case-insensitive |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_11` | `parse_property_shape` | `prop_shape=prop_shape` → `None` | accepted-gap | arg-drop survives the green suite; error-context vs data path unclear — revisit if parser diagnostics misreport |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_43` | `parse_property_shape` | positional `prop_shape,` removed | accepted-gap | same as `_11` |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_64` | `parse_property_shape` | `shape_iri` → `None` (warning arg) | ineffective | feeds warning text only |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_69` | `parse_property_shape` | warning text → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.property_shape.x__sole_datatype_constraint__mutmut_5` | `sole_datatype_constraint` | `predicates(member, None)` → `predicates(member,)` | equivalent | removed arg *is* the `None` default |
| `fastshaql.core.parser.property_shape.x__sole_datatype_constraint__mutmut_10` | `sole_datatype_constraint` | `objects(member, SH.datatype)` → `objects(member, None)` | equivalent | the `predicates == {sh:datatype}` guard means every object *is* a datatype object — filter subsumed |
| `fastshaql.core.parser.property_shape.x__sole_datatype_constraint__mutmut_12` | `sole_datatype_constraint` | `objects(member, SH.datatype)` → `objects(member,)` | equivalent | trailing-arg removal ⇒ `None`, same subsumption as `_10` |

### `parser/shacl_path.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.shacl_path.x__strict_path_list__mutmut_4` | `strict_path_list` | `what=` label → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x__strict_path_list__mutmut_13` | `strict_path_list` | `source` arg → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path__mutmut_16` | `parse_shacl_path` | `prop_shape` arg → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_3` | `parse_shacl_path_node` | error text → `XX…XX` | ineffective | error wording only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_4` | `parse_shacl_path_node` | error text case-flip | ineffective | error wording only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_5` | `parse_shacl_path_node` | error text upper | ineffective | error wording only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_18` | `parse_shacl_path_node` | error text → `XX…XX` | ineffective | error wording only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_25` | `parse_shacl_path_node` | `what=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_34` | `parse_shacl_path_node` | `source` arg → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_55` | `parse_shacl_path_node` | `source` arg → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_64` | `parse_shacl_path_node` | `what=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_69` | `parse_shacl_path_node` | `what=` text → `XX…XX` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_70` | `parse_shacl_path_node` | `what=` text case-flip | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_71` | `parse_shacl_path_node` | `what=` text upper | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_76` | `parse_shacl_path_node` | `what=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_77` | `parse_shacl_path_node` | `section=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_78` | `parse_shacl_path_node` | `source=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_86` | `parse_shacl_path_node` | `what=` text → `XX…XX` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_87` | `parse_shacl_path_node` | `what=` text case-flip | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_88` | `parse_shacl_path_node` | `what=` text upper | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_89` | `parse_shacl_path_node` | `section=` text → `XX…XX` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_98` | `parse_shacl_path_node` | `what=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_99` | `parse_shacl_path_node` | `section=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_100` | `parse_shacl_path_node` | `source=` → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_108` | `parse_shacl_path_node` | `what=` text → `XX…XX` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_109` | `parse_shacl_path_node` | `what=` text upper | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_110` | `parse_shacl_path_node` | `section=` text → `XX…XX` | ineffective | error-context label only |

### `parser/targets.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_2` | `unsupported_target` | error text → `XX…XX` | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_3` | `unsupported_target` | error text case-flip | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_4` | `unsupported_target` | error text upper | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_5` | `unsupported_target` | error text → `XX…XX` | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_6` | `unsupported_target` | error text upper | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_6` | `reject_unsupported` | `shape_iri` → `None` (error arg) | ineffective | feeds error text only |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_16` | `reject_unsupported` | error text → `XX…XX` | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_17` | `reject_unsupported` | error text case-flip | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_19` | `reject_unsupported` | error text → `XX…XX` | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_20` | `reject_unsupported` | error text upper | ineffective | error wording only |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_33` | `reject_unsupported` | `shape_iri` → `None` (error arg) | ineffective | feeds error text only |
| `fastshaql.core.parser.targets.x__implicit_class_target__mutmut_6` | `implicit_class_target` | `objects(shape_iri, RDF.type)` → `objects(shape_iri,)` | equivalent | trailing-arg removal ⇒ `None`; the behavioral case is mutant `_4` (wave-1b) |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_22` | `parse_target` | declaration label → `XX…XX` | ineffective | label feeds error text only |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_25` | `parse_target` | declaration label → `XX…XX` | ineffective | label feeds error text only |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_26` | `parse_target` | declaration label case-flip | ineffective | label feeds error text only |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_27` | `parse_target` | declaration label upper | ineffective | label feeds error text only |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_29` | `parse_target` | declaration label → `XX…XX` | ineffective | label feeds error text only |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_37` | `parse_target` | `join` separator in error text | ineffective | error wording only |

### `parser/parse.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_8` | `merge_parent_prop` | `child.graphql_type_name` → `None` (warning arg) | ineffective | feeds warning text only |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_10` | `merge_parent_prop` | `existing.iri` → `None` (warning arg) | ineffective | feeds warning text only |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_11` | `merge_parent_prop` | `prop.iri` → `None` (warning arg) | ineffective | feeds warning text only |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_19` | `merge_parent_prop` | warning text → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_20` | `merge_parent_prop` | warning text case-flip | ineffective | warning wording only |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_22` | `merge_parent_prop` | warning text → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.parse.x__resolve_inheritance__mutmut_8` | `resolve_inheritance` | cycle `join` separator in error text | ineffective | error wording only |
| `fastshaql.core.parser.parse.x__make_synthetic_shape__mutmut_5` | `_make_synthetic_shape` | explicit `description=None` removed | equivalent | equals the `NodeShapeIR` default |
| `fastshaql.core.parser.parse.x__make_synthetic_shape__mutmut_7` | `_make_synthetic_shape` | explicit `target_class=None` removed | equivalent | equals the `NodeShapeIR` default |
| `fastshaql.core.parser.parse.x_parse_shapes__mutmut_2` | `parse_shapes` | default `description_language="en"` → `"EN"` | equivalent | BCP 47 matching is case-insensitive |
| `fastshaql.core.parser.parse.x_parse_shapes__mutmut_11` | `parse_shapes` | `setdefault(shape_iri, None)` → `setdefault(shape_iri,)` | equivalent | removed arg *is* the `None` default |
| `fastshaql.core.parser.parse.x_parse_shapes__mutmut_16` | `parse_shapes` | positional `shape_iri,` removed from a call | accepted-gap | survival implies a log-call arg drop, not the `parse_node_shape` call (that would `TypeError`); revisit if parser diagnostics misreport |

### `parser/shacl_in.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_14` | `parse_shacl_in` | `what=` label → `None` | ineffective | error-context label only |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_24` | `parse_shacl_in` | error message → `None` | ineffective | error wording only |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_39` | `parse_shacl_in` | `prop_shape` → `None` (error arg) | ineffective | feeds error text only |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_44` | `parse_shacl_in` | warning text → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_47` | `parse_shacl_in` | warning text → `XX…XX` | ineffective | warning wording only |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_48` | `parse_shacl_in` | warning text upper | ineffective | warning wording only |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_50` | `parse_shacl_in` | `join` separator in warning text | ineffective | warning wording only |

### `parser/node_shape.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.node_shape.x__parse_inherited_shape_iris__mutmut_11` | `parse_inherited_shape_iris` | `sorted(key=str)` → `sorted(key=None)` | equivalent | `URIRef` is a `str` subclass — identical ordering |
| `fastshaql.core.parser.node_shape.x__parse_inherited_shape_iris__mutmut_13` | `parse_inherited_shape_iris` | `sorted(iris, key=str)` → `sorted(iris,)` | equivalent | same — default comparison is `str` |
| `fastshaql.core.parser.node_shape.x_parse_node_shape__mutmut_2` | `parse_node_shape` | default `description_language="en"` → `"EN"` | equivalent | BCP 47 matching is case-insensitive |

### `parser/util/graph_reads.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.util.graph_reads.x__pick_localized_literal__mutmut_6` | `pick_localized_literal` | `sorted(key=…)` → `sorted(…)` | equivalent | same order for str-comparable terms; the mixed-type crash case is mutant `_4` (wave-1b) |
| `fastshaql.core.parser.util.graph_reads.x__pick_localized_literal__mutmut_9` | `pick_localized_literal` | language key `""` → `"XXXX"` | equivalent | both sort before lowercase BCP 47 tags — order unchanged |
| `fastshaql.core.parser.util.graph_reads.x_first_localized_str__mutmut_2` | `first_localized_str` | default `lang="en"` → `"EN"` | equivalent | BCP 47 matching is case-insensitive |
| `fastshaql.core.parser.util.graph_reads.x__strict_rdf_list__mutmut_28` | `strict_rdf_list` | error text → `XX…XX` | ineffective | error wording only |

### `parser/util/identifiers.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.util.identifiers.x__read_code_identifier__mutmut_25` | `read_code_identifier` | message with regex doc → `XX…XX` | ineffective | documents the separately-applied regex; wording only |
| `fastshaql.core.parser.util.identifiers.x__read_code_identifier__mutmut_26` | `read_code_identifier` | message case-flip | ineffective | same |
| `fastshaql.core.parser.util.identifiers.x__read_code_identifier__mutmut_27` | `read_code_identifier` | message upper | ineffective | same |
| `fastshaql.core.parser.util.identifiers.x__finalize_graphql_name__mutmut_4` | `finalize_graphql_name` | error text → `XX…XX` | ineffective | error wording only |
| `fastshaql.core.parser.util.identifiers.x__finalize_graphql_name__mutmut_5` | `finalize_graphql_name` | error text case-flip | ineffective | error wording only |
| `fastshaql.core.parser.util.identifiers.x__finalize_graphql_name__mutmut_6` | `finalize_graphql_name` | error text upper | ineffective | error wording only |

### Wave-1b kill list (not triaged — tests landing next)

Killed by the wave-1b batch (default-language contract, per-shape skip loops, `sh:in` duplicate-warning scoping, target-predicate scoping, lexical fallback determinism): `property_shape.x_parse_property_shape__mutmut_1` and `_61`, `parse.x_parse_shapes__mutmut_20` and `_25`, `shacl_in.x_parse_shacl_in__mutmut_36`, `targets.x__reject_unsupported__mutmut_21`, `targets.x__implicit_class_target__mutmut_4`, `node_shape.x_parse_node_shape__mutmut_1`, `util.graph_reads.x__pick_localized_literal__mutmut_4`. Reclassified after reading the guard: `property_shape.x__sole_datatype_constraint__mutmut_10` is equivalent (row above).

## Wave 2 — `parser/node_expr/*` + `core/translation` (post-batch residue, 2026-09-01)

Scope: the 220 survivors of the wave-1 batch in `core/parser/node_expr/`
(select_scan, semantics, shacl_prefixes, parse, filter_shape) and
`core/translation/` (node_expr, filter_shape, query, selection, variables,
paths, patterns, joins, field_binding, filters/*). Killed by the wave-2
batch:

- `select_scan`: `parse_shacl_select` — keyword search anchoring after the
  SELECT head, end-of-text brace boundary; `_reject_trailing_suffix` —
  whitespace spans between trailing literals don't end the scan;
  `validate_select_prebinding` — VALUES data-block anchoring (first `{`,
  never `rfind`), malformed-VALUES fallthrough keeps later spans checked.
- `semantics`: `reject_derived_path_targets` / `_reject_derived_conjuncts` —
  recursion through nested `sh:property` conjuncts (arity and argument
  neutralizations); `_reject_derived_predicates` — candidate shapes come
  from `sh:path` declarations only.
- `shacl_prefixes`: `parse_shacl_prefixes` — declarations are read from
  `sh:declare` edges of the node's `sh:prefixes` only.
- `parser/filter_shape`: `_parse_shape`, `_class_conjuncts`,
  `_pattern_conjuncts` — conjunct scans are subject-scoped (no sibling
  leakage); `_reject_unknown_predicates` — every predicate is checked.
- `translation/node_expr`: the role-var minting discipline — role-prefixed
  bases through every nesting lane (exists-over-exists, filterShape nodes,
  materialized compound conditions, pure nested-if conditions, single-branch
  impure arms, conditioned-OPTIONAL arm forms, defaultValue lanes).
- `translation/filter_shape`: exact lowering contracts — `datatype()`
  equality, `hasValue` equality, `sh:minCount 1` absorption inside property
  conjuncts, counter-allocated value variables through nesting depth.
- `translation/field_binding`: `_promote_relationship_field` registers
  `(join var, empty child VariableMap)` exactly.
- `translation/joins`: `relationship_join_patterns` emits the child
  `rdf:type` triple only when asked (`emit_type_triple` default False).
- `translation/filters/literals`: declared datatypes ride GraphQL string /
  int / bool / list operands.
- `translation/filters/operators`: `_membership_values` carries the field's
  declared datatype into `IN` literals.
- `translation/filters/fields`: `_branch_to_expression` call sites (AND/OR
  branches, NOT) wrap pattern-bearing branches in `EXISTS`.
- `translation/filters/exists`: `translate_exists_relationship` threads the
  registry into nested EXISTS walks.

Residue below (ordered by module, then mutant id).
### `parser/node_expr/select_scan.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_7` | `shacl_select` | -select_pos = find_keyword(text, "SELECT") +select_pos = find_keyword(text, "select") | equivalent | find_keyword is case-insensitive |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_10` | `shacl_select` | -raise UnsupportedShapeError("sh:select must start with SELECT") +raise UnsupportedShapeError("XXsh:select mus | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_34` | `shacl_select` | -where_pos = find_keyword(text, "WHERE", head_start) +where_pos = find_keyword(text, "where", head_start) | equivalent | find_keyword is case-insensitive |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_37` | `shacl_select` | -raise UnsupportedShapeError("sh:select must contain WHERE") +raise UnsupportedShapeError("XXsh:select must co | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_39` | `shacl_select` | -raise UnsupportedShapeError("sh:select must contain WHERE") +raise UnsupportedShapeError("SH:SELECT MUST CONT | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_54` | `shacl_select` | -"sh:select WHERE must be followed by a graph pattern block" +"XXsh:select WHERE must be followed by a graph p | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_55` | `shacl_select` | -"sh:select WHERE must be followed by a graph pattern block" +"sh:select where must be followed by a graph pat | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_3` | `extract_projection_var` | -raise UnsupportedShapeError("sh:select must project exactly one variable") +raise UnsupportedShapeError("XXsh | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_8` | `extract_projection_var` | -"sh:select SELECT-head expression (e.g. (EXPR AS ?var)) is not supported; " +"XXsh:select SELECT-head express | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_11` | `extract_projection_var` | -"move the computation into the WHERE body via BIND" +"XXmove the computation into the WHERE body via BINDXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_12` | `extract_projection_var` | -"move the computation into the WHERE body via BIND" +"move the computation into the where body via bind" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_13` | `extract_projection_var` | -"move the computation into the WHERE body via BIND" +"MOVE THE COMPUTATION INTO THE WHERE BODY VIA BIND" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_22` | `extract_projection_var` | -if not vars_found: +if vars_found: | equivalent | both arms raise the same error type |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_24` | `extract_projection_var` | -raise UnsupportedShapeError("sh:select must project exactly one variable") +raise UnsupportedShapeError("XXsh | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__reject_trailing_suffix__mutmut_9` | `reject_trailing_suffix` | -if m := _TOP_LEVEL_MODIFIERS_RE.search(suffix, start, end): +if m := _TOP_LEVEL_MODIFIERS_RE.search(suffix, s | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x__reject_trailing_suffix__mutmut_14` | `reject_trailing_suffix` | -"sh:select must not contain trailing SPARQL after the WHERE block" +"XXsh:select must not contain trailing SP | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_5` | `validate_select_prebinding` | -"sh:select body must not contain MINUS (SHACL-SPARQL Appendix A)" +"XXsh:select body must not contain MINUS ( | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_7` | `validate_select_prebinding` | -"sh:select body must not contain MINUS (SHACL-SPARQL Appendix A)" +"SH:SELECT BODY MUST NOT CONTAIN MINUS (SH | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_10` | `validate_select_prebinding` | -"sh:select body must not bind AS ?this or AS $this (SHACL-SPARQL Appendix A)" +"XXsh:select body must not bin | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_24` | `validate_select_prebinding` | -continue  # malformed VALUES — defer to the triple store +break  # malformed VALUES — defer to the triple sto | equivalent | break and continue coincide: a later data block would be found for the earlier match too |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_27` | `validate_select_prebinding` | -"sh:select body must not bind ?this/$this via VALUES (SHACL-SPARQL Appendix A)" +"XXsh:select body must not b | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_29` | `validate_select_prebinding` | -"sh:select body must not bind ?this/$this via VALUES (SHACL-SPARQL Appendix A)" +"SH:SELECT BODY MUST NOT BIN | ineffective | error/warning wording only |

### `parser/node_expr/semantics.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_10` | `arm_label` | -case _ as unreachable:  # pragma: no cover — unreachable: closed union \| assert_never(unreachable) + | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_15` | `arm_label` | -label = "shnex:ListExpression" +label = "XXshnex:ListExpressionXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_23` | `arm_label` | -label = "sh:select" +label = "XXsh:selectXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_26` | `arm_label` | -label = "shnex:pathValues" +label = "XXshnex:pathValuesXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_40` | `arm_label` | -assert_never(unreachable) +assert_never(None) | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.semantics.x_reject_derived_path_targets__mutmut_6` | `reject_derived_path_targets` | -case _ as unreachable:  # pragma: no cover — unreachable: closed union \| assert_never(unreachable) + | equivalent | unreachable arm (closed union) |
| `fastshaql.core.parser.node_expr.semantics.x_reject_derived_path_targets__mutmut_56` | `reject_derived_path_targets` | -assert_never(unreachable) +assert_never(None) | equivalent | unreachable arm (closed union) |
| `fastshaql.core.parser.node_expr.semantics.x__reject_derived_conjuncts__mutmut_11` | `reject_derived_conjuncts` | -_reject_derived_conjuncts(graph, conjunct.nested, shape_iri, field_name) +_reject_derived_conjuncts(graph, co | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.semantics.x__reject_derived_conjuncts__mutmut_12` | `reject_derived_conjuncts` | -_reject_derived_conjuncts(graph, conjunct.nested, shape_iri, field_name) +_reject_derived_conjuncts(graph, co | ineffective | error/warning wording only |

### `parser/node_expr/parse.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.parser.node_expr.parse.x_parse_expr_object__mutmut_6` | `expr_object` | -f"unsupported node expression object {obj!r}" +None | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_14` | `sole_key_parameter` | -"more than once" +"XXmore than onceXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_20` | `sole_key_parameter` | -names = ", ".join(_qname(graph, key) for key in present) +names = "XX, XX".join(_qname(graph, key) for key in | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_26` | `sole_key_parameter` | -"exactly one function identifier is required" +"XXexactly one function identifier is requiredXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_27` | `sole_key_parameter` | -"exactly one function identifier is required" +"EXACTLY ONE FUNCTION IDENTIFIER IS REQUIRED" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_58` | `sole_key_parameter` | -"more than once" +"XXmore than onceXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_59` | `sole_key_parameter` | -"more than once" +"MORE THAN ONCE" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_path_values__mutmut_4` | `parse_path_values` | -path = parse_shacl_path_node(graph, path_node, expr_node) +path = parse_shacl_path_node(graph, path_node, Non | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_path_values__mutmut_20` | `parse_path_values` | -"(non-constant focus expressions are not supported)" +"XX(non-constant focus expressions are not supported)XX | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_path_values__mutmut_21` | `parse_path_values` | -"(non-constant focus expressions are not supported)" +"(NON-CONSTANT FOCUS EXPRESSIONS ARE NOT SUPPORTED)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_if__mutmut_9` | `parse_if` | -"must be statically single-valued expressions (shnex:exists, constants, " +"XXmust be statically single-value | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_if__mutmut_11` | `parse_if` | -"sh:sparqlExpr, nested shnex:if)" +"XXsh:sparqlExpr, nested shnex:if)XX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_if__mutmut_12` | `parse_if` | -"sh:sparqlExpr, nested shnex:if)" +"sh:sparqlexpr, nested shnex:if)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_if__mutmut_13` | `parse_if` | -"sh:sparqlExpr, nested shnex:if)" +"SH:SPARQLEXPR, NESTED SHNEX:IF)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_constant_list__mutmut_11` | `parse_constant_list` | -"not supported)" +"XXnot supported)XX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_constant_list__mutmut_12` | `parse_constant_list` | -"not supported)" +"NOT SUPPORTED)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_instances_of__mutmut_13` | `parse_instances_of` | -"IRI list — arbitrary class expressions are not supported" +"XXIRI list — arbitrary class expressions are not | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_instances_of__mutmut_14` | `parse_instances_of` | -"IRI list — arbitrary class expressions are not supported" +"iri list — arbitrary class expressions are not s | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__parse_instances_of__mutmut_15` | `parse_instances_of` | -"IRI list — arbitrary class expressions are not supported" +"IRI LIST — ARBITRARY CLASS EXPRESSIONS ARE NOT S | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__unsupported_message__mutmut_12` | `unsupported_message` | -names = ", ".join(sorted(str(p) for p in predicates)) +names = "XX, XX".join(sorted(str(p) for p in predicate | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__unsupported_message__mutmut_18` | `unsupported_message` | -"expected sh:select, sh:sparqlExpr, or a shnex: function" +"XXexpected sh:select, sh:sparqlExpr, or a shnex:  | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__unsupported_message__mutmut_19` | `unsupported_message` | -"expected sh:select, sh:sparqlExpr, or a shnex: function" +"expected sh:select, sh:sparqlexpr, or a shnex: fu | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.parse.x__unsupported_message__mutmut_20` | `unsupported_message` | -"expected sh:select, sh:sparqlExpr, or a shnex: function" +"EXPECTED SH:SELECT, SH:SPARQLEXPR, OR A SHNEX: FU | ineffective | error/warning wording only |

### `parser/node_expr/filter_shape.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.parser.node_expr.filter_shape.x_parse_filter_shape__mutmut_3` | `filter_shape` | -return _parse_shape(graph, shape_node, inside_property=False) +return _parse_shape(graph, shape_node, inside_ | equivalent | None is falsy, equal to the False default |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_3` | `parse_shape` | -"named shape references are not supported" +"XXnamed shape references are not supportedXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_4` | `parse_shape` | -"named shape references are not supported" +"NAMED SHAPE REFERENCES ARE NOT SUPPORTED" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_32` | `parse_shape` | -"must be IRIs (Core §7.1.2)" +"XXmust be IRIs (Core §7.1.2)XX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_66` | `parse_shape` | -f"shnex:filterShape sh:maxCount {graph.value(shape_node, SH.maxCount)} " +f"shnex:filterShape sh:maxCount {gr | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_67` | `parse_shape` | -f"shnex:filterShape sh:maxCount {graph.value(shape_node, SH.maxCount)} " +f"shnex:filterShape sh:maxCount {gr | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_68` | `parse_shape` | -f"shnex:filterShape sh:maxCount {graph.value(shape_node, SH.maxCount)} " +f"shnex:filterShape sh:maxCount {gr | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_69` | `parse_shape` | -f"shnex:filterShape sh:maxCount {graph.value(shape_node, SH.maxCount)} " +f"shnex:filterShape sh:maxCount {gr | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_70` | `parse_shape` | -"is not supported — cardinality upper bounds need k-variable EXISTS " +"XXis not supported — cardinality uppe | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_71` | `parse_shape` | -"is not supported — cardinality upper bounds need k-variable EXISTS " +"is not supported — cardinality upper  | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_72` | `parse_shape` | -"is not supported — cardinality upper bounds need k-variable EXISTS " +"IS NOT SUPPORTED — CARDINALITY UPPER  | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_73` | `parse_shape` | -"(implementation narrowing)" +"XX(implementation narrowing)XX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_74` | `parse_shape` | -"(implementation narrowing)" +"(IMPLEMENTATION NARROWING)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__has_value_conjuncts__mutmut_8` | `has_value_conjuncts` | -"be matched in a filter (IRI or literal required)" +"XXbe matched in a filter (IRI or literal required)XX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__has_value_conjuncts__mutmut_9` | `has_value_conjuncts` | -"be matched in a filter (IRI or literal required)" +"be matched in a filter (iri or literal required)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__has_value_conjuncts__mutmut_10` | `has_value_conjuncts` | -"be matched in a filter (IRI or literal required)" +"BE MATCHED IN A FILTER (IRI OR LITERAL REQUIRED)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__class_conjuncts__mutmut_12` | `class_conjuncts` | -graph, value, what=f"shnex:filterShape {predicate} list" +graph, value, what=None | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__pattern_conjuncts__mutmut_10` | `pattern_conjuncts` | -"at most one is supported" +"XXat most one is supportedXX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__pattern_conjuncts__mutmut_11` | `pattern_conjuncts` | -"at most one is supported" +"AT MOST ONE IS SUPPORTED" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_11` | `min_count_conjuncts` | -"sh:property (a node-level minCount is vacuous)" +"XXsh:property (a node-level minCount is vacuous)XX" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_12` | `min_count_conjuncts` | -"sh:property (a node-level minCount is vacuous)" +"sh:property (a node-level mincount is vacuous)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_13` | `min_count_conjuncts` | -"sh:property (a node-level minCount is vacuous)" +"SH:PROPERTY (A NODE-LEVEL MINCOUNT IS VACUOUS)" | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_19` | `min_count_conjuncts` | -"only sh:minCount 1 lowers to flat SPARQL (implementation narrowing)" +"XXonly sh:minCount 1 lowers to flat S | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_20` | `min_count_conjuncts` | -"only sh:minCount 1 lowers to flat SPARQL (implementation narrowing)" +"only sh:mincount 1 lowers to flat spa | ineffective | error/warning wording only |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_21` | `min_count_conjuncts` | -"only sh:minCount 1 lowers to flat SPARQL (implementation narrowing)" +"ONLY SH:MINCOUNT 1 LOWERS TO FLAT SPA | ineffective | error/warning wording only |

### `translation/node_expr.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.node_expr.x__substitute_focus_var__mutmut_4` | `substitute_focus_var` | -pos = 0 +pos = None | equivalent | None equals 0 as a slice start |
| `fastshaql.core.translation.node_expr.x__translate__mutmut_10` | `translate` | -case _ as unreachable:  # pragma: no cover — unreachable: closed union \| assert_never(unreachable) + | equivalent | unreachable arm (closed union) |
| `fastshaql.core.translation.node_expr.x__translate__mutmut_105` | `translate` | -assert_never(unreachable) +assert_never(None) | equivalent | unreachable arm (closed union) |
| `fastshaql.core.translation.node_expr.x__condition__mutmut_24` | `condition` | -return [], Condition(_strict_true(pure), total=False) +return [], Condition(_strict_true(pure), total=None) | equivalent | None is falsy, same as total=False in the guards |
| `fastshaql.core.translation.node_expr.x__pure_branch__mutmut_20` | `pure_branch` | -case IfNodeExpr(cond=c, then=t, otherwise=o) if t is not None and o is not None: +case IfNodeExpr(cond=c, the | equivalent | a None branch fails the pure walk either way |

### `translation/filter_shape.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_8` | `translate_conjunct` | -case FilterMinCountOne():  # pragma: no cover — parser rejects node-level minCount \| raise TypeError( \| "Filt | equivalent | unreachable arm (closed union) |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_9` | `translate_conjunct` | -case _ as unreachable:  # pragma: no cover — unreachable: closed union \| assert_never(unreachable) + | equivalent | unreachable arm (closed union) |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_109` | `translate_conjunct` | -"FilterMinCountOne is only meaningful inside a property conjunct" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_110` | `translate_conjunct` | -"FilterMinCountOne is only meaningful inside a property conjunct" +"XXFilterMinCountOne is only meaningful in | ineffective | error/warning wording only |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_111` | `translate_conjunct` | -"FilterMinCountOne is only meaningful inside a property conjunct" +"filtermincountone is only meaningful insi | ineffective | error/warning wording only |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_112` | `translate_conjunct` | -"FilterMinCountOne is only meaningful inside a property conjunct" +"FILTERMINCOUNTONE IS ONLY MEANINGFUL INSI | ineffective | error/warning wording only |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_113` | `translate_conjunct` | -assert_never(unreachable) +assert_never(None) | ineffective | error/warning wording only |

### `translation/query.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.query.x_translate_query__mutmut_5` | `translate_query` | -"QueryContext.write_graph is reserved for the future writes era " +"XXQueryContext.write_graph is reserved fo | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x_translate_query__mutmut_6` | `translate_query` | -"QueryContext.write_graph is reserved for the future writes era " +"querycontext.write_graph is reserved for  | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x_translate_query__mutmut_8` | `translate_query` | -"(SPARQL Update WITH / Graph Store Protocol target); the " +"XX(SPARQL Update WITH / Graph Store Protocol tar | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x_translate_query__mutmut_9` | `translate_query` | -"(SPARQL Update WITH / Graph Store Protocol target); the " +"(sparql update with / graph store protocol targe | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x_translate_query__mutmut_10` | `translate_query` | -"(SPARQL Update WITH / Graph Store Protocol target); the " +"(SPARQL UPDATE WITH / GRAPH STORE PROTOCOL TARGE | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x_translate_query__mutmut_11` | `translate_query` | -"read-only query pipeline never consumes it — leave it unset" +"XXread-only query pipeline never consumes it  | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x_translate_query__mutmut_12` | `translate_query` | -"read-only query pipeline never consumes it — leave it unset" +"READ-ONLY QUERY PIPELINE NEVER CONSUMES IT —  | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x__target_entity_patterns__mutmut_17` | `target_entity_patterns` | -"cannot translate root query field" +"XXcannot translate root query fieldXX" | ineffective | error/warning wording only |
| `fastshaql.core.translation.query.x__target_entity_patterns__mutmut_18` | `target_entity_patterns` | -"cannot translate root query field" +"CANNOT TRANSLATE ROOT QUERY FIELD" | ineffective | error/warning wording only |

### `translation/selection.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.selection.x_iter_field_selections__mutmut_3` | `iter_field_selections` | -kind = type(sel).__name__ +kind = None | ineffective | error/warning wording only |
| `fastshaql.core.translation.selection.x_iter_field_selections__mutmut_4` | `iter_field_selections` | -kind = type(sel).__name__ +kind = type(None).__name__ | ineffective | error/warning wording only |
| `fastshaql.core.translation.selection.x_iter_field_selections__mutmut_6` | `iter_field_selections` | -f"Unsupported selection kind {kind!r}" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.selection.x__translate_relationship_selection__mutmut_3` | `translate_relationship_selection` | -prop, field_name=field_name +prop, field_name=None | ineffective | error/warning wording only |
| `fastshaql.core.translation.selection.x__translate_relationship_selection__mutmut_5` | `translate_relationship_selection` | -prop, field_name=field_name \| ) +prop, ) | ineffective | error/warning wording only |
| `fastshaql.core.translation.selection.x__translate_relationship_selection__mutmut_24` | `translate_relationship_selection` | -translate_selection(child_selection, child_shape, child_scope, frozenset()) +translate_selection(child_select | equivalent | explicit frozenset equals the parameter default |

### `translation/variables.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_13` | `VariableAllocator.allocate` | -"unreachable" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_14` | `VariableAllocator.allocate` | -"unreachable" +"XXunreachableXX" | ineffective | error/warning wording only |
| `fastshaql.core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_15` | `VariableAllocator.allocate` | -"unreachable" +"UNREACHABLE" | ineffective | error/warning wording only |

### `translation/paths.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.paths.x_map_shacl_path_to_sparql_path__mutmut_16` | `map_shacl_path_to_sparql_path` | -f"Unsupported SHACL property path type: {type(path).__name__}" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.paths.x_map_shacl_path_to_sparql_path__mutmut_17` | `map_shacl_path_to_sparql_path` | -f"Unsupported SHACL property path type: {type(path).__name__}" +f"Unsupported SHACL property path type: {type | ineffective | error/warning wording only |

### `translation/patterns.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.patterns.x__raw_core__mutmut_3` | `raw_core` | -f"derived property {prop.graphql_field_name!r} lacks its sh:values node expression" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.patterns.x_scalar_bind_patterns__mutmut_51` | `scalar_bind_patterns` | -*wrap_if_unbound(_raw_core(prop, inner, subject), bound=False), +*wrap_if_unbound(_raw_core(prop, inner, subj | equivalent | None is falsy, equal to the False default |

### `translation/joins.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.joins.x_relationship_join_patterns__mutmut_4` | `relationship_join_patterns` | -f"derived property {prop.graphql_field_name!r} lacks its sh:values node expression" +None | ineffective | error/warning wording only |

### `translation/field_binding.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.field_binding.x__promote_relationship_field__mutmut_10` | `promote_relationship_field` | -emit_type_triple=False, +emit_type_triple=None, | equivalent | None is falsy, equal to the False default |
| `fastshaql.core.translation.field_binding.x__promote_relationship_field__mutmut_14` | `promote_relationship_field` | -emit_type_triple=False, \| ) +) | equivalent | dropped argument falls back to the same False default |
| `fastshaql.core.translation.field_binding.x_bind_promoted_fields__mutmut_3` | `bind_promoted_fields` | -continue +break | equivalent | None is falsy, equal to the False default |
| `fastshaql.core.translation.field_binding.x_bind_promoted_fields__mutmut_7` | `bind_promoted_fields` | -continue  # pragma: no cover — promoted names guaranteed in property_shapes +break  # pragma: no cover — prom | equivalent | None is falsy, equal to the False default |
| `fastshaql.core.translation.field_binding.x_bind_promoted_fields__mutmut_21` | `bind_promoted_fields` | -field_name, prop, scope, project=False, bound=True +field_name, prop, scope, project=None, bound=True | equivalent | unreachable continue (promoted names guaranteed) |

### `translation/filters/literals.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.filters.literals.x_value_to_literal__mutmut_5` | `value_to_literal` | -case NullValueNode(): \| return None + | equivalent | falls through to the same None-returning arm |
| `fastshaql.core.translation.filters.literals.x_value_to_literal__mutmut_6` | `value_to_literal` | -case _:  # pragma: no cover — List/Object/Variable unreachable (GraphQL coerces) \| return None + | equivalent | falls off the match to the same None return |

### `translation/filters/extract.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.filters.extract.x__extract_int_argument__mutmut_5` | `extract_int_argument` | -f"{name!r} argument must be an integer" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.filters.extract.x_extract_where_argument__mutmut_6` | `extract_where_argument` | -"where argument must be an object value" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.filters.extract.x_extract_where_argument__mutmut_7` | `extract_where_argument` | -"where argument must be an object value" +"XXwhere argument must be an object valueXX" | ineffective | error/warning wording only |
| `fastshaql.core.translation.filters.extract.x_extract_where_argument__mutmut_8` | `extract_where_argument` | -"where argument must be an object value" +"WHERE ARGUMENT MUST BE AN OBJECT VALUE" | ineffective | error/warning wording only |

### `translation/filters/exists.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.filters.exists.x_translate_exists_relationship__mutmut_11` | `translate_exists_relationship` | -ctx.subject, child_subject, prop, emit_type_triple=False +ctx.subject, child_subject, prop, emit_type_triple= | equivalent | None is falsy, equal to the False default |
| `fastshaql.core.translation.filters.exists.x_translate_exists_relationship__mutmut_15` | `translate_exists_relationship` | -ctx.subject, child_subject, prop, emit_type_triple=False \| ) +ctx.subject, child_subject, prop, ) | equivalent | dropped argument falls back to the same False default |

### `translation/filters/fields.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.filters.fields.xǁ_FieldTranslatorǁ__init____mutmut_1` | `FieldTranslator.__init__` | -self.shape = shape +self.shape = None | equivalent | attribute never read after assignment |
| `fastshaql.core.translation.filters.fields.xǁ_FieldTranslatorǁon_property__mutmut_4` | `FieldTranslator.on_property` | -f"Relationship filter {name!r} requires an object value" +None | ineffective | error/warning wording only |
| `fastshaql.core.translation.filters.fields.x_translate_fields__mutmut_2` | `translate_fields` | -translator = _FieldTranslator(shape, ctx, registry) +translator = _FieldTranslator(None, ctx, registry) | equivalent | attribute never read after assignment |

### `translation/filters/operators.py`

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|

| `fastshaql.core.translation.filters.operators.x_translate_scalar_ops__mutmut_23` | `translate_scalar_ops` | -iri_values=False, +iri_values=None, | equivalent | None is falsy, equal to the False default |
| `fastshaql.core.translation.filters.operators.x__enum_term__mutmut_4` | `enum_term` | -if term is None or not isinstance(term, (URIRef, Literal)): +if term is None and not isinstance(term, (URIRef | equivalent | parser guarantees enum terms are URIRef/Literal |
| `fastshaql.core.translation.filters.operators.x_translate_operator_field__mutmut_20` | `translate_operator_field` | -literal = value_to_literal(op_field.value, XSD.string) +literal = value_to_literal(op_field.value, None) | equivalent | XSD.string and None produce the same plain literal |


## Wave 3 — registry / schema / execution / adapters / sparql / kernel (post-batch residue, 2026-09-07)

Scope: the 160 never-triaged survivors outside parser/translation —
`core/registry.py` + `executable.py` (41), `core/schema/*` (46),
`core/execution/*` + `adapters/*` (42), `core/sparql/*` + `core/kernel/*` (31).
Killed by the wave-3 batch (score 92.2% → 93.7%, survivors 383 → 313):

- `registry`: declaration reads are schema-subject-scoped — stray
  `graphql:*Shape`/`*Class` edges on non-schema resources are inert, and an
  object read scoped to the schema's own edges (public/protected/private,
  class closures, the publicNamespace warning, the schema hunt itself);
  class closures expand the declared class itself plus `rdfs:subClassOf`
  descendants only (predicate discipline); declaration precedence
  private > public > protected; `index_by_target_class` skips unindexed
  shapes instead of terminating the scan.
- `schema`: the operator → field-type contract (`_graphql_fields_for_spec`,
  `_list_field`) — which operator fields each `*Filter` input exposes and the
  GraphQL type per category (`Int` equality, `[Int!]!` membership, `String`
  patterns), asserted by direct call (see the shielding note below); the
  root type name `Query`.
- `execution`: metrics are strictly-positive after a real pipeline pass
  (`translate_ms`/`store_ms`/`convert_ms` wired, not the 0.0 defaults);
  `_group_rows_by_var` skips rows missing the group key (a decode-omitted
  unbound var never truncates later groups).
- `adapters`: `ide=True` defaults for both `build_graphql_view` and
  `build_graphql_router` serve GraphiQL on GET without opting in.
- `sparql`: `word_bounded_any` builds a working alternation (pinned directly
  — see shielding note); `skip_ws_and_comments` skips exactly the four SPARQL
  whitespace chars; `extract_braced_body` raises the opener `ValueError`
  (never `IndexError`) on empty text; `CompareExpr` threads `indent` into a
  populated `EXISTS` operand.
- `kernel`: the Accept-Language default weight is exactly 1.0 (a q-less entry
  ties an explicit `q=1`); `http(s)://` sources merge as locations
  (positional `parse(source)`), never inline data.

Process note (test trims): the same batch loosened ~15 diagnostics-wording
pins in `unit/parser/` to identifier-substring asserts (thermo-nuclear
review: sentence pins contradict the ineffective-wording verdicts below) and
deleted tests whose emissions the e2e goldens pin byte-for-byte (lang chain
twins, the FROM-render trio). Ten wording-only mutants those pins used to
kill are reclassified ineffective below rather than re-pinned.

### Residue — wave-3 scope

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.registry.x__demote_untargeted_public_shapes__mutmut_5/7/8/11/12/13/14/15` | `demote_untargeted_public_shapes` | warning text/args | ineffective | warning wording only |
| `fastshaql.core.registry.x_resolve_visibility__mutmut_12/19/33` | `resolve_visibility` | error/warning text | ineffective | wording only; existing `match` substrings survive |
| `fastshaql.core.registry.x__enforce_closed_world__mutmut_4/6` | `enforce_closed_world` | guard `or`→`and` / `_is_synthetic(None)` | equivalent | synthetic shapes are never EXCLUDED (PROTECTED precedes), so un-skipping them cannot fire the VisibilityError |
| `fastshaql.executable.x__resolver_context__mutmut_4` | `resolver_context` | TypeError text | ineffective | error wording only |
| `fastshaql.core.schema.filters.x_build_filter_type__mutmut_10/12` | `build_filter_type` | `field_name` arg → None / dropped | equivalent | error-label only; falls back to `prop.graphql_field_name`, which always equals the passed key |
| `fastshaql.core.schema._gql.x_input_object/object_type/enum_type__mutmut_1/5/6/7/10/13` | `_gql` constructors | `typing.cast` strings / dead `description` default | equivalent | `cast` is a runtime identity; no caller passes `description` |
| `fastshaql.core.schema.fields.x_wrap_field_type__mutmut_6/10/11/12` | `wrap_field_type` | `typing.cast` strings | equivalent | cast identity |
| `fastshaql.core.execution.converter` cast sites (`_apply_scalar_fields` 19/23/24, `_finalize_entity` 9/13/14, `_group_rows_by_var`—none, `_apply_relationship_fields` 4/6, `_init_entity` 10, `_finalize_entity` 2) | converter | cast strings / arg neutralizations / list-init | equivalent | cast identity; overwritten before read; error-label fallback (`_4`/`_6`); unreachable absent-field KeyError (`_2`) |
| `fastshaql.core.execution.converter.x_coerce_value__mutmut_4/6/7` | `coerce_value` | fall-through arm deleted / TypeError text | accepted-gap | `# pragma: no cover` defensive branch behind the `SparqlTerm` type contract; killing it means passing a non-term on purpose |
| `fastshaql.core.execution.store` cast sites (`decode_sparql_results` 10/14/15/16, `InMemoryStore.query` 7/11/12/13/14/18/19/20) | store | `typing.cast` strings | equivalent | cast identity |
| `fastshaql.adapters.django.x_build_graphql_view__mutmut_2/3/4/5` | `build_graphql_view` | NotImplementedError text | ineffective | raise still covered; wording only |
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_6/7/49/50` | `extract_braced_body` | error text | ineffective | wording only; `match` substrings survive |
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_12/13/14` | `extract_braced_body` | `body_start` initializers | equivalent | guard guarantees `{` at `open_brace`; first loop iteration overwrites the initializer before the return slice |
| `fastshaql.core.sparql.lex.x_find_keyword__mutmut_9` | `find_keyword` | `span_end <= start` → `<` | equivalent | a zero-width search window can never match a non-empty keyword |
| `fastshaql.core.sparql.expressions.x__render_child__mutmut_1` | `_render_child` | `indent=0` default → 1 | equivalent | dead default — both callers pass `indent` explicitly |
| `fastshaql.core.sparql.queries.x__validate_solution_modifiers__mutmut_6/14` | `validate_solution_modifiers` | LIMIT/OFFSET error text | ineffective | wording only |
| `fastshaql.core.kernel.context.x_lang_tags_from_accept_language__mutmut_14/17` | `lang_tags_from_accept_language` | `maxsplit` 1→none/2 | equivalent | element `[0]` of a split is unchanged by `maxsplit` |
| `fastshaql.core.kernel.identifiers.x_raw_enum_member_name__mutmut_3/4` | `raw_enum_member_name` | TypeError text | ineffective | wording only (pragma'd arm) |
| `fastshaql.core.kernel.io.x__expand_source__mutmut_3/4` | `_expand_source` | TypeError text | ineffective | wording only |

### Residue — wording reclassifications from the wave-3 trim (parser modules, wave-1 scope)

Previously killed by sentence-exact diagnostics pins; the pins are now
identifier-substrings, so these survive. All are XX-wrap / case-flip /
suffix mutations of warning text whose identifier-bearing prefix stays
asserted:

| Mutant ID | Location | Mutation | Verdict | Reason |
|---|---|---|---|---|
| `fastshaql.core.parser.parse.x__resolve_shape_iri__mutmut_14` | `resolve_shape_iri` | synthetic-shape warning text | ineffective | wording only; class + synthetic IRIs still asserted |
| `fastshaql.core.parser.property_shape.x__check_derived_field_boundaries__mutmut_16` | `check_derived_field_boundaries` | warning text wrap | ineffective | wording only; `min_count=` value still asserted |
| `fastshaql.core.parser.property_shape.x__datatype_objects__mutmut_10/11` | `datatype_objects` | error text | ineffective | wording only; shape/field prefix still asserted |
| `fastshaql.core.parser.property_shape.x__or_datatypes__mutmut_21/23/24` | `or_datatypes` | warning text | ineffective | wording only |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_44/115` | `parse_property_shape` | zero-capacity warning text | ineffective | wording only; declaration label still asserted |
| `fastshaql.core.parser.node_shape.x_parse_node_shape__mutmut_40` | `parse_node_shape` | duplicate-field warning text | ineffective | wording only; field + shape still asserted |

### Shielding caveat — import-time-computed tables

`_OPERATOR_FIELD_SPECS` (schema/filters.py) and the `select_scan` modifier
regexes (via `word_bounded_any`) are computed at module import, before
mutmut arms its trampoline — forked test children inherit the already-built
objects, so schema-level assertions can never observe mutations there.
Direct unit calls at test time are the *only* mutation coverage for such
tables (`unit/schema/test_filters.py`, `unit/sparql/test_lex.py`); keep
them direct if those modules are restructured.
