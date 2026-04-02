#!/usr/bin/env python3
"""Unit tests for Phase 3.4: defaultConfig merge."""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _merge_pattern_default_configs


def test_merge_full_defaultconfig():
    """User didn't provide config → all defaults merged into assumptions."""
    patterns = {
        "cache-aside": {
            "defaultConfig": {
                "eviction_policy": "lru",
                "ttl_seconds": 3600
            }
        }
    }
    spec = {"assumptions": {}}

    _merge_pattern_default_configs(["cache-aside"], patterns, spec, {})

    assert "cache-aside" in spec["assumptions"]["patterns"]
    assert spec["assumptions"]["patterns"]["cache-aside"]["eviction_policy"] == "lru"
    assert spec["assumptions"]["patterns"]["cache-aside"]["ttl_seconds"] == 3600
    print("✅ test_merge_full_defaultconfig passed")


def test_user_provided_config_not_in_assumptions():
    """User provided config → pattern NOT in assumptions."""
    patterns = {
        "cache-aside": {
            "defaultConfig": {
                "eviction_policy": "lru",
                "ttl_seconds": 3600
            }
        }
    }
    spec = {
        "patterns": {
            "cache-aside": {
                "eviction_policy": "lfu"  # User provided
            }
        },
        "assumptions": {}
    }

    _merge_pattern_default_configs(["cache-aside"], patterns, spec, {})

    # User-provided config → should NOT be in assumptions at all
    assert "cache-aside" not in spec["assumptions"].get("patterns", {})
    # User config stays in patterns section
    assert spec["patterns"]["cache-aside"]["eviction_policy"] == "lfu"
    print("✅ test_user_provided_config_not_in_assumptions passed")


def test_pattern_without_defaultconfig():
    """Pattern without defaultConfig → empty {} in assumptions."""
    patterns = {
        "api-graphql-schema-first": {
            # No defaultConfig field
        }
    }
    spec = {"assumptions": {}}

    _merge_pattern_default_configs(["api-graphql-schema-first"], patterns, spec, {})

    # Pattern should be in assumptions with empty config
    assert "api-graphql-schema-first" in spec["assumptions"]["patterns"]
    assert spec["assumptions"]["patterns"]["api-graphql-schema-first"] == {}
    print("✅ test_pattern_without_defaultconfig passed")


if __name__ == "__main__":
    test_merge_full_defaultconfig()
    test_user_provided_config_not_in_assumptions()
    test_pattern_without_defaultconfig()
    print("\n✅ All Phase 3.4 tests passed!")
