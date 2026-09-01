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
