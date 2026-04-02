#!/usr/bin/env python3
"""
Unit tests for pattern configuration validation and assumptions.patterns merging.

Tests both:
1. _validate_user_pattern_configs() - Validates user-provided pattern configs
2. _merge_pattern_default_configs() - Merges defaultConfig into assumptions.patterns

Comprehensive test coverage for Tasks 1-4 edge cases.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from archcompiler import _validate_user_pattern_configs, _merge_pattern_default_configs


def test_no_user_patterns():
    """Test validation passes when no user patterns provided."""
    spec = {"project": {"name": "test"}}
    patterns = {}
    # Should not raise
    _validate_user_pattern_configs(spec, patterns)


def test_pattern_not_in_registry():
    """Test validation fails when pattern not found in registry."""
    spec = {
        "patterns": {
            "nonexistent-pattern": {"config": "value"}
        }
    }
    patterns = {}

    with pytest.raises(SystemExit) as exc_info:
        _validate_user_pattern_configs(spec, patterns)

    error_msg = str(exc_info.value)
    assert "nonexistent-pattern" in error_msg
    assert "does not exist in the pattern registry" in error_msg


def test_pattern_without_config_schema():
    """Test validation passes for patterns without configSchema."""
    spec = {
        "patterns": {
            "test-pattern": {
                "arbitrary_field": "value",
                "another_field": 123
            }
        }
    }
    patterns = {
        "test-pattern": {
            "id": "test-pattern",
            "title": "Test Pattern"
            # No configSchema
        }
    }

    # Should not raise - patterns without configSchema accept any config
    _validate_user_pattern_configs(spec, patterns)


def test_pattern_with_empty_config_schema():
    """Test validation passes for patterns with empty properties."""
    spec = {
        "patterns": {
            "test-pattern": {
                "arbitrary_field": "value"
            }
        }
    }
    patterns = {
        "test-pattern": {
            "id": "test-pattern",
            "configSchema": {
                "type": "object",
                "properties": {}
            }
        }
    }

    # Should not raise - no properties to validate
    _validate_user_pattern_configs(spec, patterns)


def test_valid_complete_config():
    """Test validation passes with all required fields provided."""
    spec = {
        "patterns": {
            "cache-aside": {
                "invalidation_strategy": "ttl",
                "ttl_seconds": 3600,
                "max_memory_mb": 512
            }
        }
    }
    patterns = {
        "cache-aside": {
            "id": "cache-aside",
            "configSchema": {
                "type": "object",
                "properties": {
                    "invalidation_strategy": {"type": "string"},
                    "ttl_seconds": {"type": "integer"},
                    "max_memory_mb": {"type": "integer"}
                }
            }
        }
    }

    # Should not raise
    _validate_user_pattern_configs(spec, patterns)


def test_missing_required_fields():
    """Test validation fails with missing required fields."""
    spec = {
        "patterns": {
            "cache-aside": {
                "ttl_seconds": 3600
                # Missing: invalidation_strategy, max_memory_mb
            }
        }
    }
    patterns = {
        "cache-aside": {
            "id": "cache-aside",
            "configSchema": {
                "type": "object",
                "properties": {
                    "invalidation_strategy": {"type": "string"},
                    "ttl_seconds": {"type": "integer"},
                    "max_memory_mb": {"type": "integer"}
                }
            }
        }
    }

    with pytest.raises(SystemExit) as exc_info:
        _validate_user_pattern_configs(spec, patterns)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg
    assert "invalidation_strategy" in error_msg
    assert "max_memory_mb" in error_msg
    assert "Partial configs are not allowed" in error_msg


def test_extra_fields():
    """Test validation fails with extra fields not in schema."""
    spec = {
        "patterns": {
            "cache-aside": {
                "invalidation_strategy": "ttl",
                "ttl_seconds": 3600,
                "max_memory_mb": 512,
                "extra_field": "not in schema",
                "another_extra": 123
            }
        }
    }
    patterns = {
        "cache-aside": {
            "id": "cache-aside",
            "configSchema": {
                "type": "object",
                "properties": {
                    "invalidation_strategy": {"type": "string"},
                    "ttl_seconds": {"type": "integer"},
                    "max_memory_mb": {"type": "integer"}
                }
            }
        }
    }

    with pytest.raises(SystemExit) as exc_info:
        _validate_user_pattern_configs(spec, patterns)

    error_msg = str(exc_info.value)
    assert "Unknown fields" in error_msg
    assert "extra_field" in error_msg or "another_extra" in error_msg
    assert "Partial configs are not allowed" in error_msg


def test_empty_config_with_required_fields():
    """Test validation fails with empty config when schema has fields."""
    spec = {
        "patterns": {
            "cache-aside": {}
        }
    }
    patterns = {
        "cache-aside": {
            "id": "cache-aside",
            "configSchema": {
                "type": "object",
                "properties": {
                    "invalidation_strategy": {"type": "string"},
                    "ttl_seconds": {"type": "integer"},
                    "max_memory_mb": {"type": "integer"}
                }
            }
        }
    }

    with pytest.raises(SystemExit) as exc_info:
        _validate_user_pattern_configs(spec, patterns)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg


def test_both_missing_and_extra_fields():
    """Test validation reports both missing and extra fields."""
    spec = {
        "patterns": {
            "cache-aside": {
                "ttl_seconds": 3600,
                "extra_field": "not in schema"
                # Missing: invalidation_strategy, max_memory_mb
            }
        }
    }
    patterns = {
        "cache-aside": {
            "id": "cache-aside",
            "configSchema": {
                "type": "object",
                "properties": {
                    "invalidation_strategy": {"type": "string"},
                    "ttl_seconds": {"type": "integer"},
                    "max_memory_mb": {"type": "integer"}
                }
            }
        }
    }

    with pytest.raises(SystemExit) as exc_info:
        _validate_user_pattern_configs(spec, patterns)

    error_msg = str(exc_info.value)
    assert "Missing required fields" in error_msg
    assert "Unknown fields" in error_msg


def test_multiple_patterns_with_errors():
    """Test validation reports errors for multiple patterns."""
    spec = {
        "patterns": {
            "pattern-1": {
                "field1": "value"
                # Missing: field2
            },
            "pattern-2": {
                "field1": "value",
                "field2": "value",
                "extra": "not in schema"
            }
        }
    }
    patterns = {
        "pattern-1": {
            "id": "pattern-1",
            "configSchema": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "string"}
                }
            }
        },
        "pattern-2": {
            "id": "pattern-2",
            "configSchema": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "string"}
                }
            }
        }
    }

    with pytest.raises(SystemExit) as exc_info:
        _validate_user_pattern_configs(spec, patterns)

    error_msg = str(exc_info.value)
    assert "pattern-1" in error_msg
    assert "pattern-2" in error_msg


def test_mixed_valid_and_invalid_patterns():
    """Test validation fails if any pattern has errors, even if others are valid."""
    spec = {
        "patterns": {
            "valid-pattern": {
                "field1": "value",
                "field2": "value"
            },
            "invalid-pattern": {
                "field1": "value"
                # Missing: field2
            }
        }
    }
    patterns = {
        "valid-pattern": {
            "id": "valid-pattern",
            "configSchema": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "string"}
                }
            }
        },
        "invalid-pattern": {
            "id": "invalid-pattern",
            "configSchema": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string"},
                    "field2": {"type": "string"}
                }
            }
        }
    }

    with pytest.raises(SystemExit) as exc_info:
        _validate_user_pattern_configs(spec, patterns)

    error_msg = str(exc_info.value)
    assert "invalid-pattern" in error_msg
    assert "Missing required fields" in error_msg
    # valid-pattern should not be mentioned in error message
    # (only invalid patterns are listed)
    # Note: We check for "Pattern 'valid-pattern'" to avoid false positive with "invalid-pattern"
    assert "Pattern 'valid-pattern'" not in error_msg


# =============================================================================
# Tests for _merge_pattern_default_configs()
# =============================================================================

def test_merge_includes_patterns_without_default_config():
    """All selected patterns appear in assumptions.patterns, even those without defaultConfig."""
    patterns = {
        "cache-aside": {
            "defaultConfig": {
                "eviction_policy": "lru",
                "ttl_seconds": 3600
            }
        },
        "api-graphql-schema-first": {
            # No defaultConfig field
        }
    }
    spec = {"assumptions": {}}

    _merge_pattern_default_configs(
        ["cache-aside", "api-graphql-schema-first"],
        patterns,
        spec,
        {}
    )

    # Both patterns should be in assumptions
    assert "patterns" in spec["assumptions"]
    assert "cache-aside" in spec["assumptions"]["patterns"]
    assert "api-graphql-schema-first" in spec["assumptions"]["patterns"]

    # Pattern with defaultConfig shows full config
    assert spec["assumptions"]["patterns"]["cache-aside"]["eviction_policy"] == "lru"
    assert spec["assumptions"]["patterns"]["cache-aside"]["ttl_seconds"] == 3600

    # Pattern without defaultConfig shows empty {}
    assert spec["assumptions"]["patterns"]["api-graphql-schema-first"] == {}


def test_merge_skips_user_provided_configs():
    """Patterns with user-provided config NOT in assumptions.patterns."""
    patterns = {
        "cache-aside": {
            "defaultConfig": {
                "eviction_policy": "lru",
                "ttl_seconds": 3600
            }
        },
        "db-read-replicas": {
            "defaultConfig": {
                "replica_count": 2,
                "lag_threshold_ms": 100
            }
        }
    }
    spec = {
        "patterns": {
            "cache-aside": {
                "eviction_policy": "lfu",  # User provided custom config
                "ttl_seconds": 7200
            }
        },
        "assumptions": {}
    }

    _merge_pattern_default_configs(
        ["cache-aside", "db-read-replicas"],
        patterns,
        spec,
        {}
    )

    # cache-aside has user config → NOT in assumptions
    assert "cache-aside" not in spec["assumptions"].get("patterns", {})

    # db-read-replicas has no user config → IN assumptions with defaults
    assert "db-read-replicas" in spec["assumptions"]["patterns"]
    assert spec["assumptions"]["patterns"]["db-read-replicas"]["replica_count"] == 2
    assert spec["assumptions"]["patterns"]["db-read-replicas"]["lag_threshold_ms"] == 100

    # User config stays in patterns section
    assert spec["patterns"]["cache-aside"]["eviction_policy"] == "lfu"
    assert spec["patterns"]["cache-aside"]["ttl_seconds"] == 7200


def test_merge_with_empty_selected_patterns():
    """No patterns selected → assumptions.patterns should be empty or not exist."""
    patterns = {}
    spec = {"assumptions": {}}

    _merge_pattern_default_configs([], patterns, spec, {})

    # Either assumptions.patterns doesn't exist or is empty
    if "patterns" in spec.get("assumptions", {}):
        assert len(spec["assumptions"]["patterns"]) == 0


def test_merge_multiple_patterns_with_defaults():
    """Multiple patterns with defaultConfig all merged correctly."""
    patterns = {
        "pattern-a": {
            "defaultConfig": {
                "field_a1": "value_a1",
                "field_a2": 123
            }
        },
        "pattern-b": {
            "defaultConfig": {
                "field_b1": "value_b1",
                "field_b2": 456
            }
        },
        "pattern-c": {
            "defaultConfig": {
                "field_c1": "value_c1"
            }
        }
    }
    spec = {"assumptions": {}}

    _merge_pattern_default_configs(
        ["pattern-a", "pattern-b", "pattern-c"],
        patterns,
        spec,
        {}
    )

    # All patterns in assumptions
    assert len(spec["assumptions"]["patterns"]) == 3

    # Verify each pattern's config
    assert spec["assumptions"]["patterns"]["pattern-a"]["field_a1"] == "value_a1"
    assert spec["assumptions"]["patterns"]["pattern-a"]["field_a2"] == 123
    assert spec["assumptions"]["patterns"]["pattern-b"]["field_b1"] == "value_b1"
    assert spec["assumptions"]["patterns"]["pattern-b"]["field_b2"] == 456
    assert spec["assumptions"]["patterns"]["pattern-c"]["field_c1"] == "value_c1"


def test_merge_preserves_existing_assumptions():
    """Merging pattern configs preserves other assumptions sections."""
    patterns = {
        "cache-aside": {
            "defaultConfig": {
                "ttl_seconds": 3600
            }
        }
    }
    spec = {
        "assumptions": {
            "constraints": {
                "cloud": "aws"
            },
            "nfr": {
                "availability": {
                    "target_uptime_percent": 99.9
                }
            }
        }
    }

    _merge_pattern_default_configs(["cache-aside"], patterns, spec, {})

    # Pattern config added
    assert "cache-aside" in spec["assumptions"]["patterns"]
    assert spec["assumptions"]["patterns"]["cache-aside"]["ttl_seconds"] == 3600

    # Existing assumptions preserved
    assert spec["assumptions"]["constraints"]["cloud"] == "aws"
    assert spec["assumptions"]["nfr"]["availability"]["target_uptime_percent"] == 99.9


def test_merge_pattern_not_in_registry():
    """Pattern ID in selected list but not in registry → should raise KeyError."""
    patterns = {
        "existing-pattern": {
            "defaultConfig": {
                "field1": "value1"
            }
        }
    }
    spec = {"assumptions": {}}

    # nonexistent-pattern is in selected list but not in patterns registry
    # This should raise KeyError since pattern filtering should have caught this earlier
    with pytest.raises(KeyError) as exc_info:
        _merge_pattern_default_configs(
            ["existing-pattern", "nonexistent-pattern"],
            patterns,
            spec,
            {}
        )

    assert "nonexistent-pattern" in str(exc_info.value)


def test_merge_complex_defaultconfig():
    """Pattern with nested/complex defaultConfig structure."""
    patterns = {
        "complex-pattern": {
            "defaultConfig": {
                "simple_field": "value",
                "nested_object": {
                    "inner_field1": "inner_value1",
                    "inner_field2": 42
                },
                "array_field": ["item1", "item2", "item3"],
                "boolean_field": True,
                "null_field": None
            }
        }
    }
    spec = {"assumptions": {}}

    _merge_pattern_default_configs(["complex-pattern"], patterns, spec, {})

    config = spec["assumptions"]["patterns"]["complex-pattern"]

    # Verify all field types preserved
    assert config["simple_field"] == "value"
    assert config["nested_object"]["inner_field1"] == "inner_value1"
    assert config["nested_object"]["inner_field2"] == 42
    assert config["array_field"] == ["item1", "item2", "item3"]
    assert config["boolean_field"] is True
    assert config["null_field"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
