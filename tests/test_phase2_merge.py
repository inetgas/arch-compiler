#!/usr/bin/env python3
"""Unit tests for Phase 2: Merge with defaults."""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _merge_with_defaults


def test_merge_tracks_only_defaults():
    """Only defaulted fields tracked in assumptions, not user-provided."""
    spec = {
        "constraints": {
            "platform": "api"  # User provided
        }
    }

    defaults = {
        "constraints": {
            "cloud": "agnostic",
            "language": "agnostic",
            "platform": "agnostic"  # Default, but user overrode
        }
    }

    result = _merge_with_defaults(spec, defaults)

    # Spec.constraints unchanged (user provided platform)
    assert spec["constraints"]["platform"] == "api"

    # Assumptions only has defaulted fields
    assert "cloud" in result["assumptions"]["constraints"]
    assert "language" in result["assumptions"]["constraints"]
    assert "platform" not in result["assumptions"]["constraints"]

    print("✅ test_merge_tracks_only_defaults passed")


def test_merge_nested_nfr():
    """Nested NFR objects merged correctly."""
    spec = {
        "nfr": {
            "availability": {
                "target": 0.999  # User provided
            }
        }
    }

    defaults = {
        "nfr": {
            "availability": {
                "target": 0.99
            },
            "rpo_minutes": 60,
            "rto_minutes": 60
        }
    }

    result = _merge_with_defaults(spec, defaults)

    # User's availability.target not in assumptions
    assert "availability" not in result["assumptions"].get("nfr", {})

    # Defaulted rpo/rto in assumptions
    assert result["assumptions"]["nfr"]["rpo_minutes"] == 60
    assert result["assumptions"]["nfr"]["rto_minutes"] == 60

    print("✅ test_merge_nested_nfr passed")


if __name__ == "__main__":
    test_merge_tracks_only_defaults()
    test_merge_nested_nfr()
    print("\n✅ All Phase 2 merge tests passed!")
