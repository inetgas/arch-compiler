#!/usr/bin/env python3
"""Test that assumptions are preserved during recompilation."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _merge_with_defaults, _load_defaults


def test_preserve_partial_assumptions_operating_model():
    """
    When spec has partial assumptions.operating_model, only merge missing fields.
    User provided: on_call, deploy_freq, ops_team_size
    Should merge: single_resource_monthly_ops_usd, amortization_months
    """
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "assumptions": {
            "operating_model": {
                "on_call": False,
                "deploy_freq": "weekly",
                "ops_team_size": 0
            }
        }
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # User-provided values should be preserved
    assert spec["assumptions"]["operating_model"]["on_call"] == False
    assert spec["assumptions"]["operating_model"]["deploy_freq"] == "weekly"
    assert spec["assumptions"]["operating_model"]["ops_team_size"] == 0

    # Missing fields should be merged
    assert "single_resource_monthly_ops_usd" in spec["assumptions"]["operating_model"]
    assert "amortization_months" in spec["assumptions"]["operating_model"]

    # Top-level operating_model should have ALL fields (user + defaults)
    assert "on_call" in spec["operating_model"]
    assert "single_resource_monthly_ops_usd" in spec["operating_model"]

    print("✅ test_preserve_partial_assumptions_operating_model passed")


def test_preserve_custom_assumption_values():
    """
    When spec has assumptions with CUSTOM values (different from defaults),
    preserve those custom values, don't overwrite with defaults.
    """
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "assumptions": {
            "operating_model": {
                "on_call": True,  # Custom: default is False
                "deploy_freq": "daily",  # Custom: default is weekly
                "ops_team_size": 5  # Custom: default is 0
            }
        }
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # Custom values should be PRESERVED (not overwritten with defaults)
    assert spec["assumptions"]["operating_model"]["on_call"] == True, "on_call was overwritten!"
    assert spec["assumptions"]["operating_model"]["deploy_freq"] == "daily", "deploy_freq was overwritten!"
    assert spec["assumptions"]["operating_model"]["ops_team_size"] == 5, "ops_team_size was overwritten!"

    # Missing fields should be merged
    assert "single_resource_monthly_ops_usd" in spec["assumptions"]["operating_model"]
    assert "amortization_months" in spec["assumptions"]["operating_model"]

    # Top-level should also have custom values
    assert spec["operating_model"]["on_call"] == True
    assert spec["operating_model"]["ops_team_size"] == 5

    print("✅ test_preserve_custom_assumption_values passed")


def test_no_merge_when_assumptions_complete():
    """
    When spec has complete assumptions (all fields from defaults), don't merge anything.
    """
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "assumptions": {
            "operating_model": {
                "on_call": False,
                "deploy_freq": "weekly",
                "ops_team_size": 0,
                "single_resource_monthly_ops_usd": 10000,
                "amortization_months": 24
            }
        }
    }

    defaults = _load_defaults()

    # Store original assumptions
    original_assumptions = dict(spec["assumptions"]["operating_model"])

    _merge_with_defaults(spec, defaults)

    # Assumptions should be UNCHANGED (all fields already present)
    assert spec["assumptions"]["operating_model"] == original_assumptions

    print("✅ test_no_merge_when_assumptions_complete passed")


def test_add_new_assumption_sections():
    """
    CORRECTED: If user didn't provide assumptions.constraints, ADD it during merge.
    User feedback: "add new sections - if user didn't have assumptions.constraints, add it"
    """
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "assumptions": {
            "operating_model": {
                "on_call": False,
                "deploy_freq": "weekly",
                "ops_team_size": 0
            }
        }
        # NOTE: No assumptions.constraints provided
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # SHOULD add assumptions.constraints (from defaults)
    assert "constraints" in spec["assumptions"], "assumptions.constraints should be added!"

    # SHOULD add assumptions.nfr (from defaults)
    assert "nfr" in spec["assumptions"], "assumptions.nfr should be added!"

    # SHOULD add assumptions.cost (from defaults)
    assert "cost" in spec["assumptions"], "assumptions.cost should be added!"

    # But operating_model values should still be preserved
    assert spec["assumptions"]["operating_model"]["on_call"] == False
    assert spec["assumptions"]["operating_model"]["deploy_freq"] == "weekly"
    assert spec["assumptions"]["operating_model"]["ops_team_size"] == 0

    print("✅ test_add_new_assumption_sections passed")


def test_fresh_spec_normal_merge():
    """
    When spec has NO assumptions, do normal merge (track everything as assumptions).
    """
    spec = {
        "project": {"name": "Test", "domain": "testing"}
        # NO assumptions section
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # Should create assumptions and populate all sections
    assert "assumptions" in spec
    assert "constraints" in spec["assumptions"]
    assert "nfr" in spec["assumptions"]
    assert "operating_model" in spec["assumptions"]
    assert "cost" in spec["assumptions"]

    # All fields should be tracked as assumptions
    assert "cloud" in spec["assumptions"]["constraints"]
    assert "on_call" in spec["assumptions"]["operating_model"]

    print("✅ test_fresh_spec_normal_merge passed")


if __name__ == "__main__":
    test_preserve_partial_assumptions_operating_model()
    test_preserve_custom_assumption_values()
    test_no_merge_when_assumptions_complete()
    test_add_new_assumption_sections()
    test_fresh_spec_normal_merge()
    print("\n✅ All tests passed!")
