#!/usr/bin/env python3
"""
Unit tests for NFR filtering behavior after backwards logic fix.

Tests verify:
1. Patterns with high availability support low requirements
2. Boolean capabilities support both true and false
3. Latency limitations are still enforced (lower bounds kept)
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from archcompiler import _filter_by_supports_nfr


def load_test_pattern(pattern_data: dict) -> dict:
    """Create a test pattern with NFR rules."""
    return {
        "id": "test-pattern",
        "title": "Test Pattern",
        "supports_nfr": pattern_data.get("supports_nfr", []),
        **pattern_data
    }


def test_availability_high_supports_low():
    """Pattern supporting high availability should support low requirements."""

    # Pattern supports up to 0.9999 availability (no lower bound)
    pattern = load_test_pattern({
        "supports_nfr": [
            {
                "path": "/nfr/availability/target",
                "op": "<=",
                "value": 0.9999,
                "reason": "Supports up to 99.99% availability"
            }
        ]
    })

    patterns = {"test-pattern": pattern}

    # Spec requests LOW availability (0.95)
    spec = {
        "nfr": {
            "availability": {"target": 0.95}
        }
    }

    selected, rejected, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec, {})

    assert len(selected) == 1, "Pattern should be selected for low availability requirement"
    assert selected[0] == "test-pattern"
    assert len(rejected) == 0
    print("✅ test_availability_high_supports_low passed")


def test_availability_exceeds_capability():
    """Pattern should be rejected if requirement exceeds capability ceiling."""

    # Pattern supports up to 0.9999 availability
    pattern = load_test_pattern({
        "supports_nfr": [
            {
                "path": "/nfr/availability/target",
                "op": "<=",
                "value": 0.9999,
                "reason": "Supports up to 99.99% availability"
            }
        ]
    })

    patterns = {"test-pattern": pattern}

    # Spec requests HIGHER availability (0.99999 = five 9s)
    spec = {
        "nfr": {
            "availability": {"target": 0.99999}
        }
    }

    selected, rejected, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec, {})

    assert len(selected) == 0, "Pattern should be rejected when requirement exceeds capability"
    assert len(rejected) == 1
    assert rejected[0]["id"] == "test-pattern"
    print("✅ test_availability_exceeds_capability passed")


def test_boolean_capability_both_values():
    """Pattern with "in" operator should support both true and false."""

    # Pattern supports PII = true OR false
    pattern = load_test_pattern({
        "supports_nfr": [
            {
                "path": "/nfr/data/pii",
                "op": "in",
                "value": [True, False],
                "reason": "Supports both PII and non-PII data"
            }
        ]
    })

    patterns = {"test-pattern": pattern}

    # Test with pii=true
    spec_with_pii = {"nfr": {"data": {"pii": True}}}
    selected1, rejected1, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec_with_pii, {})
    assert len(selected1) == 1, "Pattern should support pii=true"

    # Test with pii=false
    spec_without_pii = {"nfr": {"data": {"pii": False}}}
    selected2, rejected2, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec_without_pii, {})
    assert len(selected2) == 1, "Pattern should support pii=false"

    print("✅ test_boolean_capability_both_values passed")


def test_latency_lower_bound_enforced():
    """Latency >= rules are true limitations and should be enforced."""

    # Serverless pattern has minimum latency of 50ms (cold start limitation)
    pattern = load_test_pattern({
        "supports_nfr": [
            {
                "path": "/nfr/latency/p95Milliseconds",
                "op": ">=",
                "value": 50,
                "reason": "Lambda cold starts establish minimum p95 of 50ms"
            }
        ]
    })

    patterns = {"test-pattern": pattern}

    # Spec requires STRICT latency (10ms) - should be rejected
    spec_strict = {"nfr": {"latency": {"p95Milliseconds": 10}}}
    selected1, rejected1, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec_strict, {})
    assert len(selected1) == 0, "Pattern should be rejected for strict latency requirement"
    assert len(rejected1) == 1

    # Spec requires RELAXED latency (100ms) - should be selected
    spec_relaxed = {"nfr": {"latency": {"p95Milliseconds": 100}}}
    selected2, rejected2, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec_relaxed, {})
    assert len(selected2) == 1, "Pattern should be selected for relaxed latency requirement"
    assert len(rejected2) == 0

    print("✅ test_latency_lower_bound_enforced passed")


def test_multiple_nfr_rules():
    """Pattern with multiple NFR rules should match all correctly."""

    pattern = load_test_pattern({
        "supports_nfr": [
            {
                "path": "/nfr/availability/target",
                "op": "<=",
                "value": 0.9999,
                "reason": "Supports up to 99.99%"
            },
            {
                "path": "/nfr/data/pii",
                "op": "in",
                "value": [True, False],
                "reason": "Supports both"
            },
            {
                "path": "/nfr/latency/p95Milliseconds",
                "op": ">=",
                "value": 50,
                "reason": "Minimum 50ms"
            }
        ]
    })

    patterns = {"test-pattern": pattern}

    # Spec matches all rules
    spec = {
        "nfr": {
            "availability": {"target": 0.99},
            "data": {"pii": False},
            "latency": {"p95Milliseconds": 100}
        }
    }

    selected, rejected, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec, {})
    assert len(selected) == 1, "Pattern should be selected when all rules match"
    assert len(rejected) == 0

    # Spec fails latency rule
    spec_fail = {
        "nfr": {
            "availability": {"target": 0.99},
            "data": {"pii": False},
            "latency": {"p95Milliseconds": 10}  # Too strict
        }
    }

    selected2, rejected2, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec_fail, {})
    assert len(selected2) == 0, "Pattern should be rejected when any rule fails"
    assert len(rejected2) == 1

    print("✅ test_multiple_nfr_rules passed")


def test_boolean_false_requirement():
    """Pattern requiring false should only match false (less capable)."""

    # Pattern requires audit_logging=false (cheaper, less capable)
    pattern = load_test_pattern({
        "supports_nfr": [
            {
                "path": "/nfr/security/audit_logging",
                "op": "==",
                "value": False,
                "reason": "No audit logging (lower cost)"
            }
        ]
    })

    patterns = {"test-pattern": pattern}

    # Spec with audit_logging=false - should match
    spec_false = {"nfr": {"security": {"audit_logging": False}}}
    selected1, rejected1, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec_false, {})
    assert len(selected1) == 1, "Pattern should match when both are false"

    # Spec with audit_logging=true - should NOT match
    spec_true = {"nfr": {"security": {"audit_logging": True}}}
    selected2, rejected2, _ = _filter_by_supports_nfr(["test-pattern"], patterns, spec_true, {})
    assert len(selected2) == 0, "Pattern requiring false should not match true"
    assert len(rejected2) == 1

    print("✅ test_boolean_false_requirement passed")


def test_db_read_replicas_excluded_for_simple_oltp():
    """db-read-replicas uses >= floor; excluded when spec QPS is below its threshold."""

    # Synthetic db-read-replicas pattern: only useful at >= 500 read QPS
    pattern = load_test_pattern({
        "id": "db-read-replicas",
        "supports_nfr": [
            {
                "path": "/nfr/throughput/peak_query_per_second_read",
                "op": ">=",
                "value": 500,
                "reason": "Read replicas are only beneficial at high read QPS (>= 500)"
            }
        ]
    })

    patterns = {"db-read-replicas": pattern}
    honored = {"db-read-replicas": {"constraints": [], "nfr": []}}

    # Simple OLTP app: 0.1 QPS (far below floor)
    spec_simple = {"nfr": {"throughput": {"peak_query_per_second_read": 0.1}}}
    selected, rejected, _ = _filter_by_supports_nfr(
        ["db-read-replicas"], patterns, spec_simple, honored.copy()
    )

    assert "db-read-replicas" not in selected, (
        "db-read-replicas should be excluded for simple OLTP (0.1 QPS below 500 floor)"
    )
    assert len(rejected) == 1

    print("✅ test_db_read_replicas_excluded_for_simple_oltp passed")


def test_db_read_replicas_included_for_high_qps():
    """db-read-replicas is included when spec declares high read QPS."""

    # Synthetic db-read-replicas pattern: only useful at >= 500 read QPS
    pattern = load_test_pattern({
        "id": "db-read-replicas",
        "supports_nfr": [
            {
                "path": "/nfr/throughput/peak_query_per_second_read",
                "op": ">=",
                "value": 500,
                "reason": "Read replicas are only beneficial at high read QPS (>= 500)"
            }
        ]
    })

    patterns = {"db-read-replicas": pattern}
    honored = {"db-read-replicas": {"constraints": [], "nfr": []}}

    # High-traffic app: 5000 read QPS (well above floor)
    spec_high = {"nfr": {"throughput": {"peak_query_per_second_read": 5000.0}}}
    selected, rejected, _ = _filter_by_supports_nfr(
        ["db-read-replicas"], patterns, spec_high, honored.copy()
    )

    assert "db-read-replicas" in selected, (
        "db-read-replicas should be included for high-read app (5000 QPS above 500 floor)"
    )
    assert len(rejected) == 0

    print("✅ test_db_read_replicas_included_for_high_qps passed")


def test_arch_monolith_excluded_for_high_qps():
    """arch-monolith uses <= ceiling; excluded when spec QPS exceeds its ceiling."""

    # Synthetic arch-monolith pattern: insufficient above 1000 write QPS
    pattern = load_test_pattern({
        "id": "arch-monolith",
        "supports_nfr": [
            {
                "path": "/nfr/throughput/peak_query_per_second_write",
                "op": "<=",
                "value": 1000,
                "reason": "Monolith architecture is insufficient beyond 1000 write QPS"
            }
        ]
    })

    patterns = {"arch-monolith": pattern}
    honored = {"arch-monolith": {"constraints": [], "nfr": []}}

    # Very high QPS: 10000 write QPS (exceeds ceiling)
    spec_high = {"nfr": {"throughput": {"peak_query_per_second_write": 10000.0}}}
    selected, rejected, _ = _filter_by_supports_nfr(
        ["arch-monolith"], patterns, spec_high, honored.copy()
    )

    assert "arch-monolith" not in selected, (
        "arch-monolith should be excluded for very high write QPS (10000 exceeds 1000 ceiling)"
    )
    assert len(rejected) == 1

    print("✅ test_arch_monolith_excluded_for_high_qps passed")


def main():
    """Run all unit tests."""
    print("\nRunning NFR filtering unit tests...\n")

    try:
        test_availability_high_supports_low()
        test_availability_exceeds_capability()
        test_boolean_capability_both_values()
        test_latency_lower_bound_enforced()
        test_multiple_nfr_rules()
        test_boolean_false_requirement()
        test_db_read_replicas_excluded_for_simple_oltp()
        test_db_read_replicas_included_for_high_qps()
        test_arch_monolith_excluded_for_high_qps()

        print("\n✅ All 9 tests passed!\n")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
