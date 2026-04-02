#!/usr/bin/env python3
"""Unit tests for Phase 3.1: supports_constraints filtering."""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _filter_by_supports_constraints


def test_empty_constraints_included():
    """Patterns with empty supports_constraints are neutral (included)."""
    patterns = {
        "gof-singleton": {"supports_constraints": []}
    }
    spec = {"constraints": {"platform": "api"}}

    selected, rejected, _ = _filter_by_supports_constraints(patterns, spec)

    assert "gof-singleton" in selected
    assert len(rejected) == 0
    print("✅ test_empty_constraints_included passed")


def test_matching_constraint_included():
    """Pattern with matching constraint rule is included."""
    patterns = {
        "api-rest": {
            "supports_constraints": [
                {"path": "/constraints/platform", "op": "in", "value": ["api", "web"], "reason": "..."}
            ]
        }
    }
    spec = {"constraints": {"platform": "api"}}

    selected, rejected, _ = _filter_by_supports_constraints(patterns, spec)

    assert "api-rest" in selected
    assert len(rejected) == 0
    print("✅ test_matching_constraint_included passed")


def test_mismatched_constraint_excluded():
    """Pattern with mismatched constraint rule is excluded."""
    patterns = {
        "mobile-specific": {
            "supports_constraints": [
                {"path": "/constraints/platform", "op": "==", "value": "mobile", "reason": "..."}
            ]
        }
    }
    spec = {"constraints": {"platform": "api"}}

    selected, rejected, _ = _filter_by_supports_constraints(patterns, spec)

    assert "mobile-specific" not in selected
    assert len(rejected) == 1
    assert rejected[0]["id"] == "mobile-specific"
    assert rejected[0]["phase"] == "phase_3_1_constraints"
    print("✅ test_mismatched_constraint_excluded passed")


if __name__ == "__main__":
    test_empty_constraints_included()
    test_matching_constraint_included()
    test_mismatched_constraint_excluded()
    print("\n✅ All Phase 3.1 tests passed!")
