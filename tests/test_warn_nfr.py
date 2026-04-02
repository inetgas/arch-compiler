#!/usr/bin/env python3
"""Unit tests for warn_nfr evaluation in the compiler."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.archcompiler import _evaluate_warn_nfr_rules


# Minimal pattern with warn_nfr
# Rules describe the sub-optimal condition: warn fires when rule PASSES (_evaluate_rule returns True)
CACHE_ASIDE = {
    "id": "cache-aside",
    "warn_nfr": [
        {
            "path": "/nfr/consistency/needsReadYourWrites",
            "op": "==",
            "value": True,  # warn when spec REQUIRES read-your-writes (cache-aside is eventually consistent)
            "reason": "Eventual consistency; read-your-writes adds complexity.",
            "message": "cache-aside: needsReadYourWrites=true but pattern is eventually consistent."
        },
        {
            "path": "/nfr/throughput/peak_jobs_per_hour",
            "op": "<",
            "value": 36000,  # warn when throughput IS low (overhead may not justify caching)
            "reason": "Low QPS means caching overhead may not justify benefit.",
            "message": "cache-aside: peak throughput is {actual} jobs/hour. Caching may add unnecessary complexity."
        }
    ]
}

SPEC_BOTH_WARN = {
    "nfr": {
        "consistency": {"needsReadYourWrites": True},   # == True → warn
        "throughput": {"peak_jobs_per_hour": 1000}      # < 36000 → warn
    }
}

SPEC_NO_WARN = {
    "nfr": {
        "consistency": {"needsReadYourWrites": False},     # != True → no warn
        "throughput": {"peak_jobs_per_hour": 1000000}      # not < 36000 → no warn
    }
}

SPEC_DEFAULTS = {}  # no nfr at all


def test_warn_nfr_both_rules_fire():
    """Low QPS + needsReadYourWrites=true → 2 warnings (both sub-optimal conditions present)."""
    warnings = _evaluate_warn_nfr_rules([CACHE_ASIDE], SPEC_BOTH_WARN)
    assert len(warnings) == 2
    codes = {w["code"] for w in warnings}
    assert "warn_nfr" in codes


def test_warn_nfr_no_warnings_when_spec_ok():
    """High QPS + needsReadYourWrites=false → no warnings."""
    warnings = _evaluate_warn_nfr_rules([CACHE_ASIDE], SPEC_NO_WARN)
    assert len(warnings) == 0


def test_warn_nfr_null_actual_skips_warning():
    """Missing NFR field → no warning (null actual = architectural unknown)."""
    warnings = _evaluate_warn_nfr_rules([CACHE_ASIDE], SPEC_DEFAULTS)
    assert len(warnings) == 0


def test_warn_nfr_actual_interpolation():
    """Message {actual} is replaced with the real spec value."""
    warnings = _evaluate_warn_nfr_rules([CACHE_ASIDE], SPEC_BOTH_WARN)
    qps_warnings = [w for w in warnings if "1000" in w["message"]]
    assert len(qps_warnings) == 1, f"Expected QPS interpolation, got: {warnings}"


def test_warn_nfr_pattern_without_warn_nfr():
    """Pattern with no warn_nfr field → no warnings."""
    pattern_no_warns = {"id": "some-pattern"}
    warnings = _evaluate_warn_nfr_rules([pattern_no_warns], SPEC_BOTH_WARN)
    assert len(warnings) == 0


def test_warn_nfr_warning_includes_pattern_id():
    """Each warning dict includes the originating pattern ID."""
    warnings = _evaluate_warn_nfr_rules([CACHE_ASIDE], SPEC_BOTH_WARN)
    for w in warnings:
        assert w.get("pattern_id") == "cache-aside"


from tools.archcompiler import _evaluate_warn_constraints_rules

PATTERN_WITH_WARN_CONSTRAINTS = {
    "id": "some-pattern",
    "warn_constraints": [
        {
            "path": "/constraints/features/async_messaging",
            "op": "==",
            "value": False,  # warn when async IS disabled but pattern requires async
            "reason": "Pattern is designed for async workflows; sync mode may cause issues.",
            "message": "some-pattern: async_messaging={actual} — this pattern is designed for async workflows."
        }
    ]
}

SPEC_SYNC = {"constraints": {"features": {"async_messaging": False}}}   # async disabled → warn
SPEC_ASYNC = {"constraints": {"features": {"async_messaging": True}}}   # async enabled → no warn


def test_warn_constraints_rule_fires():
    """async_messaging=false (sync mode) → 1 warning (pattern needs async)."""
    warnings = _evaluate_warn_constraints_rules([PATTERN_WITH_WARN_CONSTRAINTS], SPEC_SYNC)
    assert len(warnings) == 1
    assert warnings[0]["code"] == "warn_constraints"
    assert warnings[0]["pattern_id"] == "some-pattern"


def test_warn_constraints_rule_no_warning():
    """async_messaging=true (async enabled) → no warning."""
    warnings = _evaluate_warn_constraints_rules([PATTERN_WITH_WARN_CONSTRAINTS], SPEC_ASYNC)
    assert len(warnings) == 0


def test_warn_constraints_null_actual_skips():
    """Missing constraint field → no warning."""
    warnings = _evaluate_warn_constraints_rules([PATTERN_WITH_WARN_CONSTRAINTS], {})
    assert len(warnings) == 0
