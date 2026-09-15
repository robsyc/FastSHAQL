# Mutation survivor triage record

The committed record of mutation survivors we have triaged and deliberately
accept, so future sessions don't re-triage them. A mutant listed here is
settled: revisit an entry only with a stated reason. The score floor
([`mutmut-floor.json`](../mutmut-floor.json)) gates the score; this record
explains the residue it tolerates. Reproduce with `just mutate`; inspect a
survivor with `uv run mutmut show <id>`.

Regenerated 2026-09-12 from a fully-clean run (`just mutate-clean`) after
the polymorphic-relationships slice and the guard/allocator threading
refactor; numbers are current as of that run. Mutant numbers are
per-function and shift when the source changes — locate a survivor by
module + function + mutation shape, not by number alone. The floor moved
94.3 → 94.2 with this regeneration: every survivor below is individually
triaged equivalent or ineffective, so the residue the floor tolerates grew
by the refactor's accepted survivors — nothing killable remains.

Every survivor is one of two verdicts — no open gaps remain:

- **equivalent** — observably identical behavior. Recurring mechanisms:
  `typing.cast` is a runtime identity (its type argument is never
  consulted); a `None` or dropped argument equals the callee's default or
  falsy value; closed-union `match` arms (with `assert_never`) are
  unreachable; and the matchers involved (`find_keyword`, BCP 47 language
  lookup) are case-insensitive. mutmut 3.8.0 added ternary-condition and
  decorated-class-method mutants; their recurring equivalents: an unused
  parameter's default (the body never reads it — the `_indent` renders);
  a ternary whose dead arm carries the only difference (the value is read
  only on the arm both forms agree on); and `"_".join` over a one-element
  list, which is that element. Parallel-list `zip(..., strict=True)` pairs
  co-derived same-length inputs.
- **ineffective** — diagnostic text only: error/warning wording and
  error-context labels. Tests pin the identifier-bearing prefix of
  diagnostics, never full sentences, so wording mutants survive by design.

A Reason is recorded only where the verdict is not an instance of the
definitions above.

### `adapters.django`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `adapters.django.x_build_graphql_view__mutmut_2` | _build_graphql_view — value → None | ineffective | — |
| `adapters.django.x_build_graphql_view__mutmut_3` | _build_graphql_view — message XX-wrap | ineffective | — |
| `adapters.django.x_build_graphql_view__mutmut_4/5` | _build_graphql_view — message case-flip | ineffective | — |
| `adapters.django.x_build_graphql_view__mutmut_31` | _build_graphql_view — CONTENT_TYPE default "" → "XXXX" | equivalent | any default that is not `application/json` fails the envelope prefix check identically (415) |

### `core.execution.converter`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.execution.converter.x_coerce_value__mutmut_6` | _coerce_value — `raise TypeError(f"Unsupported SPARQL term type: {type(term)!r}")` → `raise TypeError(None)` | ineffective | — |
| `core.execution.converter.x_coerce_value__mutmut_7` | _coerce_value — `raise TypeError(f"Unsupported SPARQL term type: {type(term)!r}")` → `raise TypeError(f"Unsupported SPARQL term type: {type(None)!r}")` | ineffective | — |
| `core.execution.converter.x__apply_scalar_fields__mutmut_19` | __apply_scalar_fields — cast type → None | equivalent | — |
| `core.execution.converter.x__polymorphic_children__mutmut_9/12/13` | __polymorphic_children — for member, lane in zip(prop.union_members, binding.members,… | equivalent | binding.members runs parallel to prop.union_members by construction (built member-for-member in _translate_union_selection) — the strict check can never fire |
| `core.execution.converter.x__finalize_entity__mutmut_2` | __finalize_entity — `if isinstance(values, list) and field_name in shape.property_shapes:` → `if isinstance(values, list) or field_name in shape.property_shapes:` | equivalent | every list-valued entity key is written only for a kind.is_list property shape, so the not-in-shape side of the or never reaches the prop lookup |
| `core.execution.converter.x__finalize_entity__mutmut_9` | __finalize_entity — cast type → None | equivalent | — |

### `core.execution.store`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.execution.store.x_decode_sparql_results__mutmut_10` | _decode_sparql_results — cast type → None | equivalent | — |
| `core.execution.store.xǁInMemoryStoreǁquery__mutmut_7/11` | ǁInMemoryStoreǁquery — cast type → None | equivalent | — |

### `core.kernel.context`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.kernel.context.x_lang_tags_from_accept_language__mutmut_14` | _lang_tags_from_accept_language — `tag = segment.split(";", maxsplit=1)[0].strip().lower()` → `tag = segment.split(";", )[0].strip().lower()` | equivalent | element [0] of a split is unchanged by maxsplit |
| `core.kernel.context.x_lang_tags_from_accept_language__mutmut_17` | _lang_tags_from_accept_language — `tag = segment.split(";", maxsplit=1)[0].strip().lower()` → `tag = segment.split(";", maxsplit=2)[0].strip().lower()` | equivalent | element [0] of a split is unchanged by maxsplit |

### `core.kernel.identifiers`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.kernel.identifiers.x_raw_enum_member_name__mutmut_3` | _raw_enum_member_name — argument → None | ineffective | — |
| `core.kernel.identifiers.x_raw_enum_member_name__mutmut_4` | _raw_enum_member_name — `f"enum member must be an IRI or literal, got {type(term).__name__}"` → `f"enum member must be an IRI or literal, got {type(None).__name__}"` | ineffective | — |

### `core.kernel.io`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.kernel.io.x__expand_source__mutmut_3` | __expand_source — argument → None | ineffective | — |
| `core.kernel.io.x__expand_source__mutmut_4` | __expand_source — f"load_shapes expected str, Path, Graph, or sequence thereof… | ineffective | — |

### `core.parser.datatypes`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.datatypes.x_datatypes_from_shape__mutmut_20` | _datatypes_from_shape — message XX-wrap | ineffective | — |
| `core.parser.datatypes.x_datatypes_from_shape__mutmut_21/22` | _datatypes_from_shape — message case-flip | ineffective | — |
| `core.parser.datatypes.x_datatypes_from_shape__mutmut_26` | _datatypes_from_shape — message XX-wrap | ineffective | — |
| `core.parser.datatypes.x_datatypes_from_shape__mutmut_27/28` | _datatypes_from_shape — message case-flip | ineffective | — |
| `core.parser.datatypes.x__datatype_objects__mutmut_10` | __datatype_objects — message XX-wrap | ineffective | — |
| `core.parser.datatypes.x__datatype_objects__mutmut_11` | __datatype_objects — message case-flip | ineffective | — |
| `core.parser.datatypes.x__or_datatypes__mutmut_4` | __or_datatypes — diagnostic label → None | ineffective | — |
| `core.parser.datatypes.x__or_datatypes__mutmut_21/23` | __or_datatypes — message XX-wrap | ineffective | — |
| `core.parser.datatypes.x__or_datatypes__mutmut_24` | __or_datatypes — message case-flip | ineffective | — |
| `core.parser.datatypes.x__sole_datatype_constraint__mutmut_6` | __sole_datatype_constraint — predicates = set(graph.predicates(member, None)) - NON_VALID… | equivalent | same rdflib default-None identity |

### `core.parser.node_expr.filter_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.node_expr.filter_shape.x_parse_filter_shape__mutmut_3` | _parse_filter_shape — `return _parse_shape(graph, shape_node, inside_property=False)` → `return _parse_shape(graph, shape_node, inside_property=None)` | equivalent | None is the falsy reading — same as False |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_3` | __parse_shape — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_4` | __parse_shape — message case-flip | ineffective | — |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_32` | __parse_shape — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_66/67/68/69` | __parse_shape — f"shnex:filterShape sh:maxCount {graph.value(shape_node, SH.… | ineffective | — |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_70` | __parse_shape — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_71/72` | __parse_shape — message case-flip | ineffective | — |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_73` | __parse_shape — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__parse_shape__mutmut_74` | __parse_shape — message case-flip | ineffective | — |
| `core.parser.node_expr.filter_shape.x__has_value_conjuncts__mutmut_8` | __has_value_conjuncts — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__has_value_conjuncts__mutmut_9/10` | __has_value_conjuncts — message case-flip | ineffective | — |
| `core.parser.node_expr.filter_shape.x__class_conjuncts__mutmut_12` | __class_conjuncts — diagnostic label → None | ineffective | — |
| `core.parser.node_expr.filter_shape.x__pattern_conjuncts__mutmut_10` | __pattern_conjuncts — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__pattern_conjuncts__mutmut_11` | __pattern_conjuncts — message case-flip | ineffective | — |
| `core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_11` | __min_count_conjuncts — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_12/13` | __min_count_conjuncts — message case-flip | ineffective | — |
| `core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_19` | __min_count_conjuncts — message XX-wrap | ineffective | — |
| `core.parser.node_expr.filter_shape.x__min_count_conjuncts__mutmut_20/21` | __min_count_conjuncts — message case-flip | ineffective | — |

### `core.parser.node_expr.parse`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.node_expr.parse.x_parse_expr_object__mutmut_6` | _parse_expr_object — value → None | ineffective | — |
| `core.parser.node_expr.parse.x__sole_key_parameter__mutmut_14/20/26` | __sole_key_parameter — message XX-wrap | ineffective | — |
| `core.parser.node_expr.parse.x__sole_key_parameter__mutmut_27` | __sole_key_parameter — message case-flip | ineffective | — |
| `core.parser.node_expr.parse.x__sole_key_parameter__mutmut_58` | __sole_key_parameter — message XX-wrap | ineffective | — |
| `core.parser.node_expr.parse.x__sole_key_parameter__mutmut_59` | __sole_key_parameter — message case-flip | ineffective | — |
| `core.parser.node_expr.parse.x__parse_path_values__mutmut_4` | __parse_path_values — `path = parse_shacl_path_node(graph, path_node, expr_node)` → `path = parse_shacl_path_node(graph, path_node, None)` | ineffective | — |
| `core.parser.node_expr.parse.x__parse_path_values__mutmut_20` | __parse_path_values — message XX-wrap | ineffective | — |
| `core.parser.node_expr.parse.x__parse_path_values__mutmut_21` | __parse_path_values — message case-flip | ineffective | — |
| `core.parser.node_expr.parse.x__parse_if__mutmut_9/11` | __parse_if — message XX-wrap | ineffective | — |
| `core.parser.node_expr.parse.x__parse_if__mutmut_12/13` | __parse_if — message case-flip | ineffective | — |
| `core.parser.node_expr.parse.x__parse_constant_list__mutmut_11` | __parse_constant_list — message XX-wrap | ineffective | — |
| `core.parser.node_expr.parse.x__parse_constant_list__mutmut_12` | __parse_constant_list — message case-flip | ineffective | — |
| `core.parser.node_expr.parse.x__parse_instances_of__mutmut_13` | __parse_instances_of — message XX-wrap | ineffective | — |
| `core.parser.node_expr.parse.x__parse_instances_of__mutmut_14/15` | __parse_instances_of — message case-flip | ineffective | — |
| `core.parser.node_expr.parse.x__unsupported_message__mutmut_12/18` | __unsupported_message — message XX-wrap | ineffective | — |
| `core.parser.node_expr.parse.x__unsupported_message__mutmut_19/20` | __unsupported_message — message case-flip | ineffective | — |

### `core.parser.node_expr.select_scan`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_7` | _parse_shacl_select — message case-flip | equivalent | — |
| `core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_10` | _parse_shacl_select — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_34` | _parse_shacl_select — message case-flip | equivalent | — |
| `core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_37` | _parse_shacl_select — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_39` | _parse_shacl_select — `raise UnsupportedShapeError("sh:select must contain WHERE")` → `raise UnsupportedShapeError("SH:SELECT MUST CONTAIN WHERE")` | ineffective | — |
| `core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_54` | _parse_shacl_select — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x_parse_shacl_select__mutmut_55` | _parse_shacl_select — message case-flip | ineffective | — |
| `core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_3/8/11` | __extract_projection_var — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_12/13` | __extract_projection_var — message case-flip | ineffective | — |
| `core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_22` | __extract_projection_var — `if not vars_found:` → `if vars_found:` | ineffective | the flipped guard swaps which arm raises — same exception type, only the message differs |
| `core.parser.node_expr.select_scan.x__extract_projection_var__mutmut_24` | __extract_projection_var — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x__reject_trailing_suffix__mutmut_9` | __reject_trailing_suffix — `if m := _TOP_LEVEL_MODIFIERS_RE.search(suffix, start, end):` → `if m := _TOP_LEVEL_MODIFIERS_RE.search(suffix, start, ):` | ineffective | any non-blank code span raises either way — only the message choice changes |
| `core.parser.node_expr.select_scan.x__reject_trailing_suffix__mutmut_14` | __reject_trailing_suffix — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_5` | _validate_select_prebinding — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_7` | _validate_select_prebinding — message case-flip | ineffective | — |
| `core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_10` | _validate_select_prebinding — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_24` | _validate_select_prebinding — `continue  # malformed VALUES — defer to the triple store` → `break  # malformed VALUES — defer to the triple store` | equivalent | a later data block is found for the earlier match too — break and continue coincide |
| `core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_27` | _validate_select_prebinding — message XX-wrap | ineffective | — |
| `core.parser.node_expr.select_scan.x_validate_select_prebinding__mutmut_29` | _validate_select_prebinding — message case-flip | ineffective | — |

### `core.parser.node_expr.semantics`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.node_expr.semantics.x_arm_label__mutmut_10` | _arm_label — line deleted | equivalent | — |
| `core.parser.node_expr.semantics.x_arm_label__mutmut_15/23/26` | _arm_label — message XX-wrap | ineffective | — |
| `core.parser.node_expr.semantics.x_arm_label__mutmut_40` | _arm_label — `assert_never(unreachable)` → `assert_never(None)` | equivalent | — |
| `core.parser.node_expr.semantics.x_reject_derived_path_targets__mutmut_6` | _reject_derived_path_targets — line deleted | equivalent | — |
| `core.parser.node_expr.semantics.x_reject_derived_path_targets__mutmut_56` | _reject_derived_path_targets — `assert_never(unreachable)` → `assert_never(None)` | equivalent | — |
| `core.parser.node_expr.semantics.x__reject_derived_conjuncts__mutmut_11/12` | __reject_derived_conjuncts — _reject_derived_conjuncts(graph, conjunct.nested, shape_iri,… | ineffective | — |

### `core.parser.node_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.node_shape.x__parse_inherited_shape_iris__mutmut_11` | __parse_inherited_shape_iris — `return tuple(sorted(iris, key=str))` → `return tuple(sorted(iris, key=None))` | equivalent | URIRef is a str subclass — default comparison is str |
| `core.parser.node_shape.x__parse_inherited_shape_iris__mutmut_13` | __parse_inherited_shape_iris — `return tuple(sorted(iris, key=str))` → `return tuple(sorted(iris, ))` | equivalent | URIRef is a str subclass — dropped key is the identity default |
| `core.parser.node_shape.x_parse_node_shape__mutmut_2` | _parse_node_shape — `description_language: str = "en",` → `description_language: str = "EN",` | equivalent | — |
| `core.parser.node_shape.x_parse_node_shape__mutmut_40` | _parse_node_shape — message XX-wrap | ineffective | — |

### `core.parser.parse`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.parse.x__merge_parent_prop__mutmut_8/10/11` | __merge_parent_prop — value → None | ineffective | — |
| `core.parser.parse.x__merge_parent_prop__mutmut_19` | __merge_parent_prop — message XX-wrap | ineffective | — |
| `core.parser.parse.x__merge_parent_prop__mutmut_20` | __merge_parent_prop — message case-flip | ineffective | — |
| `core.parser.parse.x__merge_parent_prop__mutmut_22` | __merge_parent_prop — message XX-wrap | ineffective | — |
| `core.parser.parse.x__resolve_inheritance__mutmut_8` | __resolve_inheritance — message XX-wrap | ineffective | — |
| `core.parser.parse.x__make_synthetic_shape__mutmut_5/7` | __make_synthetic_shape — line deleted | equivalent | explicit None dropped — identical to the default |
| `core.parser.parse.x__collapse_single_member__mutmut_9/13` | __collapse_single_member — cast type → None | equivalent | — |
| `core.parser.parse.x__resolve_member__mutmut_16` | __resolve_member — cast type → None | equivalent | — |
| `core.parser.parse.x__resolve_member__mutmut_26` | __resolve_member — message XX-wrap | ineffective | — |
| `core.parser.parse.x__resolve_member__mutmut_27/28` | __resolve_member — message case-flip | ineffective | — |
| `core.parser.parse.x__resolve_member__mutmut_29` | __resolve_member — message XX-wrap | ineffective | — |
| `core.parser.parse.x__resolve_member__mutmut_30` | __resolve_member — message case-flip | ineffective | — |
| `core.parser.parse.x__reject_duplicate_members__mutmut_7` | __reject_duplicate_members — cast type → None | equivalent | — |
| `core.parser.parse.x__reject_duplicate_members__mutmut_13` | __reject_duplicate_members — message XX-wrap | ineffective | — |
| `core.parser.parse.x__reject_duplicate_members__mutmut_14` | __reject_duplicate_members — message case-flip | ineffective | — |
| `core.parser.parse.x__reject_duplicate_members__mutmut_21/26` | __reject_duplicate_members — cast type → None | equivalent | — |
| `core.parser.parse.x__reject_duplicate_members__mutmut_31` | __reject_duplicate_members — value → None | ineffective | — |
| `core.parser.parse.x__reject_duplicate_members__mutmut_32` | __reject_duplicate_members — message XX-wrap | ineffective | — |
| `core.parser.parse.x__reject_duplicate_members__mutmut_33` | __reject_duplicate_members — message case-flip | ineffective | — |
| `core.parser.parse.x_parse_shapes__mutmut_2` | _parse_shapes — def parse_shapes(graph: Graph, *, description_language: str … | equivalent | — |
| `core.parser.parse.x_parse_shapes__mutmut_11` | _parse_shapes — `shape_iris.setdefault(shape_iri, None)` → `shape_iris.setdefault(shape_iri, )` | equivalent | dropped trailing arg is the None default |

### `core.parser.property_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.property_shape.x__check_derived_field_boundaries__mutmut_16` | __check_derived_field_boundaries — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__and_class_values__mutmut_15` | __and_class_values — `values = list(graph.objects(member, SH_CLASS))` → `values = list(graph.objects(member, None))` | equivalent | the guard requires sh:class to be the member's only predicate, so all-objects equals the sh:class objects |
| `core.parser.property_shape.x__and_class_values__mutmut_17` | __and_class_values — `values = list(graph.objects(member, SH_CLASS))` → `values = list(graph.objects(member, ))` | equivalent | same — dropped trailing arg is the all-predicates default |
| `core.parser.property_shape.x__and_class_values__mutmut_22` | __and_class_values — `if set(graph.predicates(member, None)) != {SH_CLASS} or not all(` → `if set(graph.predicates(member, )) != {SH_CLASS} or not all(` | equivalent | same rdflib default-None identity |
| `core.parser.property_shape.x__class_values__mutmut_19` | __class_values — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__class_values__mutmut_20` | __class_values — message case-flip | ineffective | — |
| `core.parser.property_shape.x__class_values__mutmut_36` | __class_values — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__class_values__mutmut_37` | __class_values — message case-flip | ineffective | — |
| `core.parser.property_shape.x__class_values__mutmut_38` | __class_values — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__class_values__mutmut_39` | __class_values — message case-flip | ineffective | — |
| `core.parser.property_shape.x__class_values__mutmut_43` | __class_values — `values = tuple(sorted(flat, key=str))` → `values = tuple(sorted(flat, key=None))` | equivalent | URIRef is a str subclass — default sort compares as strings |
| `core.parser.property_shape.x__class_values__mutmut_45` | __class_values — `values = tuple(sorted(flat, key=str))` → `values = tuple(sorted(flat, ))` | equivalent | same — default key is the identity |
| `core.parser.property_shape.x__relationship_value_lane__mutmut_30/41` | __relationship_value_lane — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__relationship_value_lane__mutmut_42/43` | __relationship_value_lane — message case-flip | ineffective | — |
| `core.parser.property_shape.x__relationship_value_lane__mutmut_44` | __relationship_value_lane — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__relationship_value_lane__mutmut_45` | __relationship_value_lane — message case-flip | ineffective | — |
| `core.parser.property_shape.x__sole_node_ref__mutmut_10` | __sole_node_ref — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__sole_node_ref__mutmut_11/12` | __sole_node_ref — message case-flip | ineffective | — |
| `core.parser.property_shape.x__sole_node_ref__mutmut_13` | __sole_node_ref — message XX-wrap | ineffective | — |
| `core.parser.property_shape.x__sole_node_ref__mutmut_14/15` | __sole_node_ref — message case-flip | ineffective | — |
| `core.parser.property_shape.x_parse_property_shape__mutmut_2` | _parse_property_shape — `description_language: str = "en",` → `description_language: str = "EN",` | equivalent | — |
| `core.parser.property_shape.x_parse_property_shape__mutmut_50/77/126` | _parse_property_shape — message XX-wrap | ineffective | — |

### `core.parser.shacl_in`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.shacl_in.x_parse_shacl_in__mutmut_14` | _parse_shacl_in — members = strict_rdf_list(graph, in_heads[0], what=f"sh:in l… | ineffective | — |
| `core.parser.shacl_in.x_parse_shacl_in__mutmut_24` | _parse_shacl_in — value → None | ineffective | — |
| `core.parser.shacl_in.x_parse_shacl_in__mutmut_39` | _parse_shacl_in — cast type → None | ineffective | — |
| `core.parser.shacl_in.x_parse_shacl_in__mutmut_44/47` | _parse_shacl_in — message XX-wrap | ineffective | — |
| `core.parser.shacl_in.x_parse_shacl_in__mutmut_48` | _parse_shacl_in — message case-flip | ineffective | — |
| `core.parser.shacl_in.x_parse_shacl_in__mutmut_50` | _parse_shacl_in — message XX-wrap | ineffective | — |

### `core.parser.shacl_path`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.shacl_path.x__strict_path_list__mutmut_4` | __strict_path_list — `elements = strict_rdf_list(graph, head, what=f"{what} on {source}")` → `elements = strict_rdf_list(graph, head, what=None)` | ineffective | — |
| `core.parser.shacl_path.x__strict_path_list__mutmut_13` | __strict_path_list — `parse_shacl_path_node(graph, element, source, ancestors=nested)` → `parse_shacl_path_node(graph, element, None, ancestors=nested)` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path__mutmut_16` | _parse_shacl_path — `return parse_shacl_path_node(graph, path_node, prop_shape)` → `return parse_shacl_path_node(graph, path_node, None)` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_3` | _parse_shacl_path_node — message XX-wrap | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_4/5` | _parse_shacl_path_node — message case-flip | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_18` | _parse_shacl_path_node — message XX-wrap | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_25` | _parse_shacl_path_node — if (operand := sole_object(graph, node, predicate, what=name… | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_34` | _parse_shacl_path_node — `parse_shacl_path_node(graph, operand, source, ancestors=nested)` → `parse_shacl_path_node(graph, operand, None, ancestors=nested)` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_55` | _parse_shacl_path_node — `parse_shacl_path_node(graph, inverse, source, ancestors=nested)` → `parse_shacl_path_node(graph, inverse, None, ancestors=nested)` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_64` | _parse_shacl_path_node — diagnostic label → None | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_69` | _parse_shacl_path_node — message XX-wrap | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_70` | _parse_shacl_path_node — `graph, node, SH.alternativePath, what="sh:alternativePath"` → `graph, node, SH.alternativePath, what="sh:alternativepath"` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_71` | _parse_shacl_path_node — `graph, node, SH.alternativePath, what="sh:alternativePath"` → `graph, node, SH.alternativePath, what="SH:ALTERNATIVEPATH"` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_76/77` | _parse_shacl_path_node — diagnostic label → None | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_78` | _parse_shacl_path_node — value → None | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_86` | _parse_shacl_path_node — message XX-wrap | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_87` | _parse_shacl_path_node — message case-flip | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_88` | _parse_shacl_path_node — `what="sh:alternativePath list",` → `what="SH:ALTERNATIVEPATH LIST",` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_89` | _parse_shacl_path_node — message XX-wrap | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_98/99` | _parse_shacl_path_node — diagnostic label → None | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_100` | _parse_shacl_path_node — value → None | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_108` | _parse_shacl_path_node — message XX-wrap | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_109` | _parse_shacl_path_node — `what="sh:path sequence list",` → `what="SH:PATH SEQUENCE LIST",` | ineffective | — |
| `core.parser.shacl_path.x_parse_shacl_path_node__mutmut_110` | _parse_shacl_path_node — message XX-wrap | ineffective | — |

### `core.parser.targets`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.targets.x__unsupported_target__mutmut_2` | __unsupported_target — message XX-wrap | ineffective | — |
| `core.parser.targets.x__unsupported_target__mutmut_3/4` | __unsupported_target — message case-flip | ineffective | — |
| `core.parser.targets.x__unsupported_target__mutmut_5` | __unsupported_target — message XX-wrap | ineffective | — |
| `core.parser.targets.x__unsupported_target__mutmut_6` | __unsupported_target — message case-flip | ineffective | — |
| `core.parser.targets.x__reject_unsupported__mutmut_6` | __reject_unsupported — `raise _unsupported_target(shape_iri, predicate)` → `raise _unsupported_target(None, predicate)` | ineffective | — |
| `core.parser.targets.x__reject_unsupported__mutmut_16` | __reject_unsupported — message XX-wrap | ineffective | — |
| `core.parser.targets.x__reject_unsupported__mutmut_17` | __reject_unsupported — message case-flip | ineffective | — |
| `core.parser.targets.x__reject_unsupported__mutmut_19` | __reject_unsupported — message XX-wrap | ineffective | — |
| `core.parser.targets.x__reject_unsupported__mutmut_20` | __reject_unsupported — message case-flip | ineffective | — |
| `core.parser.targets.x__reject_unsupported__mutmut_33` | __reject_unsupported — `raise _unsupported_target(shape_iri, predicate)` → `raise _unsupported_target(None, predicate)` | ineffective | — |
| `core.parser.targets.x_parse_target__mutmut_22/25` | _parse_target — message XX-wrap | ineffective | — |
| `core.parser.targets.x_parse_target__mutmut_26` | _parse_target — `("sh:targetClass", target_class is not None),` → `("sh:targetclass", target_class is not None),` | ineffective | — |
| `core.parser.targets.x_parse_target__mutmut_27` | _parse_target — `("sh:targetClass", target_class is not None),` → `("SH:TARGETCLASS", target_class is not None),` | ineffective | — |
| `core.parser.targets.x_parse_target__mutmut_29/37` | _parse_target — message XX-wrap | ineffective | — |

### `core.parser.unions`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.unions.x_sh_or_members__mutmut_35` | _sh_or_members — value → None | equivalent | the flag is only read in boolean context — None and False are both falsy |
| `core.parser.unions.x_sh_or_members__mutmut_37` | _sh_or_members — value → None | equivalent | same — boolean context only |
| `core.parser.unions.x_sh_or_members__mutmut_54` | _sh_or_members — message XX-wrap | ineffective | — |
| `core.parser.unions.x_sh_or_members__mutmut_55` | _sh_or_members — message case-flip | ineffective | — |
| `core.parser.unions.x_sh_or_members__mutmut_56` | _sh_or_members — message XX-wrap | ineffective | — |
| `core.parser.unions.x_sh_or_members__mutmut_57` | _sh_or_members — message case-flip | ineffective | — |
| `core.parser.unions.x__sole_value_constraint__mutmut_6` | __sole_value_constraint — predicates = set(graph.predicates(member, None)) - NON_VALID… | equivalent | rdflib predicates() defaults its second argument to None — dropped trailing arg is the same call |
| `core.parser.unions.x__sole_value_constraint__mutmut_27/29` | __sole_value_constraint — message XX-wrap | ineffective | — |
| `core.parser.unions.x__sole_value_constraint__mutmut_30` | __sole_value_constraint — `f"(got {', '.join(repr(o) for o in objects) or 'no value'})"` → `f"(got {', '.join(repr(o) for o in objects) or 'NO VALUE'})"` | ineffective | — |

### `core.parser.util.graph_reads`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.util.graph_reads.x__pick_localized_literal__mutmut_9` | __pick_localized_literal — message XX-wrap | ineffective | — |
| `core.parser.util.graph_reads.x_first_localized_str__mutmut_2` | _first_localized_str — `lang: str = "en",` → `lang: str = "EN",` | equivalent | — |
| `core.parser.util.graph_reads.x_strict_rdf_list__mutmut_28` | _strict_rdf_list — message XX-wrap | ineffective | — |

### `core.parser.util.identifiers`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.util.identifiers.x_read_code_identifier__mutmut_25` | _read_code_identifier — message XX-wrap | ineffective | — |
| `core.parser.util.identifiers.x_read_code_identifier__mutmut_26/27` | _read_code_identifier — message case-flip | ineffective | — |
| `core.parser.util.identifiers.x_finalize_graphql_name__mutmut_4` | _finalize_graphql_name — message XX-wrap | ineffective | — |
| `core.parser.util.identifiers.x_finalize_graphql_name__mutmut_5/6` | _finalize_graphql_name — message case-flip | ineffective | — |

### `core.parser.visibility`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_5` | __demote_untargeted_public_shapes — value → None | ineffective | — |
| `core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_7` | __demote_untargeted_public_shapes — `shape.iri,` → `)` | ineffective | — |
| `core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_8/11` | __demote_untargeted_public_shapes — message XX-wrap | ineffective | — |
| `core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_12/13` | __demote_untargeted_public_shapes — message case-flip | ineffective | — |
| `core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_14` | __demote_untargeted_public_shapes — message XX-wrap | ineffective | — |
| `core.parser.visibility.x__demote_untargeted_public_shapes__mutmut_15` | __demote_untargeted_public_shapes — message case-flip | ineffective | — |
| `core.parser.visibility.x__reject_excluded_targets__mutmut_1` | __reject_excluded_targets — `if target is None or _is_synthetic(target):` → `if target is None and _is_synthetic(target):` | equivalent | synthetic member targets classify PROTECTED (never EXCLUDED) unless a schema declares the parser-minted synthetic IRI private — contrived beyond construction |
| `core.parser.visibility.x__reject_excluded_targets__mutmut_3` | __reject_excluded_targets — `if target is None or _is_synthetic(target):` → `if target is None or _is_synthetic(None):` | equivalent | synthetic member targets classify PROTECTED (never EXCLUDED) unless a schema declares the parser-minted synthetic IRI private — contrived beyond construction |
| `core.parser.visibility.x_resolve_visibility__mutmut_12/19/33` | _resolve_visibility — message XX-wrap | ineffective | — |

### `core.registry`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.registry.xǁShapeRegistryǁresolve_relationship_target__mutmut_1` | `resolve_relationship_target` — label → None | ineffective | the label appears only in the two ValueError texts |

### `core.schema._gql`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.schema._gql.x_input_object__mutmut_1` | _input_object — cast type → None | equivalent | — |
| `core.schema._gql.x_object_type__mutmut_1` | _object_type — cast type → None | equivalent | — |
| `core.schema._gql.x_enum_type__mutmut_1` | _enum_type — cast type → None | equivalent | — |
| `core.schema._gql.x_union_type__mutmut_1` | _union_type — cast type → None | equivalent | — |

### `core.schema.build`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.schema.build.x_build_schema__mutmut_6` | _build_schema — message XX-wrap | equivalent | no synthesized name can be "Query": {Parent}{Field} always capitalizes the field part, and filter-input names end in Filter |
| `core.schema.build.x_build_schema__mutmut_7` | _build_schema — message case-flip | equivalent | no synthesized name can be "Query": {Parent}{Field} always capitalizes the field part, and filter-input names end in Filter |
| `core.schema.build.x_build_schema__mutmut_8` | _build_schema — `taken: set[str] = {"Query"} | set(operator_inputs)` → `taken: set[str] = {"QUERY"} | set(operator_inputs)` | equivalent | no synthesized name can be "Query": {Parent}{Field} always capitalizes the field part, and filter-input names end in Filter |

### `core.schema.fields`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.schema.fields.x_wrap_field_type__mutmut_6` | _wrap_field_type — cast type → None | equivalent | — |
| `core.schema.fields.x_wrap_field_type__mutmut_10` | _wrap_field_type — cast type → None | equivalent | — |

### `core.sparql.expressions`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.sparql.expressions.xǁTermExprǁrender__mutmut_1` | ǁTermExprǁrender — unused indent default 0 → 1 | equivalent | the body `del indent`s it — the default is never read |
| `core.sparql.expressions.xǁRawSparqlExprǁrender__mutmut_1` | ǁRawSparqlExprǁrender — unused indent default 0 → 1 | equivalent | same — the body `del indent`s it |

### `core.sparql.lex`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.sparql.lex.x_find_keyword__mutmut_9` | _find_keyword — `if span_end <= start:` → `if span_end < start:` | equivalent | a zero-width search window can never match a non-empty keyword |
| `core.sparql.lex.x_map_code_spans__mutmut_2` | _map_code_spans — value → None | equivalent | None is 0 as a slice start |
| `core.sparql.lex.x_extract_braced_body__mutmut_6` | _extract_braced_body — message XX-wrap | ineffective | — |
| `core.sparql.lex.x_extract_braced_body__mutmut_7` | _extract_braced_body — message case-flip | ineffective | — |
| `core.sparql.lex.x_extract_braced_body__mutmut_12` | _extract_braced_body — value → None | equivalent | the guard guarantees { at open_brace; the first loop iteration overwrites the initializer before the return slice |
| `core.sparql.lex.x_extract_braced_body__mutmut_13` | _extract_braced_body — `body_start = -1` → `body_start = +1` | equivalent | the guard guarantees { at open_brace; the first loop iteration overwrites the initializer before the return slice |
| `core.sparql.lex.x_extract_braced_body__mutmut_14` | _extract_braced_body — `body_start = -1` → `body_start = -2` | equivalent | the guard guarantees { at open_brace; the first loop iteration overwrites the initializer before the return slice |
| `core.sparql.lex.x_extract_braced_body__mutmut_49` | _extract_braced_body — message XX-wrap | ineffective | — |
| `core.sparql.lex.x_extract_braced_body__mutmut_50` | _extract_braced_body — message case-flip | ineffective | — |

### `core.sparql.paths`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.sparql.paths.xǁPredicatePathǁrender__mutmut_1` and the sibling path renders (`SequencePath`, `AlternativePath`, `InversePath`, `OneOrMorePath`, `ZeroOrMorePath`, `ZeroOrOnePath`) | `render` — unused `_indent` default 0 → 1 | equivalent | path renders never read `_indent` — the default is dead |

### `core.sparql.queries`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.sparql.queries.x__validate_solution_modifiers__mutmut_6/14` | __validate_solution_modifiers — message XX-wrap | ineffective | — |
| `core.sparql.queries.xǁSelectQueryǁrender__mutmut_15/18` | ǁSelectQueryǁrender — subquery-pad ternary mutated | equivalent | `pad` is read only on the `as_subquery` arm, where `or True` and the mutated else coincide |
| `core.sparql.queries.xǁSelectQueryǁrender__mutmut_21/24` | ǁSelectQueryǁrender — content-indent ternary mutated | equivalent | the top-level arm never reads `content_indent` (WHERE renders at its own default) |
| `core.sparql.queries.xǁSelectQueryǁrender__mutmut_27` | ǁSelectQueryǁrender — `cp` ternary `or True` | equivalent | on the top-level arm `content_indent` is 0, so `cp` is `""` either way |
| `core.sparql.queries.xǁSelectQueryǁrender__mutmut_33` | ǁSelectQueryǁrender — where-body ternary `or True` | equivalent | `where.render(0)` equals `where.render()` and `lstrip()` is a no-op on a `{`-led block |

### `core.translation.field_binding`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.field_binding.x_reject_polymorphic_filter__mutmut_4` | _reject_polymorphic_filter — message XX-wrap | ineffective | — |
| `core.translation.field_binding.x_begin_relationship_selection__mutmut_10` | _begin_relationship_selection — value → None | equivalent | the skipped reserve is defensive: allocator-minted names cannot contain the guard's double-underscore form, so no allocation can ever collide with it |
| `core.translation.field_binding.xǁFieldBindingsǁbind_promoted_fields__mutmut_22` | ǁFieldBindingsǁbind_promoted_fields — project=False → None | equivalent | `if project:` — None is falsy, identical to False |

### `core.translation.filter_shape`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.filter_shape.x__translate_conjunct__mutmut_8` | __translate_conjunct — line deleted | equivalent | closed-union arm — unreachable (parser rejects node-level minCount) |
| `core.translation.filter_shape.x__translate_conjunct__mutmut_9` | __translate_conjunct — line deleted | equivalent | — |
| `core.translation.filter_shape.x__translate_conjunct__mutmut_108` | __translate_conjunct — value → None | equivalent | the raise is unreachable (pragma: the parser rejects node-level minCount) — a dead diagnostic |
| `core.translation.filter_shape.x__translate_conjunct__mutmut_109` | __translate_conjunct — message XX-wrap | ineffective | — |
| `core.translation.filter_shape.x__translate_conjunct__mutmut_110/111` | __translate_conjunct — message case-flip | ineffective | — |
| `core.translation.filter_shape.x__translate_conjunct__mutmut_112` | __translate_conjunct — `assert_never(unreachable)` → `assert_never(None)` | equivalent | the raise is unreachable (pragma: the parser rejects node-level minCount) — a dead diagnostic |

### `core.translation.filters.exists_scope`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.filters.exists_scope.xǁRootFilterContextǁscalar_var__mutmut_2` | `scalar_var` — unreachable raise text → None | equivalent | the promotion invariant pre-binds every filter field — the KeyError arm never runs |
| `fastshaql.core.translation.filters.exists_scope.xǁRootFilterContextǁtranslate_relationship__mutmut_6` | `translate_relationship` — unreachable raise text → None | equivalent | same — relationships are pre-bound before WHERE translation |

### `core.translation.filters.literals`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.filters.literals.x_value_to_literal__mutmut_5/6` | _value_to_literal — line deleted | equivalent | deleted arm falls through to the same None return |

### `core.translation.filters.operators`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.filters.operators.x_translate_scalar_ops__mutmut_23` | _translate_scalar_ops — value → None | equivalent | boolean flag → None — None is falsy, same as False |
| `core.translation.filters.operators.x_translate_scalar_ops__mutmut_25` | _translate_scalar_ops — iri_values=False → None | equivalent | every use is a truthiness check — None is falsy, identical to False |
| `core.translation.filters.operators.x__enum_term__mutmut_4` | __enum_term — `if term is None or not isinstance(term, (URIRef, Literal)):` → `if term is None and not isinstance(term, (URIRef, Literal)):` | equivalent | the parser guarantees enum terms are URIRef/Literal |
| `core.translation.filters.operators.x_translate_operator_field__mutmut_20` | _translate_operator_field — `literal = value_to_literal(op_field.value, XSD.string)` → `literal = value_to_literal(op_field.value, None)` | equivalent | XSD.string and None produce the same plain literal |

### `core.translation.filters.where`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.filters.where.x__extract_int_argument__mutmut_5` | __extract_int_argument — value → None | ineffective | — |
| `core.translation.filters.where.x_extract_where_argument__mutmut_6` | _extract_where_argument — value → None | ineffective | — |
| `core.translation.filters.where.x_extract_where_argument__mutmut_7` | _extract_where_argument — message XX-wrap | ineffective | — |
| `core.translation.filters.where.x_extract_where_argument__mutmut_8` | _extract_where_argument — message case-flip | ineffective | — |
| `core.translation.filters.where.xǁ_FieldTranslatorǁ__init____mutmut_1` | ǁ_FieldTranslatorǁ__init__ — value → None | equivalent | the shape attribute is never read after assignment |
| `core.translation.filters.where.xǁ_FieldTranslatorǁon_property__mutmut_4` | ǁ_FieldTranslatorǁon_property — value → None | ineffective | — |
| `core.translation.filters.where.x_translate_fields__mutmut_2` | _translate_fields — `translator = _FieldTranslator(shape, ctx, registry)` → `translator = _FieldTranslator(None, ctx, registry)` | equivalent | the shape attribute is never read after assignment |

### `core.translation.joins`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.joins.x_relationship_join_patterns__mutmut_18` | _relationship_join_patterns — `relationship_type_patterns(child_subject, prop, allocator=allocator)` → `relationship_type_patterns(child_subject, prop, allocator=None)` | equivalent | same — the reserve is defensive against an unmintable name |
| `core.translation.joins.x_relationship_join_patterns__mutmut_21` | _relationship_join_patterns — `relationship_type_patterns(child_subject, prop, allocator=allocator)` → `relationship_type_patterns(child_subject, prop, )` | equivalent | same — the reserve is defensive against an unmintable name |
| `core.translation.joins.x_relationship_link_patterns__mutmut_10` | _relationship_link_patterns — value → None | equivalent | the raise is unreachable (pragma: source is DERIVED iff values_expr is set) — a dead diagnostic |
| `core.translation.joins.x_relationship_type_patterns__mutmut_5` | _relationship_type_patterns — `allocator.reserve(str(guard_var))` → `allocator.reserve(str(None))` | equivalent | the reserve's collision target is unreachable (double-underscore guard names are never allocator-minted); reserving a wrong string is equally inert |
| `core.translation.joins.x_membership_guard__mutmut_6` | _membership_guard — cast type → None | equivalent | — |

### `core.translation.node_expr`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.node_expr.x__translate__mutmut_10` | __translate — line deleted | equivalent | — |
| `core.translation.node_expr.x__translate__mutmut_105` | __translate — `assert_never(unreachable)` → `assert_never(None)` | equivalent | — |
| `core.translation.node_expr.x__condition__mutmut_24` | __condition — `return [], Condition(_strict_true(pure), total=False)` → `return [], Condition(_strict_true(pure), total=None)` | equivalent | None is falsy — same as False |
| `core.translation.node_expr.x__pure_branch__mutmut_20` | __pure_branch — case IfNodeExpr(cond=c, then=t, otherwise=o) if t is not Non… | equivalent | a None branch fails the pure walk either way |

### `core.translation.paths`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.paths.x_map_shacl_path_to_sparql_path__mutmut_16` | _map_shacl_path_to_sparql_path — value → None | ineffective | — |
| `core.translation.paths.x_map_shacl_path_to_sparql_path__mutmut_17` | _map_shacl_path_to_sparql_path — `f"Unsupported SHACL property path type: {type(path).__name__}"` → `f"Unsupported SHACL property path type: {type(None).__name__}"` | ineffective | — |

### `core.translation.patterns`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.patterns.x__raw_core__mutmut_3` | __raw_core — value → None | ineffective | — |
| `core.translation.patterns.x_scalar_bind_patterns__mutmut_51` | _scalar_bind_patterns — `*wrap_if_unbound(_raw_core(prop, inner, subject), bound=False),` → `*wrap_if_unbound(_raw_core(prop, inner, subject), bound=None),` | equivalent | None is falsy — same as bound=False |

### `core.translation.query`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.query.x_translate_query__mutmut_5` | _translate_query — message XX-wrap | ineffective | — |
| `core.translation.query.x_translate_query__mutmut_6` | _translate_query — message case-flip | ineffective | — |
| `core.translation.query.x_translate_query__mutmut_8` | _translate_query — message XX-wrap | ineffective | — |
| `core.translation.query.x_translate_query__mutmut_9/10` | _translate_query — message case-flip | ineffective | — |
| `core.translation.query.x_translate_query__mutmut_11` | _translate_query — message XX-wrap | ineffective | — |
| `core.translation.query.x_translate_query__mutmut_12` | _translate_query — message case-flip | ineffective | — |
| `core.translation.query.x__target_entity_patterns__mutmut_16` | __target_entity_patterns — message XX-wrap | ineffective | — |
| `core.translation.query.x__target_entity_patterns__mutmut_17` | __target_entity_patterns — message case-flip | ineffective | — |

### `core.translation.selection`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.selection.x__translate_union_selection__mutmut_36` | __translate_union_selection — `zip(prop.union_members, member_shapes, strict=True), start=1` → `zip(prop.union_members, member_shapes, strict=None), start=1` | equivalent | member_shapes is derived from prop.union_members one statement earlier — same length by construction, the strict check can never fire |
| `core.translation.selection.x__translate_union_selection__mutmut_39` | __translate_union_selection — `zip(prop.union_members, member_shapes, strict=True), start=1` → `zip(prop.union_members, member_shapes, ), start=1` | equivalent | same — co-derived zip inputs |
| `core.translation.selection.x__translate_union_selection__mutmut_40` | __translate_union_selection — `zip(prop.union_members, member_shapes, strict=True), start=1` → `zip(prop.union_members, member_shapes, strict=False), start=1` | equivalent | same — co-derived zip inputs |
| `core.translation.selection.x__translate_union_selection__mutmut_71` | __translate_union_selection — cast type → None | equivalent | — |
| `core.translation.selection.x__translate_union_selection__mutmut_76` | __translate_union_selection — members.append(MemberBinding(member.class_iri, member_scope.… | equivalent | the converter's stamping lanes read classes from prop.union_members; the binding's class_iri is structurally parallel but never consulted for lookups |
| `core.translation.selection.x__translate_union_selection__mutmut_97` | __translate_union_selection — `bound=bindings.field_is_bound(prop, field_name),` → `bound=bindings.field_is_bound(prop, None),` | equivalent | promotion binding rejects polymorphic fields (reject_polymorphic_filter, even for a null filter value) before any translation completes, so the promoted clause never reaches a completing union selection; unpromoted, None-in-set and name-in-set both compute is_required |
| `core.translation.selection.x__union_fragments__mutmut_6` | __union_fragments — message XX-wrap | ineffective | — |
| `core.translation.selection.x__union_fragments__mutmut_7` | __union_fragments — message case-flip | ineffective | — |
| `core.translation.selection.x__union_fragments__mutmut_11` | __union_fragments — cast type → None | equivalent | — |

### `core.translation.scope`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `fastshaql.core.translation.scope.xǁTranslationScopeǁappend_projection__mutmut_2` | `append_projection` — seen-set add(var) → add(None) | equivalent | membership is only queried with real `Variable`s — a None member never matches |

### `core.translation.variables`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_3` | ǁVariableAllocatorǁallocate — scoping ternary `or True` | equivalent | `"_".join([stem])` is `stem` — the empty-scope arm yields the same variable |
| `core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_13` | ǁVariableAllocatorǁallocate — value → None | ineffective | — |
| `core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_14` | ǁVariableAllocatorǁallocate — message XX-wrap | ineffective | — |
| `core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_15` | ǁVariableAllocatorǁallocate — message case-flip | ineffective | — |
| `core.translation.variables.xǁVariableAllocatorǁallocate__mutmut_16/17` | ǁVariableAllocatorǁallocate — unreachable raise text XX-wrap/case-flip | equivalent | `count(2)` always yields a fresh name — the raise never runs |

### `executable`

| Mutant | Mutation | Verdict | Reason |
|---|---|---|---|
| `executable.x__resolver_context__mutmut_4` | __resolver_context — message XX-wrap | ineffective | — |

## Import-time-computed tables

`_OPERATOR_FIELD_SPECS` (`schema/filters.py`) and the `select_scan` modifier
regexes (via `word_bounded_any`, `sparql/lex.py`) are computed at module
import, before mutmut arms its trampoline — forked test children inherit
the already-built objects, so schema-level assertions can never observe
mutations there. Direct unit calls at test time
(`unit/schema/test_filters.py`, `unit/sparql/test_lex.py`) are the *only*
mutation coverage for such tables; keep them direct if those modules are
restructured. The same mechanism covers `NON_VALIDATING_MEMBER_PREDICATES`
(`parser/unions.py`): `unit/parser/test_unions.py` parametrizes over the
live frozenset, so a table entry must land there to stay covered.
