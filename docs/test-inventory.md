# Test Inventory

**Total:** 340 tests across 30 files
**Run all:** `python3 -m pytest tests/ -q`

---

## Test Files

### 1. `test_schema_compliance.py`
Validates all patterns comply with `pattern-schema.yaml` and checks for legacy/removed fields.

| Test | Description |
|------|-------------|
| `test_all_patterns_comply_with_schema` | All patterns must validate against pattern-schema.yaml |
| `test_no_compatibility_field` | No patterns should have legacy `compatibility` field (removed in Part 2A) |
| `test_no_generic_variant_fields` | No patterns should have `generic` or `variant_of` fields (removed in Part 2A) |
| `test_schema_file_loadable` | pattern-schema.yaml must be valid YAML with correct structure |
| `test_schema_required_fields_reasonable` | Schema required fields match current pattern structure |

---

### 2. `test_pattern_schema_validation.py`
Uses `audit_patterns.py` tool to validate all patterns against schema.

| Test | Description |
|------|-------------|
| `test_all_patterns_valid_schema` | All patterns must conform to pattern-schema.yaml (via audit_patterns.py) |
| `test_all_pattern_files_loadable` | All pattern JSON files must be valid JSON with id field matching filename |
| `test_pattern_required_fields` | All patterns must have core required fields (id, version, title, description, etc.) |
| `test_pattern_supports_fields` | All patterns must have `supports_nfr` and `supports_constraints` (Part 2A requirement) |
| `test_no_excluded_if_fields` | No patterns should have legacy `excludedIf` field (removed in Part 2A) |

---

### 3. `test_phase2_merge.py`
Tests Phase 2 merge-with-defaults functionality.

| Test | Description |
|------|-------------|
| `test_merge_tracks_only_defaults` | Only defaulted fields tracked in assumptions, not user-provided values |
| `test_merge_nested_nfr` | Nested NFR objects merged correctly with proper assumption tracking |

---

### 4. `test_phase3_2_nfr.py`
Unit tests for Phase 3.2 `supports_nfr` filtering.

| Test | Description |
|------|-------------|
| `test_no_spec_nfr_all_pass` | If spec has no NFR section, all patterns pass |
| `test_empty_nfr_excluded_when_spec_has_nfr` | Empty `supports_nfr` rejected when spec has NFR requirements |
| `test_matching_nfr_included` | Pattern with matching NFR rules is included |

---

### 5. `test_phase3_4_defaultconfig.py`
Unit tests for Phase 3.4 defaultConfig merge.

| Test | Description |
|------|-------------|
| `test_merge_full_defaultconfig` | User didn't provide config → all defaults merged into assumptions |
| `test_user_provided_config_not_in_assumptions` | User provided config → pattern NOT in assumptions |
| `test_pattern_without_defaultconfig` | Pattern without defaultConfig → empty `{}` in assumptions |

---

### 6. `test_pattern_config_validation.py`
Comprehensive tests for pattern configuration validation and assumptions merging.

| Test | Description |
|------|-------------|
| `test_no_user_patterns` | Validation passes when no user patterns provided |
| `test_pattern_not_in_registry` | Validation fails when pattern not found in registry |
| `test_pattern_without_config_schema` | Validation passes for patterns without configSchema |
| `test_pattern_with_empty_config_schema` | Validation passes for patterns with empty properties |
| `test_valid_complete_config` | Validation passes with all required fields provided |
| `test_missing_required_fields` | Validation fails with missing required fields |
| `test_extra_fields` | Validation fails with extra fields not in schema |
| `test_empty_config_with_required_fields` | Validation fails with empty config when schema has fields |
| `test_both_missing_and_extra_fields` | Validation reports both missing and extra fields |
| `test_multiple_patterns_with_errors` | Validation reports errors for multiple patterns |
| `test_mixed_valid_and_invalid_patterns` | Validation fails if any pattern has errors |
| `test_merge_includes_patterns_without_default_config` | All selected patterns appear in assumptions |
| `test_merge_skips_user_provided_configs` | Patterns with user-provided config NOT in assumptions |
| `test_merge_with_empty_selected_patterns` | No patterns selected → `assumptions.patterns` empty or absent |
| `test_merge_multiple_patterns_with_defaults` | Multiple patterns with defaultConfig all merged correctly |
| `test_merge_preserves_existing_assumptions` | Merging preserves other assumptions sections |
| `test_merge_pattern_not_in_registry` | Pattern ID in selected list but not in registry → raises KeyError |
| `test_merge_complex_defaultconfig` | Pattern with nested/complex defaultConfig structure |

---

### 7. `test_assumptions_preservation.py`
Tests that assumptions are preserved during recompilation with proper merging.

| Test | Description |
|------|-------------|
| `test_preserve_partial_assumptions_operating_model` | Partial assumptions preserved, missing fields merged |
| `test_preserve_custom_assumption_values` | Custom values (different from defaults) are preserved |
| `test_no_merge_when_assumptions_complete` | Complete assumptions unchanged during merge |
| `test_add_new_assumption_sections` | Add missing assumption sections from defaults |
| `test_fresh_spec_normal_merge` | Fresh spec with no assumptions gets normal merge |

---

### 8. `test_user_input_precedence.py`
Tests that user input takes precedence over assumptions.

| Test | Description |
|------|-------------|
| `test_user_constraints_override_assumptions` | User-provided constraints override assumptions |
| `test_user_nfr_override_assumptions` | User-provided NFR values override assumptions |
| `test_user_operating_model_override_assumptions` | User-provided operating_model values override assumptions |
| `test_fresh_spec_no_redundancy_check` | Fresh specs work normally without redundancy check |

---

### 9. `test_phase4_cost.py`
Unit tests for Phase 4 cost feasibility check.

| Test | Description |
|------|-------------|
| `test_no_warnings_under_budget` | No warnings when costs under ceilings |
| `test_warning_opex_exceeds_ceiling_minimize_opex` | Warning when opex exceeds ceiling (minimize-opex intent) |
| `test_warning_capex_exceeds_ceiling_minimize_capex` | Warning when capex exceeds ceiling (minimize-capex intent) |
| `test_warning_tco_exceeds_ceiling_optimize_tco` | Warning when TCO exceeds combined ceiling (optimize-tco intent) |
| `test_ops_team_cost_calculation` | Ops team cost calculated correctly with new parameters |

---

### 10. `test_requirements_tracing.py`
Unit tests for requirements tracing helper functions.

| Test | Description |
|------|-------------|
| `test_build_index_simple` | Building inverse index with simple rules |
| `test_build_index_empty` | Building index with no rules |
| `test_format_pattern_list_short` | Formatting when ≤ 3 patterns |
| `test_format_pattern_list_long` | Formatting when > 3 patterns |
| `test_metadata_comments_free_tier` | Metadata-based comments for free tier patterns |
| `test_metadata_comments_free_tier_false` | No comment when `prefer_free_tier_if_possible` is false |

---

### 11. `test_pattern_schema_regression.py`
Regression tests for pattern schema validation after bulk updates.

| Test | Description |
|------|-------------|
| `test_all_patterns_validate_against_schema` | All patterns must validate against pattern-schema.yaml |
| `test_no_patterns_have_config_schema_required` | No patterns should have `configSchema.required` (Task 3 removal) |
| `test_patterns_with_config_schema_have_properties` | Patterns with configSchema must have properties defined |
| `test_default_config_matches_config_schema` | defaultConfig and configSchema must have matching keys |
| `test_config_schema_has_valid_structure` | configSchema must have valid JSON Schema structure |
| `test_default_config_values_match_schema_types` | defaultConfig values must match schema types |
| `test_default_config_values_satisfy_schema_constraints` | defaultConfig values must satisfy enum/min/max constraints |
| `test_patterns_count` | Verify expected number of patterns exists (regression check) |

---

### 12. `test_requirements_tracing_integration.py`
Integration tests for requirements tracing in verbose mode (exercises `test-specs/`).

| Test | Description |
|------|-------------|
| `test_requirements_tracing_verbose` | Verbose mode adds inline comments to compiled-spec.yaml |
| `test_non_verbose_no_comments` | Non-verbose mode has no pattern comments |
| `test_verbose_assumptions_patterns_have_description_comments` | Pattern keys in assumptions have description comments |
| `test_verbose_user_patterns_have_description_comments` | Top-level pattern keys have description comments |
| `test_non_verbose_no_description_comments_on_pattern_keys` | Non-verbose mode has no description comments |

---

### 13. `test_pattern_quality.py`
Tests pattern data quality (costs, capabilities, versions, conflicts).

| Test | Description |
|------|-------------|
| `test_all_patterns_have_cost_provenance` | All patterns must have `cost.provenance` field |
| `test_no_runtime_cost_impact_field` | No patterns should have `runtimeCostImpact` field (removed in Part 0B) |
| `test_adoption_cost_reasonable_range` | Adoption costs should be in reasonable range ($0–$50K) |
| `test_monthly_cost_range_valid` | Monthly cost ranges must have min ≤ max and reasonable values |
| `test_capabilities_use_hyphens` | All capability names must use lowercase-with-hyphens convention |
| `test_no_duplicate_conflicts` | Patterns should not have duplicate conflict entries |
| `test_conflicts_are_sorted` | Conflict lists should be sorted alphabetically |
| `test_pattern_types_valid` | Pattern types must be from valid set |
| `test_cloud_compatibility_valid` | Cloud compatibility must use valid values |
| `test_version_format` | Pattern versions should follow semantic versioning (X.Y.Z) |

---

### 14. `test_add_capability_reasoning.py`
Tests for LLM-based capability reasoning addition helpers.

| Test | Description |
|------|-------------|
| `test_get_validated_ids_returns_empty_when_no_section` | Returns empty when no validation section |
| `test_get_validated_ids_finds_pattern_ids` | Finds pattern IDs from validation results |
| `test_get_validated_ids_returns_empty_for_missing_file` | Returns empty for missing file |
| `test_all_have_reasoning_true_when_no_entries` | True when no capability entries |
| `test_all_have_reasoning_true_when_no_fields` | True when no provides/requires fields |
| `test_all_have_reasoning_false_when_one_missing` | False when reasoning missing on one entry |
| `test_all_have_reasoning_true_when_all_present` | True when all have reasoning |
| `test_apply_adds_reasoning_on_exact_match` | Adds reasoning on exact capability match |
| `test_apply_matches_despite_hyphen_vs_underscore` | Matches despite hyphen/underscore differences |
| `test_apply_does_not_rename_original_capability` | Doesn't rename original capability name |
| `test_apply_skips_entries_already_reasoned` | Skips entries already with reasoning |
| `test_apply_handles_requires_entries` | Handles requires capability entries |
| `test_format_includes_pattern_id_header` | Formatted entry includes pattern ID header |
| `test_format_shows_checkmark_for_valid` | Shows ✅ for valid capabilities |
| `test_format_shows_cross_for_invalid` | Shows ❌ for invalid capabilities |
| `test_format_includes_issues_section` | Includes issues section in output |
| `test_format_omits_requires_section_when_empty` | Omits requires section when empty |

---

### 15. `test_minimal_spec_recompile.py`
Tests minimal spec and recompilation support.

| Test | Description |
|------|-------------|
| `test_minimal_spec_no_empty_sections` | Minimal spec doesn't output empty top-level sections |
| `test_compiled_spec_recompilation` | Compiled-spec can be used as input and produces same output |
| `test_assumptions_properties_allowed` | Assumptions sections accept properties from defaults |
| `test_partial_assumptions_preserved_during_recompile` | Partial assumptions with custom values are preserved |

---

### 16. `test_proposals_1_4.py`
Unit tests for output proposals (sorting, minimal fields, honored rules, CLI format).

| Test | Description |
|------|-------------|
| `test_selected_patterns_sorted_by_match_score` | Patterns sorted descending by match score |
| `test_selected_patterns_minimal_fields` | Non-verbose shows only id and title |
| `test_rejected_patterns_sorted_by_partial_match` | Rejected patterns sorted by relevance |
| `test_honored_rules_format` | Honored rules structure matches failed_rules format |
| `test_honored_rules_accuracy` | Honored rules actually match spec values |
| `test_cli_outputs_compiled_spec_content` | compiled-spec.yaml content shown in CLI output |
| `test_cli_files_at_end_with_utc` | File list at end has UTC timestamp in ISO 8601 format |
| `test_verbose_comprehensive_info` | All 7 fields present in verbose mode with correct order |
| `test_verbose_cost_logging_always` | Cost calculations shown in verbose mode |
| `test_match_score_calculation_edge_cases` | Edge cases in match score calculation |
| `test_partial_match_score_edge_cases` | Edge cases in partial match score calculation |
| `test_honored_rules_persists_through_phases` | Honored rules persist through Phase 3.1–3.3 |

---

### 17. `test_apply_capability_suggestions.py`
Tests for LLM-based capability suggestion application helpers.

| Test | Description |
|------|-------------|
| `test_validate_name_already_correct` | Correct names returned as-is |
| `test_validate_name_underscores_to_hyphens` | Underscores converted to hyphens |
| `test_validate_name_strips_whitespace` | Whitespace stripped |
| `test_validate_name_lowercases` | Names lowercased |
| `test_validate_name_camel_case` | Camel case converted to hyphens |
| `test_parse_section_full` | Full section parsing with issues, provides, requires |
| `test_parse_section_no_requires` | Parsing without requires section |
| `test_parse_section_empty` | Parsing empty section |
| `test_needs_update_all_valid_same_caps` | False when all valid with same capabilities |
| `test_needs_update_rejected_capability` | True when capability rejected (❌) |
| `test_needs_update_new_in_validated` | True when new capability in validation |
| `test_needs_update_missing_in_issues` | True when 'Missing X' in issues |
| `test_needs_update_consider_adding_triggers` | True when 'Consider adding X' in issues |
| `test_merge_preserves_existing_fields` | Unchanged capabilities preserve confidence/optional |
| `test_merge_adds_new_capabilities` | New capabilities from LLM are added |
| `test_merge_removes_rejected_capabilities` | Absent capabilities from LLM are removed |
| `test_merge_normalized_fallback_matching` | Matches despite underscore/hyphen differences |
| `test_merge_returns_true_when_changed` | Returns True when pattern changed |
| `test_merge_returns_false_when_unchanged` | Returns False when nothing changed |

---

### 18. `test_nfr_filtering.py`
Tests NFR filtering behavior.

| Test | Description |
|------|-------------|
| `test_availability_high_supports_low` | High availability support accepts low requirements |
| `test_availability_exceeds_capability` | Rejected when requirement exceeds capability ceiling |
| `test_boolean_capability_both_values` | Pattern with `in` operator supports both true and false |
| `test_latency_lower_bound_enforced` | Latency >= rules are true limitations and enforced |
| `test_multiple_nfr_rules` | Pattern with multiple NFR rules matches all correctly |
| `test_boolean_false_requirement` | Pattern requiring false only matches false |
| `test_db_read_replicas_excluded_for_simple_oltp` | Read replicas excluded for low QPS |
| `test_db_read_replicas_included_for_high_qps` | Read replicas included for high QPS |
| `test_arch_monolith_excluded_for_high_qps` | Monolith excluded when QPS exceeds ceiling |

---

### 19. `test_phase3_1_constraints.py`
Unit tests for Phase 3.1 `supports_constraints` filtering.

| Test | Description |
|------|-------------|
| `test_empty_constraints_included` | Patterns with empty `supports_constraints` are neutral (pass) |
| `test_matching_constraint_included` | Pattern with matching constraint rule is included |
| `test_mismatched_constraint_excluded` | Pattern with mismatched constraint rule is excluded |

---

### 20. `test_phase3_3_conflicts.py`
Unit tests for Phase 3.3 conflict resolution with cost tie-breaking.

| Test | Description |
|------|-------------|
| `test_no_conflicts_all_selected` | Patterns without conflicts are all selected |
| `test_conflict_higher_score_wins` | Pattern with higher match score wins conflict |
| `test_conflict_tie_score_lower_cost_wins` | When scores tied, lower-cost pattern wins |
| `test_hub_pattern_both_specific_variants_selected` | Specific variants both selected despite shared hub |
| `test_pairwise_conflict_still_picks_one_winner` | Greedy MIS doesn't change pairwise behavior |

---

### 21. `test_requires_rules.py`
Unit tests for `_validate_required_spec_rules` in compiler.

| Test | Description |
|------|-------------|
| `test_no_requires_rules_no_error` | No violations when no requires rules |
| `test_requires_nfr_pass` | Pattern's `requires_nfr` rule that matches spec |
| `test_requires_nfr_fail_exits` | Pattern's `requires_nfr` rule that fails spec → compilation error |
| `test_requires_constraints_fail_exits` | Pattern's `requires_constraints` rule that fails → compilation error |
| `test_multiple_failures_all_reported` | Multiple failures all reported together |
| `test_unselected_pattern_not_checked` | Unselected patterns not validated |

---

### 22. `test_pattern_conflicts.py`
Tests pattern conflict relationships and declarations.

| Test | Description |
|------|-------------|
| `test_no_asymmetric_conflicts` | All conflict relationships must be symmetric (bidirectional) |
| `test_all_conflict_references_valid` | All patterns referenced in conflicts must exist |
| `test_generic_patterns_have_activation_gate` | Generic patterns have a feature activation gate |
| `test_variants_do_not_conflict_with_generic` | Variants must NOT conflict with their generic base |
| `test_sibling_variants_conflict` | Sibling variant patterns must conflict with each other |
| `test_architecture_patterns_mutually_exclusive` | Architecture patterns should conflict with each other |
| `test_serverless_excludes_platforms` | `arch-serverless-*` excludes all `platform-*` patterns |
| `test_platforms_exclude_serverless` | `platform-*` excludes all `arch-serverless-*` patterns |

---

### 23. `test_warn_nfr.py`
Unit tests for `warn_nfr` and `warn_constraints` evaluation.

| Test | Description |
|------|-------------|
| `test_warn_nfr_both_rules_fire` | Both `warn_nfr` rules fire when conditions met |
| `test_warn_nfr_no_warnings_when_spec_ok` | No warnings when spec meets both requirements |
| `test_warn_nfr_null_actual_skips_warning` | Missing NFR field skips warning |
| `test_warn_nfr_actual_interpolation` | Message `{actual}` replaced with real spec value |
| `test_warn_nfr_pattern_without_warn_nfr` | Pattern with no `warn_nfr` field → no warnings |
| `test_warn_nfr_warning_includes_pattern_id` | Each warning dict includes originating pattern ID |
| `test_warn_constraints_rule_fires` | `warn_constraints` rule fires when condition met |
| `test_warn_constraints_rule_no_warning` | No warning when condition not met |
| `test_warn_constraints_null_actual_skips` | Missing constraint field skips warning |

---

### 24. `test_annotated_error_output.py`
Unit tests for annotated YAML rendering (`_build_error_annotation_map`, `_render_annotated_yaml`).

#### Class: `TestViolations`
| Test | Description |
|------|-------------|
| `test_empty_inputs_returns_empty` | Empty inputs return empty map |
| `test_single_violation_gets_error_prefix` | Single violation gets ❌ prefix |
| `test_multiple_violations_same_path_sorted` | Multiple violations sorted alphabetically |
| `test_multiple_violations_different_paths_both_annotated` | Different paths both annotated |
| `test_violation_with_no_honored_rules_still_annotated` | Violation annotated even without honored rules |

#### Class: `TestActivationGateEq`
| Test | Description |
|------|-------------|
| `test_nfr_eq_included_as_activation` | NFR `==` rules included as activation |
| `test_constraints_eq_included_as_activation` | Constraints `==` rules included as activation |
| `test_multiple_eq_rules_all_annotated` | Multiple `==` rules all annotated |

#### Class: `TestActivationGateThreshold`
| Test | Description |
|------|-------------|
| `test_nfr_gte_included` | NFR `>=` rules included |
| `test_nfr_lte_included` | NFR `<=` rules included |
| `test_constraints_gte_included` | Constraints `>=` rules included |
| `test_constraints_lte_included` | Constraints `<=` rules included |
| `test_caching_required_high_read_throughput_scenario` | Complex scenario with multiple rule types |

#### Class: `TestActivationGateStrictOps`
| Test | Description |
|------|-------------|
| `test_nfr_gt_not_included` | NFR `>` rules NOT included as activation |
| `test_nfr_lt_not_included` | NFR `<` rules NOT included as activation |
| `test_constraints_gt_not_included` | Constraints `>` rules NOT included |
| `test_constraints_lt_not_included` | Constraints `<` rules NOT included |

#### Class: `TestActivationGateNotEq`
| Test | Description |
|------|-------------|
| `test_nfr_neq_not_included` | NFR `!=` rules NOT included |
| `test_constraints_neq_not_included` | Constraints `!=` rules NOT included |

#### Class: `TestActivationGateIn`
| Test | Description |
|------|-------------|
| `test_in_boolean_list_true_false_not_included` | `[True, False]` wildcard not included |
| `test_in_boolean_list_false_true_not_included` | `[False, True]` wildcard not included |
| `test_in_unknown_schema_non_boolean_included` | Unknown schema non-boolean included |
| `test_in_strict_subset_below_70pct_included` | Strict subset (< 70%) included as activation |
| `test_in_strict_subset_above_70pct_not_included` | Subset (> 70%) NOT included |
| `test_in_equal_set_not_strict_subset_not_included` | Equal set NOT included |
| `test_in_nfr_kind_not_included` | NFR `in` rules never activation gates |

#### Class: `TestViolationPathNotOverwritten`
| Test | Description |
|------|-------------|
| `test_violation_path_beats_eq_activation` | Violation ❌ never overwritten by activation annotation |
| `test_violation_path_beats_gte_activation` | Violation ❌ beats `>=` activation |
| `test_non_violating_path_gets_separate_annotation` | Non-violated path gets separate annotation |

#### Class: `TestNonViolatingPatternsExcluded`
| Test | Description |
|------|-------------|
| `test_non_violating_pattern_honored_rules_never_annotated` | Non-violating pattern rules not annotated |
| `test_empty_honored_rules_for_violating_pattern` | Violating pattern with empty honored rules |

#### Class: `TestMultiplePatterns`
| Test | Description |
|------|-------------|
| `test_two_violating_patterns_both_contribute_activation` | Both patterns contribute to same path |
| `test_two_patterns_different_activation_paths` | Different patterns, different paths |
| `test_constraints_and_nfr_rules_both_contribute` | Both constraint and NFR rules contribute |

#### Class: `TestAnnotatedYamlScalar`
| Test | Description |
|------|-------------|
| `test_bool_true_lowercase` | Boolean True rendered as lowercase `true` |
| `test_bool_false_lowercase` | Boolean False rendered as lowercase `false` |
| `test_none_null` | None rendered as `null` |
| `test_integer` | Integer rendered correctly |
| `test_float` | Float rendered correctly |
| `test_plain_string_unquoted` | Plain string unquoted |
| `test_string_with_colon_quoted` | String with colon quoted |
| `test_string_with_hash_quoted` | String with hash quoted |
| `test_string_starting_with_dash_quoted` | String starting with dash quoted |
| `test_string_starting_with_asterisk_quoted` | String starting with asterisk quoted |
| `test_reserved_word_true_quoted` | Reserved word "true" quoted |
| `test_reserved_word_false_quoted` | Reserved word "false" quoted |
| `test_reserved_word_null_quoted` | Reserved word "null" quoted |
| `test_reserved_word_yes_quoted` | Reserved word "yes" quoted |
| `test_reserved_word_no_quoted` | Reserved word "no" quoted |
| `test_reserved_word_on_quoted` | Reserved word "on" quoted |
| `test_reserved_word_off_quoted` | Reserved word "off" quoted |
| `test_reserved_word_tilde_quoted` | Reserved word "~" quoted |
| `test_leading_whitespace_quoted` | Leading whitespace quoted |
| `test_trailing_whitespace_quoted` | Trailing whitespace quoted |
| `test_double_quote_alone_not_quoted` | Double quotes alone not quoted |
| `test_double_quote_with_colon_quoted_and_escaped` | Double quotes with colon escaped |
| `test_backslash_alone_not_quoted` | Backslash alone not quoted |
| `test_backslash_with_colon_quoted_and_escaped` | Backslash with colon escaped |

#### Class: `TestRenderAnnotatedYaml`
| Test | Description |
|------|-------------|
| `test_simple_scalar_no_annotation` | Simple scalar without annotation |
| `test_scalar_with_annotation` | Scalar with annotation |
| `test_integer_scalar` | Integer scalar rendering |
| `test_float_scalar` | Float scalar rendering |
| `test_bool_true_scalar` | Boolean true scalar |
| `test_bool_false_scalar` | Boolean false scalar |
| `test_none_scalar` | None/null scalar |
| `test_nested_dict_leaf_annotation` | Annotation on nested dict leaf |
| `test_nested_dict_parent_annotation` | Annotation on dict-valued key |
| `test_deep_nesting_three_levels` | Deep nesting (3 levels) |
| `test_multiple_keys_only_annotated_one_gets_comment` | Only annotated key gets comment |
| `test_list_parent_annotation` | List parent annotation |
| `test_list_scalar_item_annotation` | List scalar item annotation |
| `test_list_of_scalars_no_annotation` | List of scalars without annotation |
| `test_list_item_none` | List item that is None |
| `test_list_item_dict_first_key_inline` | Dict items in list use inline format |
| `test_annotation_format_two_spaces_hash_space` | Annotation uses `  # ` format |
| `test_no_annotation_no_hash` | No annotation means no hash |
| `test_nested_value_indented` | Nested values properly indented |
| `test_top_level_no_indent` | Top level not indented |
| `test_empty_dict_no_lines` | Empty dict produces no lines |
| `test_empty_list_no_lines` | Empty list produces no lines |

---

### 25. `test_error_suggestions.py`
Unit tests for error suggestion formatting and schema field lookup.

| Test | Description |
|------|-------------|
| `test_enum_field_returns_pipe_joined_values` | Enum field returns pipe-joined values |
| `test_integer_field_with_minimum` | Integer field with minimum constraint |
| `test_number_field_with_min_and_max` | Number field with min and max |
| `test_boolean_field` | Boolean field info |
| `test_unknown_path_returns_unknown` | Unknown path returns "unknown" |
| `test_empty_schema_returns_unknown` | Empty schema returns "unknown" |
| `test_constraints_enum_field` | Constraints enum field info |
| `test_anyof_nullable_enum_returns_enum_options` | anyOf with nullable enum returns options |
| `test_format_suggestions_single_pattern_enum_gate` | Single pattern with enum gate |
| `test_format_suggestions_two_patterns` | Two patterns in suggestions |
| `test_format_suggestions_nfr_threshold_shown` | NFR threshold rules shown in suggestions |
| `test_format_suggestions_nfr_gte_threshold_shown` | NFR `>=` threshold shown |
| `test_format_suggestions_deduplicates_pids` | Same PID deduplicated |
| `test_format_suggestions_unknown_schema_path` | Unknown schema path handling |
| `test_format_suggestions_boolean_gate_no_available_line` | Boolean gate doesn't show "Available" |
| `test_format_suggestions_pid_not_in_honored_rules_returns_empty` | Missing PID returns empty |

---

### 26. `test_compiler_integration.py`
Comprehensive integration tests for compiler end-to-end behavior (exercises `test-specs/`).

#### Class: `TestOutputStructure`
| Test | Description |
|------|-------------|
| `test_violation_returns_nonzero_exit_code` | Violation returns exit code 1 |
| `test_success_returns_zero_exit_code` | Success returns exit code 0 |
| `test_error_mode_prints_annotated_yaml_to_stdout` | Error output is annotated YAML |
| `test_verbose_flag_creates_compiled_spec_file` | `-v` flag creates compiled-spec.yaml file |
| `test_verbose_compiled_spec_has_inline_pattern_comments` | Verbose spec has inline comments |
| `test_success_mode_prints_cost_section_to_stdout` | Success prints cost section |
| `test_error_mode_does_not_print_cost_section` | Error mode skips cost section |

#### Class: `TestErrorAnnotation`
| Test | Description |
|------|-------------|
| `test_violation_gets_error_prefix` | Violated field annotated with ❌ |
| `test_multiple_violations_same_path_sorted_alphabetically` | Multiple violations sorted |
| `test_nfr_gte_threshold_annotates_activation_field` | NFR `>=` threshold annotates triggering field |
| `test_nfr_lte_threshold_annotates_activation_field` | NFR `<=` threshold annotates ceiling |
| `test_in_violation_gets_error_annotation` | `in` violation gets ❌ |
| `test_in_activation_gate_annotates_supported_value` | `in` activation gate annotates |
| `test_eq_gate_activation_path_appears_in_suggestions` | `==` gate path in suggestions |
| `test_violation_path_retains_error_prefix_not_activation_annotation` | Violated field keeps ❌ |
| `test_only_violated_fields_have_error_annotation` | Only violated fields have ❌ |
| `test_strict_ops_do_not_annotate` | Strict ops (`>`, `<`) don't annotate |

#### Class: `TestSuggestionsBlock`
| Test | Description |
|------|-------------|
| `test_error_summary_header_present` | ❌ header present |
| `test_violation_reason_text_in_error_summary` | Reason text in summary |
| `test_suggestions_block_present_on_violation` | 💡 Suggestions block present |
| `test_nfr_gte_threshold_gate_in_suggestions` | NFR `>=` gate in suggestions |
| `test_nfr_lte_threshold_gate_in_suggestions` | NFR `<=` gate in suggestions |
| `test_eq_gate_in_suggestions_shows_activation_path` | `==` gate shows path |
| `test_suggestions_shows_activated_by_label` | 'activated by' label present |
| `test_suggestions_deduplication_single_block_per_violating_pattern` | Deduplication works |
| `test_no_suggestions_on_success` | No suggestions on clean spec |

#### Class: `TestAdvisoryWarnings`
| Test | Description |
|------|-------------|
| `test_advisory_section_present_in_success_mode` | Advisory section on success |
| `test_advisory_section_after_cost_section` | Advisory after cost section |
| `test_advisory_contains_nfr_path_and_message` | Advisory has NFR path |
| `test_advisory_section_has_at_least_one_pattern_entry` | At least one pattern entry |
| `test_advisory_section_header_format` | Correct header format |
| `test_advisory_absent_when_no_warn_rules_fire` | No advisory when no warns |
| `test_advisory_section_present_in_verbose_mode` | Advisory in verbose mode |
| `test_advisory_warnings_sorted_by_match_score` | Sorted by match score |

#### Class: `TestCostSection`
| Test | Description |
|------|-------------|
| `test_cost_section_present_on_success` | Cost section on success |
| `test_cost_section_present_when_advisory_warnings_also_present` | Cost before advisory |
| `test_cost_infeasibility_detected_and_reported` | Cost infeasibility detected |
| `test_cost_infeasibility_shows_fail_marker` | FAIL marker on infeasibility |
| `test_cost_section_absent_on_hard_violation` | No cost section on violation |

#### Class: `TestScalarFormatting`
| Test | Description |
|------|-------------|
| `test_bool_false_rendered_lowercase` | False as `false` |
| `test_bool_true_rendered_lowercase` | True as `true` |
| `test_integer_rendered_without_quotes` | Integers unquoted |
| `test_annotation_format_two_spaces_hash_space` | Comment format `  # ` |
| `test_nested_values_indented_in_error_output` | Nested values indented |
| `test_null_rendered_in_output` | Null values rendered |

#### Class: `TestAdvisoryWarnConstraints`
| Test | Description |
|------|-------------|
| `test_warn_constraints_can_produce_advisory` | `warn_constraints` produces advisory |
| `test_warn_nfr_and_warn_constraints_both_in_advisory_section` | Both in same advisory section |

---

### 27. `test_nfr_constraint_logic.py`
Tests NFR and constraint logic correctness across all patterns.

| Test | Description |
|------|-------------|
| `test_no_nfr_logic_errors` | NFR rules must use valid paths |
| `test_no_constraint_logic_errors` | Constraint rules must be valid |
| `test_nfr_paths_in_canonical_schema` | All NFR paths must exist in canonical-schema.yaml |
| `test_constraint_paths_in_canonical_schema` | All constraint paths must exist in canonical-schema.yaml |
| `test_valid_operators` | All rules must use valid operators |

---

### 28. `test_sec_auth_pattern_selection.py`
Tests `sec-auth-*` pattern selection based on `nfr.security.auth` value.

| Test | Description |
|------|-------------|
| `test_api_key_selects_only_sec_auth_api_key` | `auth: api_key` selects only `sec-auth-api-key` |
| `test_jwt_selects_only_sec_auth_jwt_stateless` | `auth: jwt` selects only `sec-auth-jwt-stateless` |
| `test_oauth2_selects_only_sec_auth_oauth2_oidc` | `auth: oauth2_oidc` selects only `sec-auth-oauth2-oidc` |
| `test_password_selects_only_sec_auth_password` | `auth: password` selects only `sec-auth-password` |
| `test_saml_selects_only_sec_auth_saml_sso` | `auth: saml` selects only `sec-auth-saml-sso` |
| `test_mtls_selects_only_sec_auth_mtls` | `auth: mtls` selects only `sec-auth-mtls-service-mesh` |
| `test_no_auth_selects_no_auth_patterns` | `auth: n/a` selects no `sec-auth-*` patterns |
| `test_session_cookies_only_for_web_platform` | `sec-auth-session-cookies` only for web platform |
| `test_password_excluded_for_api_platform` | Password excluded for API platform |
| `test_saml_excluded_for_api_platform` | SAML excluded for API platform |
| `test_jwt_accepted_by_schema` | JWT accepted by schema without error |

---

### 29. `test_semantic_validation.py`
Tests semantic validation for contradictory spec configurations.

| Test | Description |
|------|-------------|
| `test_multi_tenancy_vs_tenant_isolation` | Multi-tenancy feature vs isolation value consistency |
| `test_tenant_count_vs_multi_tenancy` | Tenant count vs `multi_tenancy` flag consistency |
| `test_compliance_vs_audit_logging` | HIPAA/SOX compliance requires audit logging |
| `test_messaging_delivery_guarantee_vs_async` | Messaging delivery guarantee vs async messaging |
| `test_batch_processing_nfr_enforcement` | Batch processing NFR enforcement |

---

### 30. `test_disallowed_saas_providers.py`
Tests `constraints.disallowed-saas-providers` enforcement.

| Test | Description |
|------|-------------|
| `test_disallowed_provider_blocks_pattern` | Disallowed provider blocks matching pattern from selection |
| `test_allowed_provider_not_affected` | Provider in `saas-providers` is not blocked |
| `test_contradiction_fails_compilation` | Provider in both `saas-providers` and `disallowed-saas-providers` fails compilation |
| `test_multiple_disallowed_providers` | Multiple disallowed providers all enforced |
| `test_empty_disallowed_list_has_no_effect` | Empty `disallowed-saas-providers` has no effect |
