"""Unit tests for _build_error_annotation_map and _render_annotated_yaml."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.archcompiler import _build_error_annotation_map, _render_annotated_yaml, _annotated_yaml_scalar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _violation(pid, path, op=">=", value=1):
    return {"pid": pid, "path": path, "op": op, "value": value, "reason": "r"}


def _rule(path, op, value):
    return {"path": path, "op": op, "value": value}


def _schema_with_enum(path, options):
    """Build a minimal canonical_schema with an enum at the given dotted path."""
    parts = [s for s in path.split("/") if s]
    schema = {}
    node = schema
    for i, part in enumerate(parts):
        node.setdefault("properties", {})
        if i == len(parts) - 1:
            node["properties"][part] = {"type": "string", "enum": options}
        else:
            node["properties"][part] = {}
            node = node["properties"][part]
    return schema


# ===========================================================================
# _build_error_annotation_map — Pass 1: violations
# ===========================================================================

class TestViolations:
    def test_empty_inputs_returns_empty(self):
        assert _build_error_annotation_map([], {}, {}) == {}

    def test_single_violation_gets_error_prefix(self):
        result = _build_error_annotation_map([_violation("p1", "/nfr/rpo_minutes")], {}, {})
        assert result["/nfr/rpo_minutes"] == "❌ p1"

    def test_multiple_violations_same_path_sorted(self):
        violations = [_violation("p2", "/path"), _violation("p1", "/path")]
        result = _build_error_annotation_map(violations, {}, {})
        assert result["/path"] == "❌ p1, p2"

    def test_multiple_violations_different_paths_both_annotated(self):
        violations = [_violation("p1", "/path/a"), _violation("p2", "/path/b")]
        result = _build_error_annotation_map(violations, {}, {})
        assert result["/path/a"] == "❌ p1"
        assert result["/path/b"] == "❌ p2"

    def test_violation_with_no_honored_rules_still_annotated(self):
        # Pattern in violations but absent from honored_rules → no crash, just violation
        result = _build_error_annotation_map([_violation("p1", "/x")], {}, {})
        assert result["/x"] == "❌ p1"
        assert len(result) == 1


# ===========================================================================
# _build_error_annotation_map — Pass 2: activation gates, op == "=="
# ===========================================================================

class TestActivationGateEq:
    def test_nfr_eq_included_as_activation(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"nfr": [_rule("/nfr/security/auth", "==", "jwt")]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/nfr/security/auth") == "p1"

    def test_constraints_eq_included_as_activation(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/features/caching", "==", True)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/constraints/features/caching") == "p1"

    def test_multiple_eq_rules_all_annotated(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"nfr": [
            _rule("/nfr/data/compliance/gdpr", "==", True),
            _rule("/nfr/security/auth", "==", "oauth2_oidc"),
        ]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/nfr/data/compliance/gdpr") == "p1"
        assert result.get("/nfr/security/auth") == "p1"


# ===========================================================================
# _build_error_annotation_map — Pass 2: activation gates, op ">=" / "<="
# ===========================================================================

class TestActivationGateThreshold:
    def test_nfr_gte_included(self):
        violations = [_violation("p1", "/constraints/features/caching")]
        honored = {"p1": {"nfr": [_rule("/nfr/throughput/peak_query_per_second_read", ">=", 200)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/nfr/throughput/peak_query_per_second_read") == "p1"

    def test_nfr_lte_included(self):
        violations = [_violation("p1", "/constraints/features/caching")]
        honored = {"p1": {"nfr": [_rule("/nfr/availability/target", "<=", 0.9999)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/nfr/availability/target") == "p1"

    def test_constraints_gte_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/min_nodes", ">=", 3)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/constraints/min_nodes") == "p1"

    def test_constraints_lte_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/max_latency", "<=", 100)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/constraints/max_latency") == "p1"

    def test_caching_required_high_read_throughput_scenario(self):
        """NFR >= threshold activates pattern; constraint violation fires. Both annotated."""
        violations = [_violation("caching-req", "/constraints/features/caching", "==", True)]
        honored = {"caching-req": {
            "nfr": [_rule("/nfr/throughput/peak_query_per_second_read", ">=", 200)],
            "constraints": [],
        }}
        result = _build_error_annotation_map(violations, honored, {})
        assert result["/constraints/features/caching"] == "❌ caching-req"
        assert result.get("/nfr/throughput/peak_query_per_second_read") == "caching-req"


# ===========================================================================
# _build_error_annotation_map — Pass 2: strict ops ">" / "<" NOT included
# ===========================================================================

class TestActivationGateStrictOps:
    def test_nfr_gt_not_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"nfr": [_rule("/nfr/throughput/peak_jobs_per_hour", ">", 100)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/nfr/throughput/peak_jobs_per_hour" not in result

    def test_nfr_lt_not_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"nfr": [_rule("/nfr/latency/p95Milliseconds", "<", 50)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/nfr/latency/p95Milliseconds" not in result

    def test_constraints_gt_not_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/min_replicas", ">", 2)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/constraints/min_replicas" not in result

    def test_constraints_lt_not_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/cost_limit", "<", 500)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/constraints/cost_limit" not in result


# ===========================================================================
# _build_error_annotation_map — Pass 2: op "!=" NOT included
# ===========================================================================

class TestActivationGateNotEq:
    def test_nfr_neq_not_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"nfr": [_rule("/nfr/security/auth", "!=", "n/a")]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/nfr/security/auth" not in result

    def test_constraints_neq_not_included(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/cloud", "!=", "on-prem")]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/constraints/cloud" not in result


# ===========================================================================
# _build_error_annotation_map — Pass 2: op "in", constraints only
# ===========================================================================

class TestActivationGateIn:
    def test_in_boolean_list_true_false_not_included(self):
        """[True, False] is a wildcard — not restrictive, not an activation gate."""
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/nfr/data/pii", "in", [True, False])]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/nfr/data/pii" not in result

    def test_in_boolean_list_false_true_not_included(self):
        """Order-independent: [False, True] is also a wildcard."""
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/nfr/data/pii", "in", [False, True])]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/nfr/data/pii" not in result

    def test_in_unknown_schema_non_boolean_included(self):
        """Unknown schema + non-boolean list → include (can't evaluate coverage)."""
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/cloud", "in", ["aws", "gcp"])]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/constraints/cloud") == "p1"

    def test_in_strict_subset_below_70pct_included(self):
        """2 of 5 options (40%) — genuinely restrictive, should annotate."""
        schema = _schema_with_enum("/constraints/cloud", ["aws", "gcp", "azure", "on-prem", "n/a"])
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/cloud", "in", ["aws", "gcp"])]}}
        result = _build_error_annotation_map(violations, honored, schema)
        assert result.get("/constraints/cloud") == "p1"

    def test_in_strict_subset_above_70pct_not_included(self):
        """3 of 4 options (75%) — not genuinely restrictive, should NOT annotate."""
        schema = _schema_with_enum("/constraints/cloud", ["aws", "gcp", "azure", "on-prem"])
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/cloud", "in", ["aws", "gcp", "azure"])]}}
        result = _build_error_annotation_map(violations, honored, schema)
        assert "/constraints/cloud" not in result

    def test_in_equal_set_not_strict_subset_not_included(self):
        """Pattern allows exactly the same set as schema — not restrictive."""
        schema = _schema_with_enum("/constraints/cloud", ["aws", "gcp"])
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [_rule("/constraints/cloud", "in", ["aws", "gcp"])]}}
        result = _build_error_annotation_map(violations, honored, schema)
        assert "/constraints/cloud" not in result

    def test_in_nfr_kind_not_included(self):
        """op='in' on NFR rules is never an activation gate."""
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"nfr": [_rule("/nfr/security/auth", "in", ["jwt", "oauth2_oidc"])]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert "/nfr/security/auth" not in result


# ===========================================================================
# _build_error_annotation_map — guard: violation path never overwritten
# ===========================================================================

class TestViolationPathNotOverwritten:
    def test_violation_path_beats_eq_activation(self):
        """If path is in violations, its ❌ annotation is never overwritten by activation gate."""
        violations = [_violation("p1", "/nfr/security/auth")]
        honored = {"p1": {"nfr": [_rule("/nfr/security/auth", "==", "jwt")]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result["/nfr/security/auth"].startswith("❌")

    def test_violation_path_beats_gte_activation(self):
        violations = [_violation("p1", "/nfr/throughput/peak_query_per_second_read")]
        honored = {"p1": {"nfr": [_rule("/nfr/throughput/peak_query_per_second_read", ">=", 200)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result["/nfr/throughput/peak_query_per_second_read"].startswith("❌")

    def test_non_violating_path_gets_separate_annotation(self):
        """Violation on /path/a; honored rule at /path/b — /path/b gets activation, not ❌."""
        violations = [_violation("p1", "/path/a")]
        honored = {"p1": {"nfr": [_rule("/path/b", ">=", 5)]}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result["/path/a"] == "❌ p1"
        assert result.get("/path/b") == "p1"


# ===========================================================================
# _build_error_annotation_map — non-violating patterns excluded
# ===========================================================================

class TestNonViolatingPatternsExcluded:
    def test_non_violating_pattern_honored_rules_never_annotated(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {
            "p1": {"nfr": []},
            "p2": {"nfr": [_rule("/nfr/availability/target", "==", 0.9999)]},
        }
        result = _build_error_annotation_map(violations, honored, {})
        assert "/nfr/availability/target" not in result

    def test_empty_honored_rules_for_violating_pattern(self):
        violations = [_violation("p1", "/nfr/rpo_minutes")]
        honored = {"p1": {"constraints": [], "nfr": []}}
        result = _build_error_annotation_map(violations, honored, {})
        assert result == {"/nfr/rpo_minutes": "❌ p1"}


# ===========================================================================
# _build_error_annotation_map — multiple patterns
# ===========================================================================

class TestMultiplePatterns:
    def test_two_violating_patterns_both_contribute_activation(self):
        violations = [_violation("p1", "/v1"), _violation("p2", "/v2")]
        honored = {
            "p1": {"nfr": [_rule("/shared/path", ">=", 100)]},
            "p2": {"nfr": [_rule("/shared/path", ">=", 200)]},
        }
        result = _build_error_annotation_map(violations, honored, {})
        annotation = result.get("/shared/path", "")
        assert "p1" in annotation
        assert "p2" in annotation

    def test_two_patterns_different_activation_paths(self):
        violations = [_violation("p1", "/v1"), _violation("p2", "/v2")]
        honored = {
            "p1": {"nfr": [_rule("/path/a", ">=", 1)]},
            "p2": {"constraints": [_rule("/path/b", "==", "jwt")]},
        }
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/path/a") == "p1"
        assert result.get("/path/b") == "p2"

    def test_constraints_and_nfr_rules_both_contribute(self):
        """Single pattern with both constraint and NFR honored rules."""
        violations = [_violation("p1", "/v1")]
        honored = {"p1": {
            "constraints": [_rule("/constraints/features/caching", "==", True)],
            "nfr": [_rule("/nfr/throughput/peak_query_per_second_read", ">=", 200)],
        }}
        result = _build_error_annotation_map(violations, honored, {})
        assert result.get("/constraints/features/caching") == "p1"
        assert result.get("/nfr/throughput/peak_query_per_second_read") == "p1"


# ===========================================================================
# _annotated_yaml_scalar
# ===========================================================================

class TestAnnotatedYamlScalar:
    def test_bool_true_lowercase(self):
        assert _annotated_yaml_scalar(True) == "true"

    def test_bool_false_lowercase(self):
        assert _annotated_yaml_scalar(False) == "false"

    def test_none_null(self):
        assert _annotated_yaml_scalar(None) == "null"

    def test_integer(self):
        assert _annotated_yaml_scalar(42) == "42"

    def test_float(self):
        assert _annotated_yaml_scalar(3.14) == "3.14"

    def test_plain_string_unquoted(self):
        assert _annotated_yaml_scalar("hello") == "hello"

    def test_string_with_colon_quoted(self):
        result = _annotated_yaml_scalar("foo: bar")
        assert result.startswith('"') and result.endswith('"')
        assert "foo: bar" in result

    def test_string_with_hash_quoted(self):
        result = _annotated_yaml_scalar("foo # comment")
        assert result.startswith('"')

    def test_string_starting_with_dash_quoted(self):
        result = _annotated_yaml_scalar("-option")
        assert result.startswith('"')

    def test_string_starting_with_asterisk_quoted(self):
        result = _annotated_yaml_scalar("*anchor")
        assert result.startswith('"')

    def test_reserved_word_true_quoted(self):
        result = _annotated_yaml_scalar("true")
        assert result.startswith('"')

    def test_reserved_word_false_quoted(self):
        assert _annotated_yaml_scalar("false").startswith('"')

    def test_reserved_word_null_quoted(self):
        assert _annotated_yaml_scalar("null").startswith('"')

    def test_reserved_word_yes_quoted(self):
        assert _annotated_yaml_scalar("yes").startswith('"')

    def test_reserved_word_no_quoted(self):
        assert _annotated_yaml_scalar("no").startswith('"')

    def test_reserved_word_on_quoted(self):
        assert _annotated_yaml_scalar("on").startswith('"')

    def test_reserved_word_off_quoted(self):
        assert _annotated_yaml_scalar("off").startswith('"')

    def test_reserved_word_tilde_quoted(self):
        assert _annotated_yaml_scalar("~").startswith('"')

    def test_leading_whitespace_quoted(self):
        assert _annotated_yaml_scalar(" space").startswith('"')

    def test_trailing_whitespace_quoted(self):
        assert _annotated_yaml_scalar("space ").startswith('"')

    def test_double_quote_alone_not_quoted(self):
        # Double quotes alone don't trigger YAML quoting — returned as-is
        result = _annotated_yaml_scalar('say "hi"')
        assert result == 'say "hi"'

    def test_double_quote_with_colon_quoted_and_escaped(self):
        # Colon triggers quoting; embedded double quotes are then escaped
        result = _annotated_yaml_scalar('say "hi": value')
        assert result.startswith('"') and result.endswith('"')
        assert '\\"hi\\"' in result

    def test_backslash_alone_not_quoted(self):
        # Backslash alone doesn't trigger YAML quoting — returned as-is
        result = _annotated_yaml_scalar("path\\to\\file")
        assert result == "path\\to\\file"

    def test_backslash_with_colon_quoted_and_escaped(self):
        # Colon triggers quoting; backslash is then doubled
        result = _annotated_yaml_scalar("path\\x: y")
        assert result.startswith('"') and result.endswith('"')
        assert "\\\\" in result


# ===========================================================================
# _render_annotated_yaml
# ===========================================================================

class TestRenderAnnotatedYaml:
    # --- scalars ---

    def test_simple_scalar_no_annotation(self):
        assert _render_annotated_yaml({"key": "value"}, {}) == ["key: value"]

    def test_scalar_with_annotation(self):
        lines = _render_annotated_yaml({"rpo": 0}, {"/rpo": "❌ p1"})
        assert lines == ["rpo: 0  # ❌ p1"]

    def test_integer_scalar(self):
        assert _render_annotated_yaml({"n": 42}, {}) == ["n: 42"]

    def test_float_scalar(self):
        assert _render_annotated_yaml({"f": 0.9999}, {}) == ["f: 0.9999"]

    def test_bool_true_scalar(self):
        assert _render_annotated_yaml({"b": True}, {}) == ["b: true"]

    def test_bool_false_scalar(self):
        assert _render_annotated_yaml({"b": False}, {}) == ["b: false"]

    def test_none_scalar(self):
        assert _render_annotated_yaml({"k": None}, {}) == ["k: null"]

    # --- nested dicts ---

    def test_nested_dict_leaf_annotation(self):
        obj = {"nfr": {"rpo": 0}}
        lines = _render_annotated_yaml(obj, {"/nfr/rpo": "❌ p1"})
        assert any("rpo: 0" in l and "❌ p1" in l for l in lines)
        assert any(l.strip() == "nfr:" for l in lines)

    def test_nested_dict_parent_annotation(self):
        """Annotation on a dict-valued key appears on the key: line."""
        obj = {"nfr": {"rpo": 0}}
        lines = _render_annotated_yaml(obj, {"/nfr": "section-note"})
        assert any("nfr:" in l and "section-note" in l for l in lines)

    def test_deep_nesting_three_levels(self):
        obj = {"a": {"b": {"c": 7}}}
        lines = _render_annotated_yaml(obj, {"/a/b/c": "deep"})
        assert any("c: 7" in l and "deep" in l for l in lines)

    def test_multiple_keys_only_annotated_one_gets_comment(self):
        obj = {"x": 1, "y": 2}
        lines = _render_annotated_yaml(obj, {"/x": "note"})
        annotated = [l for l in lines if "note" in l]
        unannotated = [l for l in lines if "y: 2" in l]
        assert len(annotated) == 1
        assert len(unannotated) == 1
        assert "#" not in unannotated[0]

    # --- lists ---

    def test_list_parent_annotation(self):
        obj = {"items": [1, 2]}
        lines = _render_annotated_yaml(obj, {"/items": "list-note"})
        assert any("items:" in l and "list-note" in l for l in lines)

    def test_list_scalar_item_annotation(self):
        obj = {"items": ["a", "b"]}
        lines = _render_annotated_yaml(obj, {"/items/0": "first"})
        assert any("- a" in l and "first" in l for l in lines)

    def test_list_of_scalars_no_annotation(self):
        lines = _render_annotated_yaml({"v": [1, 2, 3]}, {})
        assert sum(1 for l in lines if "- " in l) == 3

    def test_list_item_none(self):
        lines = _render_annotated_yaml({"v": [None]}, {})
        assert any("- null" in l for l in lines)

    def test_list_item_dict_first_key_inline(self):
        """Dict items in a list use '- key: value' format for the first key."""
        obj = {"items": [{"name": "foo", "val": 1}]}
        lines = _render_annotated_yaml(obj, {})
        assert any(l.strip().startswith("- name:") for l in lines)

    # --- annotation format ---

    def test_annotation_format_two_spaces_hash_space(self):
        lines = _render_annotated_yaml({"k": "v"}, {"/k": "note"})
        assert lines[0] == "k: v  # note"

    def test_no_annotation_no_hash(self):
        lines = _render_annotated_yaml({"k": "v"}, {})
        assert "#" not in lines[0]

    # --- indentation ---

    def test_nested_value_indented(self):
        obj = {"outer": {"inner": 1}}
        lines = _render_annotated_yaml(obj, {})
        inner_line = next(l for l in lines if "inner" in l)
        assert inner_line.startswith("  ")

    def test_top_level_no_indent(self):
        lines = _render_annotated_yaml({"top": 1}, {})
        assert not lines[0].startswith(" ")

    # --- empty containers ---

    def test_empty_dict_no_lines(self):
        assert _render_annotated_yaml({}, {}) == []

    def test_empty_list_no_lines(self):
        assert _render_annotated_yaml([], {}) == []
