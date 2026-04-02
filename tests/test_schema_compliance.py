#!/usr/bin/env python3
"""
Test pattern compliance with pattern-schema.yaml.

Validates all patterns against the JSON schema definition.
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_all_patterns_comply_with_schema():
    """All patterns must comply with pattern-schema.yaml."""
    try:
        import yaml
        import jsonschema
    except ImportError:
        import pytest
        pytest.skip("PyYAML and jsonschema required for schema validation")

    # Load schema
    schema_path = PROJECT_ROOT / "schemas" / "pattern-schema.yaml"
    with open(schema_path, 'r') as f:
        schema = yaml.safe_load(f)

    # Validate all patterns
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)

        try:
            jsonschema.validate(instance=pattern, schema=schema)
        except jsonschema.ValidationError as e:
            errors.append(f"{pattern['id']}: {e.message} (path: {list(e.path)})")
        except jsonschema.SchemaError as e:
            errors.append(f"SCHEMA ERROR for {pattern['id']}: {e.message}")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns that don't comply with schema:\n" +
        "\n".join(f"  - {err}" for err in errors[:20]) +
        (f"\n  ... and {len(errors) - 20} more" if len(errors) > 20 else "")
    )

def test_no_compatibility_field():
    """No patterns should have compatibility field (replaced by supports_constraints in Part 2A)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)

        if "compatibility" in pattern:
            errors.append(f"{pattern['id']}: Has legacy 'compatibility' field")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with legacy compatibility field:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_no_generic_variant_fields():
    """No patterns should have generic or variant_of fields (removed in Part 2A Task 7)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)

        if "generic" in pattern:
            errors.append(f"{pattern['id']}: Has legacy 'generic' field")

        if "variant_of" in pattern:
            errors.append(f"{pattern['id']}: Has legacy 'variant_of' field")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with legacy generic/variant_of fields:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_schema_file_loadable():
    """pattern-schema.yaml must be valid YAML."""
    try:
        import yaml
    except ImportError:
        import pytest
        pytest.skip("PyYAML required for schema validation")

    schema_path = PROJECT_ROOT / "schemas" / "pattern-schema.yaml"

    try:
        with open(schema_path, 'r') as f:
            schema = yaml.safe_load(f)

        # Basic schema structure checks
        assert "type" in schema, "Schema missing 'type' field"
        assert schema["type"] == "object", "Schema type must be 'object'"
        assert "properties" in schema, "Schema missing 'properties' field"
        assert "required" in schema, "Schema missing 'required' field"

    except yaml.YAMLError as e:
        assert False, f"pattern-schema.yaml is invalid YAML: {e}"
    except Exception as e:
        assert False, f"Error loading pattern-schema.yaml: {e}"

def test_schema_required_fields_reasonable():
    """Schema required fields should match current pattern structure."""
    try:
        import yaml
    except ImportError:
        import pytest
        pytest.skip("PyYAML required for schema validation")

    schema_path = PROJECT_ROOT / "schemas" / "pattern-schema.yaml"
    with open(schema_path, 'r') as f:
        schema = yaml.safe_load(f)

    required_fields = set(schema.get("required", []))

    # These fields should definitely be required
    essential_fields = {
        "id", "version", "title", "description", "types",
        "cost", "provides", "requires", "tags",
        "supports_nfr", "supports_constraints"
    }

    missing = essential_fields - required_fields

    assert len(missing) == 0, (
        f"Schema missing essential required fields: {missing}"
    )

    # These fields should NOT be in required (legacy or optional)
    forbidden_required = {"compatibility", "generic", "variant_of", "excludedIf"}

    present = forbidden_required & required_fields

    assert len(present) == 0, (
        f"Schema has legacy fields in required: {present}"
    )

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
