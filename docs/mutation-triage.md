# Mutation survivor triage record

The committed record of mutation survivors we have triaged and deliberately
accept, so future sessions don't re-triage them. A mutant listed here is
settled: revisit an entry only with a stated reason. The score floor
([`mutmut-floor.json`](../mutmut-floor.json)) gates the score; this record
explains the residue it tolerates. Reproduce with `just mutate`; inspect a
survivor with `uv run mutmut show <id>`.

Every survivor is one of two verdicts — no open gaps remain:

- **equivalent** — observably identical behavior. Recurring mechanisms:
  `typing.cast` is a runtime identity (its type argument is never
  consulted); a `None` or dropped argument equals the callee's default or
  falsy value; closed-union `match` arms (with `assert_never`) are
  unreachable; and the matchers involved (`find_keyword`, BCP 47 language
  lookup) are case-insensitive.
- **ineffective** — diagnostic text only: error/warning wording and
  error-context labels. Tests pin the identifier-bearing prefix of
  diagnostics, never full sentences, so wording mutants survive by design.

A Reason is recorded only where the verdict is not an instance of the
definitions above. Mutant numbers are per-function and shift when the
source changes — locate a survivor by module + function + mutation shape,
not by number alone.

### `adapters.django`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.adapters.django.x_build_graphql_view__mutmut_2` | `build_graphql_view` — argument → None | ineffective | — |
| `fastshaql.adapters.django.x_build_graphql_view__mutmut_3` | `build_graphql_view` — XX-wrap | ineffective | — |
| `fastshaql.adapters.django.x_build_graphql_view__mutmut_4/5` | `build_graphql_view` — case-flip | ineffective | — |

### `core.execution.converter`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.execution.converter.x__apply_scalar_fields__mutmut_19` | `apply_scalar_fields` — cast type → None | equivalent | — |
| `fastshaql.core.execution.converter.x__finalize_entity__mutmut_2` | `finalize_entity` — and → or | equivalent | every list-valued entity key is written only for a kind.is_list property shape, so the not-in-shape side of the or never reaches the prop lookup |
| `fastshaql.core.execution.converter.x__finalize_entity__mutmut_9` | `finalize_entity` — cast type → None | equivalent | — |
| `fastshaql.core.execution.converter.x_coerce_value__mutmut_6` | `coerce_value` — TypeError text XX-wrap | ineffective | — |
| `fastshaql.core.execution.converter.x_coerce_value__mutmut_7` | `coerce_value` — TypeError text case-flip | ineffective | — |

### `core.execution.store`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.execution.store.x_decode_sparql_results__mutmut_10` | `decode_sparql_results` — cast type → None | equivalent | — |
| `fastshaql.core.execution.store.xǁInMemoryStoreǁquery__mutmut_7/11` | `query` — cast type → None | equivalent | — |

### `core.kernel.context`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.kernel.context.x_lang_tags_from_accept_language__mutmut_14/17` | `lang_tags_from_accept_language` — split maxsplit mutated | equivalent | element [0] of a split is unchanged by maxsplit |

### `core.kernel.identifiers`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.kernel.identifiers.x_raw_enum_member_name__mutmut_3/4` | `raw_enum_member_name` — argument → None | ineffective | — |

### `core.kernel.io`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.kernel.io.x__expand_source__mutmut_3/4` | `expand_source` — argument → None | ineffective | — |

### `core.parser.datatypes`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.datatypes.x__datatype_objects__mutmut_10` | `datatype_objects` — error text XX-wrap | ineffective | — |
| `fastshaql.core.parser.datatypes.x__datatype_objects__mutmut_11` | `datatype_objects` — error text case-flip | ineffective | — |
| `fastshaql.core.parser.datatypes.x__or_datatypes__mutmut_21/23` | `or_datatypes` — warning text XX-wrap | ineffective | — |
| `fastshaql.core.parser.datatypes.x__or_datatypes__mutmut_24` | `or_datatypes` — warning text upper | ineffective | — |
| `fastshaql.core.parser.datatypes.x__sole_datatype_constraint__mutmut_5` | `sole_datatype_constraint` — trailing argument dropped | equivalent | — |
| `fastshaql.core.parser.datatypes.x__sole_datatype_constraint__mutmut_10` | `sole_datatype_constraint` — argument → None | equivalent | the `predicates == {sh:datatype}` guard means every object is a datatype object — the filter is subsumed |
| `fastshaql.core.parser.datatypes.x__sole_datatype_constraint__mutmut_12` | `sole_datatype_constraint` — trailing argument dropped | equivalent | dropped arg is the None default; same subsumption as `_10` |
| `fastshaql.core.parser.datatypes.x_datatypes_from_shape__mutmut_19` | `datatypes_from_shape` — error text XX-wrap | ineffective | — |
| `fastshaql.core.parser.datatypes.x_datatypes_from_shape__mutmut_20` | `datatypes_from_shape` — error text case-flip | ineffective | — |
| `fastshaql.core.parser.datatypes.x_datatypes_from_shape__mutmut_21` | `datatypes_from_shape` — error text upper | ineffective | — |
| `fastshaql.core.parser.datatypes.x_datatypes_from_shape__mutmut_25` | `datatypes_from_shape` — error text XX-wrap | ineffective | — |
| `fastshaql.core.parser.datatypes.x_datatypes_from_shape__mutmut_26` | `datatypes_from_shape` — error text case-flip | ineffective | — |
| `fastshaql.core.parser.datatypes.x_datatypes_from_shape__mutmut_27` | `datatypes_from_shape` — error text upper | ineffective | — |

### `core.parser.node_expr.filter_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.node_expr.filter_shape.x__class_conjuncts__mutmut_12` | `class_conjuncts` — argument → None | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__has_value_conjuncts__mutmut_8` | `has_value_conjuncts` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__has_value_conjuncts__mutmut_9/10` | `has_value_conjuncts` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_11` | `min_count_conjuncts` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_12/13` | `min_count_conjuncts` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_19` | `min_count_conjuncts` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_20/21` | `min_count_conjuncts` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_3` | `parse_shape` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_4` | `parse_shape` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_32` | `parse_shape` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_66/67` | `parse_shape` — argument → None | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_68/69` | `parse_shape` — error-text interpolation arg dropped | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_70` | `parse_shape` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_71/72` | `parse_shape` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_73` | `parse_shape` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__parse_shape__mutmut_74` | `parse_shape` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__pattern_conjuncts__mutmut_10` | `pattern_conjuncts` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x__pattern_conjuncts__mutmut_11` | `pattern_conjuncts` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.filter_shape.x_parse_filter_shape__mutmut_3` | `parse_filter_shape` — argument → None | equivalent | — |

### `core.parser.node_expr.parse`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.node_expr.parse.x__parse_constant_list__mutmut_11` | `parse_constant_list` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_constant_list__mutmut_12` | `parse_constant_list` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_if__mutmut_9/11` | `parse_if` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_if__mutmut_12/13` | `parse_if` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_instances_of__mutmut_13` | `parse_instances_of` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_instances_of__mutmut_14/15` | `parse_instances_of` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_path_values__mutmut_4` | `parse_path_values` — argument → None | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_path_values__mutmut_20` | `parse_path_values` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__parse_path_values__mutmut_21` | `parse_path_values` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_14/20/26` | `sole_key_parameter` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_27` | `sole_key_parameter` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_58` | `sole_key_parameter` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__sole_key_parameter__mutmut_59` | `sole_key_parameter` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__unsupported_message__mutmut_12/18` | `unsupported_message` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x__unsupported_message__mutmut_19/20` | `unsupported_message` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.parse.x_parse_expr_object__mutmut_6` | `parse_expr_object` — argument → None | ineffective | — |

### `core.parser.node_expr.select_scan`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_3/8/11` | `extract_projection_var` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_12/13` | `extract_projection_var` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_22` | `extract_projection_var` — guard negated | equivalent | both arms of the flipped guard raise the same UnsupportedShapeError |
| `fastshaql.core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_24` | `extract_projection_var` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x__reject_trailing_suffix__mutmut_9` | `reject_trailing_suffix` — search endpos dropped | ineffective | any non-blank code span raises either way — only the message choice changes |
| `fastshaql.core.parser.node_expr.select_scan.x__reject_trailing_suffix__mutmut_14` | `reject_trailing_suffix` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_7` | `parse_shacl_select` — keyword case-flip | equivalent | — |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_10` | `parse_shacl_select` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_34` | `parse_shacl_select` — keyword case-flip | equivalent | — |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_37` | `parse_shacl_select` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_39` | `parse_shacl_select` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_54` | `parse_shacl_select` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_55` | `parse_shacl_select` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_5` | `validate_select_prebinding` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_7` | `validate_select_prebinding` — case-flip | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_10` | `validate_select_prebinding` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_24` | `validate_select_prebinding` — continue → break | equivalent | a later data block is found for the earlier match too — break and continue coincide |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_27` | `validate_select_prebinding` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_29` | `validate_select_prebinding` — case-flip | ineffective | — |

### `core.parser.node_expr.semantics`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.node_expr.semantics.x__reject_derived_conjuncts__mutmut_11/12` | `reject_derived_conjuncts` — argument → None | ineffective | — |
| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_10` | `arm_label` — unreachable arm deleted | equivalent | — |
| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_15/23/26` | `arm_label` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.node_expr.semantics.x_arm_label__mutmut_40` | `arm_label` — assert_never(None) | equivalent | — |
| `fastshaql.core.parser.node_expr.semantics.x_reject_derived_path_targets__mutmut_6` | `reject_derived_path_targets` — unreachable arm deleted | equivalent | — |
| `fastshaql.core.parser.node_expr.semantics.x_reject_derived_path_targets__mutmut_56` | `reject_derived_path_targets` — assert_never(None) | equivalent | — |

### `core.parser.node_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.node_shape.x__parse_inherited_shape_iris__mutmut_11` | `parse_inherited_shape_iris` — argument → None | equivalent | URIRef is a str subclass — identical ordering |
| `fastshaql.core.parser.node_shape.x__parse_inherited_shape_iris__mutmut_13` | `parse_inherited_shape_iris` — sorted key dropped | equivalent | same — default comparison is str |
| `fastshaql.core.parser.node_shape.x_parse_node_shape__mutmut_2` | `parse_node_shape` — default "en" → "EN" | equivalent | — |
| `fastshaql.core.parser.node_shape.x_parse_node_shape__mutmut_40` | `parse_node_shape` — XX-wrap | ineffective | — |

### `core.parser.parse`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.parse.x__make_synthetic_shape__mutmut_5/7` | `make_synthetic_shape` — line deleted | equivalent | — |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_8/10/11` | `merge_parent_prop` — argument → None | ineffective | — |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_19` | `merge_parent_prop` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_20` | `merge_parent_prop` — case-flip | ineffective | — |
| `fastshaql.core.parser.parse.x__merge_parent_prop__mutmut_22` | `merge_parent_prop` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.parse.x__resolve_inheritance__mutmut_8` | `resolve_inheritance` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.parse.x__resolve_shape_iri__mutmut_14` | `resolve_shape_iri` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.parse.x_parse_shapes__mutmut_2` | `parse_shapes` — default "en" → "EN" | equivalent | — |
| `fastshaql.core.parser.parse.x_parse_shapes__mutmut_11` | `parse_shapes` — setdefault argument dropped | equivalent | — |

### `core.parser.property_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.property_shape.x__check_derived_field_boundaries__mutmut_16` | `check_derived_field_boundaries` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_2` | `parse_property_shape` — default "en" → "EN" | equivalent | — |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_43` | `parse_property_shape` — warning argument dropped | ineffective | — |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_44` | `parse_property_shape` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_64` | `parse_property_shape` — argument → None | ineffective | — |
| `fastshaql.core.parser.property_shape.x_parse_property_shape__mutmut_69/115` | `parse_property_shape` — XX-wrap | ineffective | — |

### `core.parser.shacl_in`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_14/24/39` | `parse_shacl_in` — argument → None | ineffective | — |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_44/47` | `parse_shacl_in` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_48` | `parse_shacl_in` — case-flip | ineffective | — |
| `fastshaql.core.parser.shacl_in.x_parse_shacl_in__mutmut_50` | `parse_shacl_in` — XX-wrap | ineffective | — |

### `core.parser.shacl_path`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.shacl_path.x__strict_path_list__mutmut_4/13` | `strict_path_list` — argument → None | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path__mutmut_16` | `parse_shacl_path` — argument → None | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_3` | `parse_shacl_path_node` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_4/5` | `parse_shacl_path_node` — case-flip | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_18` | `parse_shacl_path_node` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_25` | `parse_shacl_path_node` — error-context label → None | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_34/55/64` | `parse_shacl_path_node` — argument → None | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_69` | `parse_shacl_path_node` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_70/71` | `parse_shacl_path_node` — case-flip | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_76/77/78` | `parse_shacl_path_node` — argument → None | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_86` | `parse_shacl_path_node` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_87/88` | `parse_shacl_path_node` — case-flip | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_89` | `parse_shacl_path_node` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_98/99/100` | `parse_shacl_path_node` — argument → None | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_108` | `parse_shacl_path_node` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_109` | `parse_shacl_path_node` — case-flip | ineffective | — |
| `fastshaql.core.parser.shacl_path.x_parse_shacl_path_node__mutmut_110` | `parse_shacl_path_node` — XX-wrap | ineffective | — |

### `core.parser.targets`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_6` | `reject_unsupported` — argument → None | ineffective | — |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_16` | `reject_unsupported` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_17` | `reject_unsupported` — case-flip | ineffective | — |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_19` | `reject_unsupported` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_20` | `reject_unsupported` — case-flip | ineffective | — |
| `fastshaql.core.parser.targets.x__reject_unsupported__mutmut_33` | `reject_unsupported` — argument → None | ineffective | — |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_2` | `unsupported_target` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_3/4` | `unsupported_target` — case-flip | ineffective | — |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_5` | `unsupported_target` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.targets.x__unsupported_target__mutmut_6` | `unsupported_target` — case-flip | ineffective | — |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_22/25` | `parse_target` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_26/27` | `parse_target` — case-flip | ineffective | — |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_29` | `parse_target` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.targets.x_parse_target__mutmut_37` | `parse_target` — join separator in error text | ineffective | — |

### `core.parser.util.graph_reads`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.util.graph_reads.x__pick_localized_literal__mutmut_9` | `pick_localized_literal` — language key "" → "XXXX" | equivalent | both "" and "XXXX" sort before lowercase BCP 47 tags — order unchanged |
| `fastshaql.core.parser.util.graph_reads.x_first_localized_str__mutmut_2` | `first_localized_str` — default "en" → "EN" | equivalent | — |
| `fastshaql.core.parser.util.graph_reads.x_strict_rdf_list__mutmut_28` | `strict_rdf_list` — error text XX-wrap | ineffective | — |

### `core.parser.util.identifiers`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.util.identifiers.x_finalize_graphql_name__mutmut_4` | `finalize_graphql_name` — error text XX-wrap | ineffective | — |
| `fastshaql.core.parser.util.identifiers.x_finalize_graphql_name__mutmut_5` | `finalize_graphql_name` — error text case-flip | ineffective | — |
| `fastshaql.core.parser.util.identifiers.x_finalize_graphql_name__mutmut_6` | `finalize_graphql_name` — error text upper | ineffective | — |
| `fastshaql.core.parser.util.identifiers.x_read_code_identifier__mutmut_25` | `read_code_identifier` — error text XX-wrap | ineffective | — |
| `fastshaql.core.parser.util.identifiers.x_read_code_identifier__mutmut_26` | `read_code_identifier` — error text case-flip | ineffective | — |
| `fastshaql.core.parser.util.identifiers.x_read_code_identifier__mutmut_27` | `read_code_identifier` — error text upper | ineffective | — |

### `core.parser.visibility`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_5` | `demote_untargeted_public_shapes` — argument → None | ineffective | — |
| `fastshaql.core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_7` | `demote_untargeted_public_shapes` — warning argument dropped | ineffective | — |
| `fastshaql.core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_8/11` | `demote_untargeted_public_shapes` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_12/13` | `demote_untargeted_public_shapes` — case-flip | ineffective | — |
| `fastshaql.core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_14` | `demote_untargeted_public_shapes` — XX-wrap | ineffective | — |
| `fastshaql.core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_15` | `demote_untargeted_public_shapes` — case-flip | ineffective | — |
| `fastshaql.core.parser.visibility.x__enforce_closed_world__mutmut_4` | `enforce_closed_world` — or → and | equivalent | synthetic shapes are never EXCLUDED (PROTECTED precedes), so un-skipping them cannot fire the VisibilityError |
| `fastshaql.core.parser.visibility.x__enforce_closed_world__mutmut_6` | `enforce_closed_world` — argument → None | equivalent | same — synthetic shapes never reach the EXCLUDED arm |
| `fastshaql.core.parser.visibility.x_resolve_visibility__mutmut_12/19/33` | `resolve_visibility` — XX-wrap | ineffective | — |

### `core.schema._gql`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.schema._gql.x_enum_type__mutmut_1` | `enum_type` — cast type → None | equivalent | — |
| `fastshaql.core.schema._gql.x_input_object__mutmut_1` | `input_object` — cast type → None | equivalent | — |
| `fastshaql.core.schema._gql.x_object_type__mutmut_1` | `object_type` — cast type → None | equivalent | — |

### `core.schema.fields`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.schema.fields.x_wrap_field_type__mutmut_6` | `wrap_field_type` — cast type → None | equivalent | — |

### `core.sparql.lex`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_6` | `extract_braced_body` — XX-wrap | ineffective | — |
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_7` | `extract_braced_body` — case-flip | ineffective | — |
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_12` | `extract_braced_body` — initializer neutralized | equivalent | the guard guarantees `{` at open_brace; the first loop iteration overwrites the initializer before the return slice |
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_13/14` | `extract_braced_body` — initializer neutralized | equivalent | same — overwritten before the return slice |
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_49` | `extract_braced_body` — XX-wrap | ineffective | — |
| `fastshaql.core.sparql.lex.x_extract_braced_body__mutmut_50` | `extract_braced_body` — case-flip | ineffective | — |
| `fastshaql.core.sparql.lex.x_find_keyword__mutmut_9` | `find_keyword` — guard `<=` → `<` | equivalent | a zero-width search window can never match a non-empty keyword |
| `fastshaql.core.sparql.lex.x_map_code_spans__mutmut_2` | `map_code_spans` — initializer 0 → None | equivalent | None is 0 as a slice start |

### `core.sparql.queries`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.sparql.queries.x__validate_solution_modifiers__mutmut_6/14` | `validate_solution_modifiers` — XX-wrap | ineffective | — |

### `core.translation.filter_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_8/9` | `translate_conjunct` — unreachable arm deleted | equivalent | — |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_109` | `translate_conjunct` — argument → None | ineffective | — |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_110` | `translate_conjunct` — XX-wrap | ineffective | — |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_111/112` | `translate_conjunct` — case-flip | ineffective | — |
| `fastshaql.core.translation.filter_shape.x__translate_conjunct__mutmut_113` | `translate_conjunct` — assert_never(None) | equivalent | — |

### `core.translation.filters.literals`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.filters.literals.x_value_to_literal__mutmut_5` | `value_to_literal` — match arm deleted | equivalent | falls through to the same None-returning arm |
| `fastshaql.core.translation.filters.literals.x_value_to_literal__mutmut_6` | `value_to_literal` — match arm deleted | equivalent | falls off the match to the same None return |

### `core.translation.filters.operators`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.filters.operators.x__enum_term__mutmut_4` | `enum_term` — or → and | equivalent | the parser guarantees enum terms are URIRef/Literal |
| `fastshaql.core.translation.filters.operators.x_translate_operator_field__mutmut_20` | `translate_operator_field` — argument → None | equivalent | XSD.string and None produce the same plain literal |
| `fastshaql.core.translation.filters.operators.x_translate_scalar_ops__mutmut_23` | `translate_scalar_ops` — argument → None | equivalent | — |

### `core.translation.filters.where`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.filters.where.x__extract_int_argument__mutmut_5` | `extract_int_argument` — argument → None | ineffective | — |
| `fastshaql.core.translation.filters.where.x_extract_where_argument__mutmut_6` | `extract_where_argument` — argument → None | ineffective | — |
| `fastshaql.core.translation.filters.where.x_extract_where_argument__mutmut_7` | `extract_where_argument` — XX-wrap | ineffective | — |
| `fastshaql.core.translation.filters.where.x_extract_where_argument__mutmut_8` | `extract_where_argument` — case-flip | ineffective | — |
| `fastshaql.core.translation.filters.where.x_translate_fields__mutmut_2` | `translate_fields` — argument → None | equivalent | the shape attribute is never read after assignment |
| `fastshaql.core.translation.filters.where.xǁ_FieldTranslatorǁ__init____mutmut_1` | `init__` — argument → None | equivalent | the shape attribute is never read after assignment |
| `fastshaql.core.translation.filters.where.xǁ_FieldTranslatorǁon_property__mutmut_4` | `on_property` — argument → None | ineffective | — |

### `core.translation.joins`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.joins.x_relationship_join_patterns__mutmut_4` | `relationship_join_patterns` — argument → None | ineffective | — |

### `core.translation.node_expr`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.node_expr.x__condition__mutmut_24` | `condition` — argument → None | equivalent | — |
| `fastshaql.core.translation.node_expr.x__pure_branch__mutmut_20` | `pure_branch` — and → or | equivalent | a None branch fails the pure walk either way |
| `fastshaql.core.translation.node_expr.x__translate__mutmut_10` | `translate` — unreachable arm deleted | equivalent | — |
| `fastshaql.core.translation.node_expr.x__translate__mutmut_105` | `translate` — assert_never(None) | equivalent | — |

### `core.translation.paths`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.paths.x_map_shacl_path_to_sparql_path__mutmut_16/17` | `map_shacl_path_to_sparql_path` — argument → None | ineffective | — |

### `core.translation.patterns`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.patterns.x__raw_core__mutmut_3` | `raw_core` — argument → None | ineffective | — |
| `fastshaql.core.translation.patterns.x_scalar_bind_patterns__mutmut_51` | `scalar_bind_patterns` — argument → None | equivalent | — |

### `core.translation.query`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.query.x__target_entity_patterns__mutmut_17` | `target_entity_patterns` — XX-wrap | ineffective | — |
| `fastshaql.core.translation.query.x__target_entity_patterns__mutmut_18` | `target_entity_patterns` — case-flip | ineffective | — |
| `fastshaql.core.translation.query.x_translate_query__mutmut_5` | `translate_query` — XX-wrap | ineffective | — |
| `fastshaql.core.translation.query.x_translate_query__mutmut_6` | `translate_query` — case-flip | ineffective | — |
| `fastshaql.core.translation.query.x_translate_query__mutmut_8` | `translate_query` — XX-wrap | ineffective | — |
| `fastshaql.core.translation.query.x_translate_query__mutmut_9/10` | `translate_query` — case-flip | ineffective | — |
| `fastshaql.core.translation.query.x_translate_query__mutmut_11` | `translate_query` — XX-wrap | ineffective | — |
| `fastshaql.core.translation.query.x_translate_query__mutmut_12` | `translate_query` — case-flip | ineffective | — |

### `core.translation.selection`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.selection.x_iter_field_selections__mutmut_3/4/6` | `iter_field_selections` — argument → None | ineffective | — |

### `core.translation.variables`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_13` | `allocate` — argument → None | ineffective | — |
| `fastshaql.core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_14` | `allocate` — XX-wrap | ineffective | — |
| `fastshaql.core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_15` | `allocate` — case-flip | ineffective | — |

### `executable`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.executable.x__resolver_context__mutmut_4` | `resolver_context` — XX-wrap | ineffective | — |
## Import-time-computed tables

`_OPERATOR_FIELD_SPECS` (`schema/filters.py`) and the `select_scan` modifier
regexes (via `word_bounded_any`, `sparql/lex.py`) are computed at module
import, before mutmut arms its trampoline — forked test children inherit
the already-built objects, so schema-level assertions can never observe
mutations there. Direct unit calls at test time
(`unit/schema/test_filters.py`, `unit/sparql/test_lex.py`) are the *only*
mutation coverage for such tables; keep them direct if those modules are
restructured.
