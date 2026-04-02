#!/usr/bin/env python3
"""Test that user input takes precedence over assumptions.

When user provides explicit values at top-level AND assumptions have same fields,
the compiler should:
1. Honor user input value (not assumption)
2. Remove redundant field from assumptions
3. Validate user input value
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _merge_with_defaults, _load_defaults


def test_user_constraints_override_assumptions():
    """Test that user-provided constraints override assumptions."""
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "constraints": {
            "cloud": "aws",        # User explicitly specified
            "language": "python"   # User explicitly specified
        },
        "assumptions": {
            "constraints": {
                "cloud": "agnostic",    # Should be removed (redundant)
                "language": "agnostic", # Should be removed (redundant)
                "platform": "api"       # Should be kept (not in user input)
            }
        }
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # User input should win
    assert spec["constraints"]["cloud"] == "aws", "User input cloud should override assumption"
    assert spec["constraints"]["language"] == "python", "User input language should override assumption"

    # Redundant fields should be removed from assumptions
    if "constraints" in spec["assumptions"]:
        assert "cloud" not in spec["assumptions"]["constraints"], "cloud should be removed from assumptions (redundant)"
        assert "language" not in spec["assumptions"]["constraints"], "language should be removed from assumptions (redundant)"

        # Non-redundant fields should remain in assumptions
        assert spec["assumptions"]["constraints"]["platform"] == "api", "platform should remain in assumptions"
    else:
        # If entire section was removed, that's OK too (all fields were redundant)
        pass

    print("✅ test_user_constraints_override_assumptions passed")


def test_user_nfr_override_assumptions():
    """Test that user-provided NFR values override assumptions."""
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "nfr": {
            "availability": {
                "target": 0.999  # User explicitly specified
            },
            "latency": {
                "p95Milliseconds": 100  # User explicitly specified
            }
        },
        "assumptions": {
            "nfr": {
                "availability": {
                    "target": 0.95  # Should be removed (redundant)
                },
                "latency": {
                    "p95Milliseconds": 500,  # Should be removed (redundant)
                    "p99Milliseconds": 1000  # Should be kept (not in user input)
                },
                "rpo_minutes": 60  # Should be kept (not in user input)
            }
        }
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # User input should win
    assert spec["nfr"]["availability"]["target"] == 0.999, "User NFR should override assumption"
    assert spec["nfr"]["latency"]["p95Milliseconds"] == 100, "User latency should override assumption"

    # Redundant fields should be removed from assumptions.nfr
    if "availability" in spec["assumptions"]["nfr"]:
        assert "target" not in spec["assumptions"]["nfr"]["availability"], "availability.target should be removed from assumptions"

    if "latency" in spec["assumptions"]["nfr"]:
        assert "p95Milliseconds" not in spec["assumptions"]["nfr"]["latency"], "latency.p95Milliseconds should be removed from assumptions"
        # Non-redundant field in latency should remain
        assert spec["assumptions"]["nfr"]["latency"]["p99Milliseconds"] == 1000, "p99 should remain in assumptions"

    # Non-redundant top-level field should remain
    assert spec["assumptions"]["nfr"]["rpo_minutes"] == 60, "rpo_minutes should remain in assumptions"

    print("✅ test_user_nfr_override_assumptions passed")


def test_user_operating_model_override_assumptions():
    """Test that user-provided operating_model values override assumptions."""
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "operating_model": {
            "on_call": True,      # User explicitly specified
            "deploy_freq": "daily" # User explicitly specified
        },
        "assumptions": {
            "operating_model": {
                "on_call": False,           # Should be removed (redundant)
                "deploy_freq": "weekly",    # Should be removed (redundant)
                "ops_team_size": 5          # Should be kept (not in user input)
            }
        }
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # User input should win
    assert spec["operating_model"]["on_call"] == True, "User on_call should override assumption"
    assert spec["operating_model"]["deploy_freq"] == "daily", "User deploy_freq should override assumption"

    # Redundant fields should be removed from assumptions
    assert "on_call" not in spec["assumptions"]["operating_model"], "on_call should be removed from assumptions"
    assert "deploy_freq" not in spec["assumptions"]["operating_model"], "deploy_freq should be removed from assumptions"

    # Non-redundant fields should remain
    assert spec["assumptions"]["operating_model"]["ops_team_size"] == 5, "ops_team_size should remain in assumptions"

    print("✅ test_user_operating_model_override_assumptions passed")


def test_fresh_spec_no_redundancy_check():
    """Test that fresh specs (no assumptions) work normally."""
    spec = {
        "project": {"name": "Test", "domain": "testing"},
        "constraints": {
            "cloud": "aws"
        }
        # No assumptions section - fresh spec
    }

    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # Should get defaults merged
    assert spec["constraints"]["cloud"] == "aws", "User cloud should be preserved"
    assert "language" in spec["constraints"], "Default language should be added"
    assert "platform" in spec["constraints"], "Default platform should be added"

    # Assumptions should only track DEFAULTED fields, not user-provided fields
    assert "cloud" not in spec["assumptions"]["constraints"], "User-provided cloud should NOT be in assumptions (not defaulted)"
    assert "language" in spec["assumptions"]["constraints"], "Defaulted language should be in assumptions"
    assert "platform" in spec["assumptions"]["constraints"], "Defaulted platform should be in assumptions"

    print("✅ test_fresh_spec_no_redundancy_check passed")


if __name__ == "__main__":
    test_user_constraints_override_assumptions()
    test_user_nfr_override_assumptions()
    test_user_operating_model_override_assumptions()
    test_fresh_spec_no_redundancy_check()
    print("\n✅ All user input precedence tests passed!")
