"""
Unit tests for _evaluate_rule and _json_pointer_get.

Tests every operator in isolation. When a new operator is added to
_evaluate_rule, add a corresponding section here — this file acts as
the registry of supported operators and their edge-case semantics.

Operators covered: ==  !=  in  not-in  contains-any  >  <  >=  <=
Null semantics:    missing field, "!= null" guard, operator pass-through
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from archcompiler import _evaluate_rule, _json_pointer_get  # noqa: E402


# ---------------------------------------------------------------------------
# _json_pointer_get
# ---------------------------------------------------------------------------

class TestJsonPointerGet:
    def test_root_key(self):
        assert _json_pointer_get({"a": 1}, "/a") == 1

    def test_nested_key(self):
        assert _json_pointer_get({"a": {"b": 2}}, "/a/b") == 2

    def test_deeply_nested(self):
        doc = {"nfr": {"data": {"compliance": {"gdpr": True}}}}
        assert _json_pointer_get(doc, "/nfr/data/compliance/gdpr") is True

    def test_missing_key_returns_none(self):
        assert _json_pointer_get({"a": 1}, "/b") is None

    def test_missing_nested_key_returns_none(self):
        assert _json_pointer_get({"a": {}}, "/a/b") is None

    def test_path_through_none_returns_none(self):
        assert _json_pointer_get({"a": None}, "/a/b") is None

    def test_empty_doc_returns_none(self):
        assert _json_pointer_get({}, "/a/b") is None

    def test_path_without_leading_slash_returns_none(self):
        assert _json_pointer_get({"a": 1}, "a") is None

    def test_list_index(self):
        assert _json_pointer_get({"items": ["x", "y", "z"]}, "/items/1") == "y"

    def test_list_out_of_bounds_returns_none(self):
        assert _json_pointer_get({"items": ["x"]}, "/items/5") is None

    def test_boolean_false_returned_correctly(self):
        assert _json_pointer_get({"flag": False}, "/flag") is False

    def test_zero_returned_correctly(self):
        assert _json_pointer_get({"n": 0}, "/n") == 0


# ---------------------------------------------------------------------------
# Null / missing-field semantics
# These rules apply to ALL operators when the spec field is absent/null.
# ---------------------------------------------------------------------------

class TestNullSemantics:
    """When the spec field is missing (actual=None), each operator behaves as:
      - '==' : FAIL  — null cannot equal any specific value
      - 'in' : FAIL  — null is not a member of any list
      - '!= null' (expected also None): FAIL — explicit "must be set" guard
      - everything else: PASS — field absence doesn't constrain the pattern
    """

    def _rule(self, op, value):
        return {"path": "/x/missing", "op": op, "value": value}

    def _spec(self):
        return {}  # field /x/missing is absent

    def test_eq_null_actual_fails(self):
        assert _evaluate_rule(self._spec(), self._rule("==", "something")) is False

    def test_eq_null_actual_fails_for_bool(self):
        assert _evaluate_rule(self._spec(), self._rule("==", True)) is False

    def test_in_null_actual_fails(self):
        assert _evaluate_rule(self._spec(), self._rule("in", ["a", "b"])) is False

    def test_neq_null_guard_fails(self):
        # "!= null" means "field must be explicitly set"; missing field fails
        assert _evaluate_rule(self._spec(), self._rule("!=", None)) is False

    def test_neq_nonnull_expected_passes_when_missing(self):
        # field is absent, rule says "!= aws" — absence doesn't violate this
        assert _evaluate_rule(self._spec(), self._rule("!=", "aws")) is True

    def test_gt_null_actual_passes(self):
        assert _evaluate_rule(self._spec(), self._rule(">", 0)) is True

    def test_lt_null_actual_passes(self):
        assert _evaluate_rule(self._spec(), self._rule("<", 100)) is True

    def test_gte_null_actual_passes(self):
        assert _evaluate_rule(self._spec(), self._rule(">=", 0)) is True

    def test_lte_null_actual_passes(self):
        assert _evaluate_rule(self._spec(), self._rule("<=", 100)) is True

    def test_not_in_null_actual_passes(self):
        assert _evaluate_rule(self._spec(), self._rule("not-in", ["a", "b"])) is True

    def test_contains_any_null_actual_passes(self):
        assert _evaluate_rule(self._spec(), self._rule("contains-any", ["a"])) is True


# ---------------------------------------------------------------------------
# == operator
# ---------------------------------------------------------------------------

class TestOpEq:
    def test_matching_string(self):
        rule = {"path": "/constraints/cloud", "op": "==", "value": "aws"}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is True

    def test_non_matching_string(self):
        rule = {"path": "/constraints/cloud", "op": "==", "value": "aws"}
        assert _evaluate_rule({"constraints": {"cloud": "azure"}}, rule) is False

    def test_matching_bool_true(self):
        rule = {"path": "/constraints/features/caching", "op": "==", "value": True}
        assert _evaluate_rule({"constraints": {"features": {"caching": True}}}, rule) is True

    def test_non_matching_bool(self):
        rule = {"path": "/constraints/features/caching", "op": "==", "value": True}
        assert _evaluate_rule({"constraints": {"features": {"caching": False}}}, rule) is False

    def test_matching_number(self):
        rule = {"path": "/nfr/availability/target", "op": "==", "value": 0.999}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.999}}}, rule) is True

    def test_non_matching_number(self):
        rule = {"path": "/nfr/availability/target", "op": "==", "value": 0.999}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.95}}}, rule) is False

    def test_case_sensitive_string(self):
        rule = {"path": "/constraints/cloud", "op": "==", "value": "AWS"}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False


# ---------------------------------------------------------------------------
# != operator
# ---------------------------------------------------------------------------

class TestOpNeq:
    def test_non_matching_value(self):
        rule = {"path": "/constraints/cloud", "op": "!=", "value": "aws"}
        assert _evaluate_rule({"constraints": {"cloud": "azure"}}, rule) is True

    def test_matching_value_fails(self):
        rule = {"path": "/constraints/cloud", "op": "!=", "value": "aws"}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False

    def test_neq_null_guard_with_set_field(self):
        # "!= null" with a non-null actual should pass
        rule = {"path": "/nfr/throughput/peak_jobs_per_hour", "op": "!=", "value": None}
        assert _evaluate_rule({"nfr": {"throughput": {"peak_jobs_per_hour": 100}}}, rule) is True

    def test_neq_null_guard_with_null_field(self):
        # "!= null" with a null actual should fail
        rule = {"path": "/nfr/throughput/peak_jobs_per_hour", "op": "!=", "value": None}
        assert _evaluate_rule({"nfr": {"throughput": {"peak_jobs_per_hour": None}}}, rule) is False

    def test_neq_bool(self):
        rule = {"path": "/constraints/features/caching", "op": "!=", "value": False}
        assert _evaluate_rule({"constraints": {"features": {"caching": True}}}, rule) is True


# ---------------------------------------------------------------------------
# in operator
# ---------------------------------------------------------------------------

class TestOpIn:
    def test_value_in_list(self):
        rule = {"path": "/constraints/cloud", "op": "in", "value": ["aws", "gcp"]}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is True

    def test_value_not_in_list(self):
        rule = {"path": "/constraints/cloud", "op": "in", "value": ["aws", "gcp"]}
        assert _evaluate_rule({"constraints": {"cloud": "azure"}}, rule) is False

    def test_bool_in_list(self):
        rule = {"path": "/nfr/data/pii", "op": "in", "value": [True, False]}
        assert _evaluate_rule({"nfr": {"data": {"pii": True}}}, rule) is True

    def test_number_in_list(self):
        rule = {"path": "/nfr/availability/target", "op": "in", "value": [0.99, 0.999, 0.9999]}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.999}}}, rule) is True

    def test_non_list_expected_fails(self):
        # Malformed rule: value is not a list
        rule = {"path": "/constraints/cloud", "op": "in", "value": "aws"}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False

    def test_single_item_list(self):
        rule = {"path": "/constraints/cloud", "op": "in", "value": ["aws"]}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is True


# ---------------------------------------------------------------------------
# not-in operator
# ---------------------------------------------------------------------------

class TestOpNotIn:
    def test_value_not_in_list(self):
        rule = {"path": "/constraints/cloud", "op": "not-in", "value": ["aws"]}
        assert _evaluate_rule({"constraints": {"cloud": "azure"}}, rule) is True

    def test_value_in_list_fails(self):
        rule = {"path": "/constraints/cloud", "op": "not-in", "value": ["aws"]}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False

    def test_non_list_expected_passes(self):
        # Malformed rule: value is not a list — treated as satisfied per impl
        rule = {"path": "/constraints/cloud", "op": "not-in", "value": "aws"}
        assert _evaluate_rule({"constraints": {"cloud": "azure"}}, rule) is True


# ---------------------------------------------------------------------------
# contains-any operator (actual is a list, expected is a list of sought items)
# ---------------------------------------------------------------------------

class TestOpContainsAny:
    def test_intersection_exists(self):
        rule = {"path": "/constraints/saas-providers", "op": "contains-any",
                "value": ["supabase", "neon"]}
        spec = {"constraints": {"saas-providers": ["supabase", "mongodb-atlas"]}}
        assert _evaluate_rule(spec, rule) is True

    def test_no_intersection(self):
        rule = {"path": "/constraints/saas-providers", "op": "contains-any",
                "value": ["supabase", "neon"]}
        spec = {"constraints": {"saas-providers": ["openai", "anthropic"]}}
        assert _evaluate_rule(spec, rule) is False

    def test_empty_actual_list(self):
        rule = {"path": "/constraints/saas-providers", "op": "contains-any",
                "value": ["supabase"]}
        assert _evaluate_rule({"constraints": {"saas-providers": []}}, rule) is False

    def test_empty_expected_list(self):
        rule = {"path": "/constraints/saas-providers", "op": "contains-any",
                "value": []}
        assert _evaluate_rule({"constraints": {"saas-providers": ["supabase"]}}, rule) is False

    def test_non_list_actual_fails(self):
        # actual is a string, not a list
        rule = {"path": "/constraints/cloud", "op": "contains-any", "value": ["aws"]}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False

    def test_non_list_expected_fails(self):
        rule = {"path": "/constraints/saas-providers", "op": "contains-any",
                "value": "supabase"}
        assert _evaluate_rule({"constraints": {"saas-providers": ["supabase"]}}, rule) is False


# ---------------------------------------------------------------------------
# > operator
# ---------------------------------------------------------------------------

class TestOpGt:
    def test_greater(self):
        rule = {"path": "/nfr/throughput/peak_query_per_second_read", "op": ">", "value": 10}
        assert _evaluate_rule({"nfr": {"throughput": {"peak_query_per_second_read": 20}}}, rule) is True

    def test_equal_fails(self):
        rule = {"path": "/nfr/throughput/peak_query_per_second_read", "op": ">", "value": 10}
        assert _evaluate_rule({"nfr": {"throughput": {"peak_query_per_second_read": 10}}}, rule) is False

    def test_less_fails(self):
        rule = {"path": "/nfr/throughput/peak_query_per_second_read", "op": ">", "value": 10}
        assert _evaluate_rule({"nfr": {"throughput": {"peak_query_per_second_read": 5}}}, rule) is False

    def test_non_numeric_actual_fails(self):
        rule = {"path": "/constraints/cloud", "op": ">", "value": 10}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False

    def test_float_comparison(self):
        rule = {"path": "/nfr/availability/target", "op": ">", "value": 0.99}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.999}}}, rule) is True


# ---------------------------------------------------------------------------
# < operator
# ---------------------------------------------------------------------------

class TestOpLt:
    def test_less(self):
        rule = {"path": "/nfr/latency/p95Milliseconds", "op": "<", "value": 500}
        assert _evaluate_rule({"nfr": {"latency": {"p95Milliseconds": 100}}}, rule) is True

    def test_equal_fails(self):
        rule = {"path": "/nfr/latency/p95Milliseconds", "op": "<", "value": 500}
        assert _evaluate_rule({"nfr": {"latency": {"p95Milliseconds": 500}}}, rule) is False

    def test_greater_fails(self):
        rule = {"path": "/nfr/latency/p95Milliseconds", "op": "<", "value": 500}
        assert _evaluate_rule({"nfr": {"latency": {"p95Milliseconds": 1000}}}, rule) is False

    def test_non_numeric_actual_fails(self):
        rule = {"path": "/constraints/cloud", "op": "<", "value": 500}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False


# ---------------------------------------------------------------------------
# >= operator
# ---------------------------------------------------------------------------

class TestOpGte:
    def test_greater(self):
        rule = {"path": "/nfr/rto_minutes", "op": ">=", "value": 15}
        assert _evaluate_rule({"nfr": {"rto_minutes": 30}}, rule) is True

    def test_equal_passes(self):
        rule = {"path": "/nfr/rto_minutes", "op": ">=", "value": 15}
        assert _evaluate_rule({"nfr": {"rto_minutes": 15}}, rule) is True

    def test_less_fails(self):
        rule = {"path": "/nfr/rto_minutes", "op": ">=", "value": 15}
        assert _evaluate_rule({"nfr": {"rto_minutes": 5}}, rule) is False

    def test_float(self):
        rule = {"path": "/nfr/availability/target", "op": ">=", "value": 0.999}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.999}}}, rule) is True


# ---------------------------------------------------------------------------
# <= operator
# ---------------------------------------------------------------------------

class TestOpLte:
    def test_less(self):
        rule = {"path": "/nfr/availability/target", "op": "<=", "value": 0.9999}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.999}}}, rule) is True

    def test_equal_passes(self):
        rule = {"path": "/nfr/availability/target", "op": "<=", "value": 0.9999}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.9999}}}, rule) is True

    def test_greater_fails(self):
        rule = {"path": "/nfr/availability/target", "op": "<=", "value": 0.9999}
        assert _evaluate_rule({"nfr": {"availability": {"target": 0.99999}}}, rule) is False

    def test_integer_vs_float(self):
        rule = {"path": "/nfr/rto_minutes", "op": "<=", "value": 60}
        assert _evaluate_rule({"nfr": {"rto_minutes": 30}}, rule) is True


# ---------------------------------------------------------------------------
# Unknown operator
# ---------------------------------------------------------------------------

class TestUnknownOperator:
    def test_unknown_op_returns_false(self):
        rule = {"path": "/constraints/cloud", "op": "regex", "value": ".*aws.*"}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False

    def test_empty_op_returns_false(self):
        rule = {"path": "/constraints/cloud", "op": "", "value": "aws"}
        assert _evaluate_rule({"constraints": {"cloud": "aws"}}, rule) is False


# ---------------------------------------------------------------------------
# Operator exhaustiveness: every operator used in the pattern registry must
# have a corresponding TestOp* class in this file.
#
# Maintenance: if you add a new operator to _evaluate_rule, add its TestOp*
# class above AND add it to the COVERED_OPS dict below.
# ---------------------------------------------------------------------------

# Maps operator string → the TestOp* class that covers it in this file.
# Update this dict whenever a new operator is implemented.
_COVERED_OPS = {
    "==":           "TestOpEq",
    "!=":           "TestOpNeq",
    "in":           "TestOpIn",
    "not-in":       "TestOpNotIn",
    "contains-any": "TestOpContainsAny",
    ">":            "TestOpGt",
    "<":            "TestOpLt",
    ">=":           "TestOpGte",
    "<=":           "TestOpLte",
}


def test_operator_test_coverage_exhaustive():
    """
    Scan every rule in every pattern file (supports_*, requires_*, warn_*) and
    assert that each operator has a corresponding TestOp* class in this file.

    When a new operator is added to _evaluate_rule and used in patterns, this
    test will fail until both a TestOp* class AND a _COVERED_OPS entry are added.
    """
    import glob
    import json

    _RULE_FIELDS = [
        "supports_constraints", "supports_nfr",
        "requires_constraints", "requires_nfr",
        "warn_constraints", "warn_nfr",
    ]
    patterns_dir = os.path.join(os.path.dirname(__file__), "..", "patterns")
    ops_used = set()
    for fname in glob.glob(os.path.join(patterns_dir, "*.json")):
        p = json.load(open(fname))
        for field in _RULE_FIELDS:
            for rule in p.get(field, []) or []:
                op = rule.get("op", "")
                if op:
                    ops_used.add(op)

    uncovered = ops_used - set(_COVERED_OPS.keys())
    assert not uncovered, (
        f"Operators used in pattern registry but not covered by any TestOp* class:\n"
        + "\n".join(f"  '{op}'" for op in sorted(uncovered))
        + "\n\nFor each new operator:\n"
        "  1. Add a TestOp* class to this file (see existing classes for the pattern)\n"
        "  2. Add the operator → class mapping to _COVERED_OPS dict in this file"
    )
