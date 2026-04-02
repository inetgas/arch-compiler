#!/usr/bin/env python3
"""
Unit tests for _validate_required_spec_rules in archcompiler.py.

Tests that selected patterns' requires_nfr and requires_constraints rules
are evaluated against the spec, with all failures collected before exit.
"""
import sys
import pytest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _validate_required_spec_rules


def test_no_requires_rules_no_error():
    """Pattern has empty/missing requires_nfr and requires_constraints - no violations returned."""
    patterns = {
        "gof-singleton": {
            "requires_nfr": [],
            "requires_constraints": []
        },
        "gof-factory": {}  # Missing both keys entirely
    }
    spec = {"constraints": {"platform": "api", "cloud": "aws", "language": "python"}}
    selected_ids = ["gof-singleton", "gof-factory"]

    violations = _validate_required_spec_rules(selected_ids, patterns, spec)
    assert violations == []


def test_requires_nfr_pass():
    """Selected pattern has requires_nfr rule that MATCHES spec - no violations returned."""
    patterns = {
        "compliance-hipaa": {
            "requires_nfr": [
                {
                    "path": "/nfr/security/audit_logging",
                    "op": "==",
                    "value": True,
                    "reason": "HIPAA requires comprehensive audit logging for all PHI access."
                }
            ]
        }
    }
    spec = {
        "constraints": {"platform": "api", "cloud": "aws", "language": "python"},
        "nfr": {
            "security": {"audit_logging": True}
        }
    }
    selected_ids = ["compliance-hipaa"]

    violations = _validate_required_spec_rules(selected_ids, patterns, spec)
    assert violations == []


def test_requires_nfr_fail_exits():
    """Selected pattern has requires_nfr rule that FAILS against spec - violations returned."""
    patterns = {
        "compliance-hipaa": {
            "requires_nfr": [
                {
                    "path": "/nfr/security/audit_logging",
                    "op": "==",
                    "value": True,
                    "reason": "HIPAA requires comprehensive audit logging for all PHI access."
                }
            ]
        }
    }
    spec = {
        "constraints": {"platform": "api", "cloud": "aws", "language": "python"},
        "nfr": {
            "security": {"audit_logging": False}  # FAILS the rule
        }
    }
    selected_ids = ["compliance-hipaa"]

    violations = _validate_required_spec_rules(selected_ids, patterns, spec)
    assert len(violations) > 0
    # Error message must contain pattern ID, path, and reason
    assert any(v["pid"] == "compliance-hipaa" for v in violations), f"Pattern ID missing from violations: {violations}"
    assert any(v["path"] == "/nfr/security/audit_logging" for v in violations), f"Path missing from violations: {violations}"
    assert any("HIPAA requires comprehensive audit logging" in v["reason"] for v in violations), f"Reason missing from violations: {violations}"


def test_requires_constraints_fail_exits():
    """Selected pattern has requires_constraints rule that FAILS spec - violations returned."""
    patterns = {
        "on-prem-networking": {
            "requires_constraints": [
                {
                    "path": "/constraints/cloud",
                    "op": "==",
                    "value": "on-prem",
                    "reason": "This pattern only applies to on-premises deployments."
                }
            ]
        }
    }
    spec = {
        "constraints": {"platform": "api", "cloud": "aws", "language": "python"}
    }
    selected_ids = ["on-prem-networking"]

    violations = _validate_required_spec_rules(selected_ids, patterns, spec)
    assert len(violations) > 0
    assert any(v["pid"] == "on-prem-networking" for v in violations), f"Pattern ID missing from violations: {violations}"


def test_multiple_failures_all_reported():
    """Two selected patterns each with one failing rule - both failures appear in violations."""
    patterns = {
        "compliance-hipaa": {
            "requires_nfr": [
                {
                    "path": "/nfr/security/audit_logging",
                    "op": "==",
                    "value": True,
                    "reason": "HIPAA requires comprehensive audit logging for PHI access."
                }
            ]
        },
        "compliance-sox": {
            "requires_nfr": [
                {
                    "path": "/nfr/security/audit_logging",
                    "op": "==",
                    "value": True,
                    "reason": "SOX Section 302 mandates comprehensive audit trails for financial data."
                }
            ]
        }
    }
    spec = {
        "constraints": {"platform": "api", "cloud": "aws", "language": "python"},
        "nfr": {
            "security": {"audit_logging": False}  # Both patterns fail
        }
    }
    selected_ids = ["compliance-hipaa", "compliance-sox"]

    violations = _validate_required_spec_rules(selected_ids, patterns, spec)
    # Both failures must appear (not fail-fast)
    assert any(v["pid"] == "compliance-hipaa" for v in violations), f"First pattern ID missing from violations: {violations}"
    assert any(v["pid"] == "compliance-sox" for v in violations), f"Second pattern ID missing from violations: {violations}"
    assert any("HIPAA requires comprehensive audit logging" in v["reason"] for v in violations), f"First reason missing from violations: {violations}"
    assert any("SOX Section 302 mandates" in v["reason"] for v in violations), f"Second reason missing from violations: {violations}"


def test_unselected_pattern_not_checked():
    """Pattern with failing requires_nfr is NOT in selected_pattern_ids - no violations returned."""
    patterns = {
        "compliance-hipaa": {
            "requires_nfr": [
                {
                    "path": "/nfr/security/audit_logging",
                    "op": "==",
                    "value": True,
                    "reason": "HIPAA requires comprehensive audit logging for all PHI access."
                }
            ]
        },
        "gof-singleton": {
            "requires_nfr": [],
            "requires_constraints": []
        }
    }
    spec = {
        "constraints": {"platform": "api", "cloud": "aws", "language": "python"},
        "nfr": {
            "security": {"audit_logging": False}  # Would fail compliance-hipaa
        }
    }
    # Only gof-singleton is selected; compliance-hipaa is NOT selected
    selected_ids = ["gof-singleton"]

    violations = _validate_required_spec_rules(selected_ids, patterns, spec)
    assert violations == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
