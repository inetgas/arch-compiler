#!/usr/bin/env python3
"""Unit tests for Phase 3.2: supports_nfr filtering."""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _filter_by_supports_nfr


def test_no_spec_nfr_all_pass():
    """If spec has no NFR section, all patterns pass."""
    patterns = {
        "pattern-a": {"supports_nfr": []},
        "pattern-b": {"supports_nfr": [{"path": "/nfr/availability/target", "op": ">=", "value": 0.99, "reason": "..."}]}
    }
    pattern_ids = ["pattern-a", "pattern-b"]
    spec = {"constraints": {"platform": "api"}}  # No NFR section

    selected, rejected, _ = _filter_by_supports_nfr(pattern_ids, patterns, spec, {})

    assert len(selected) == 2
    assert "pattern-a" in selected
    assert "pattern-b" in selected
    assert len(rejected) == 0
    print("✅ test_no_spec_nfr_all_pass passed")


def test_empty_nfr_excluded_when_spec_has_nfr():
    """Empty supports_nfr rejected when spec has NFR requirements."""
    patterns = {
        "pattern-no-nfr": {"supports_nfr": []},
        "pattern-with-nfr": {"supports_nfr": [{"path": "/nfr/availability/target", "op": ">=", "value": 0.99, "reason": "..."}]}
    }
    pattern_ids = ["pattern-no-nfr", "pattern-with-nfr"]
    spec = {
        "constraints": {"platform": "api"},
        "nfr": {"availability": {"target": 0.999}}
    }

    selected, rejected, _ = _filter_by_supports_nfr(pattern_ids, patterns, spec, {})

    # pattern-no-nfr should be rejected (empty NFR support)
    assert "pattern-no-nfr" not in selected
    assert len(rejected) == 1
    assert rejected[0]["id"] == "pattern-no-nfr"
    assert rejected[0]["phase"] == "phase_3_2_nfr"
    assert "No NFR support" in rejected[0]["reason"]

    # pattern-with-nfr should fail rule check (0.999 >= 0.99 is true, so it passes)
    # Wait, let me reconsider - if pattern requires >= 0.99 and spec has 0.999, the rule should pass
    # Let me check the logic: _evaluate_rule(spec, rule) where rule = {"path": "/nfr/availability/target", "op": ">=", "value": 0.99}
    # This evaluates: spec.nfr.availability.target >= 0.99 → 0.999 >= 0.99 → True
    # So pattern-with-nfr should be SELECTED
    assert "pattern-with-nfr" in selected

    print("✅ test_empty_nfr_excluded_when_spec_has_nfr passed")


def test_matching_nfr_included():
    """Pattern with matching NFR rules is included."""
    patterns = {
        "ha-pattern": {
            "supports_nfr": [
                {"path": "/nfr/availability/target", "op": ">=", "value": 0.99, "reason": "Supports 99%+ availability"}
            ]
        }
    }
    pattern_ids = ["ha-pattern"]
    spec = {
        "constraints": {"platform": "api"},
        "nfr": {"availability": {"target": 0.999}}
    }

    selected, rejected, _ = _filter_by_supports_nfr(pattern_ids, patterns, spec, {})

    assert "ha-pattern" in selected
    assert len(rejected) == 0
    print("✅ test_matching_nfr_included passed")


if __name__ == "__main__":
    test_no_spec_nfr_all_pass()
    test_empty_nfr_excluded_when_spec_has_nfr()
    test_matching_nfr_included()
    print("\n✅ All Phase 3.2 tests passed!")
