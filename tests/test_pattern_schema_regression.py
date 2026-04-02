#!/usr/bin/env python3
"""
Regression tests for pattern schema validation.

Run after:
- Modifying pattern-schema.yaml
- Bulk updates to patterns/*.json
- Changes to pattern structure

Ensures all patterns still validate against schema.

Usage:
    cd tests
    pytest test_pattern_schema_regression.py -v
"""
import json
import yaml
import jsonschema
from pathlib import Path


def test_all_patterns_validate_against_schema():
    """All patterns must validate against pattern-schema.yaml."""
    schema_path = Path(__file__).parent.parent / "schemas" / "pattern-schema.yaml"
    patterns_dir = Path(__file__).parent.parent / "patterns"

    with open(schema_path) as f:
        schema = yaml.safe_load(f)

    errors = []

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        try:
            jsonschema.validate(pattern, schema)
        except jsonschema.ValidationError as e:
            errors.append(f"{pattern_file.name}: {e.message}")

    if errors:
        raise AssertionError(
            f"Pattern validation failed for {len(errors)} patterns:\n" +
            "\n".join(f"  - {err}" for err in errors)
        )


def test_no_patterns_have_config_schema_required():
    """After Task 3, no patterns should have configSchema.required."""
    patterns_dir = Path(__file__).parent.parent / "patterns"

    patterns_with_required = []

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        if "configSchema" in pattern and "required" in pattern["configSchema"]:
            patterns_with_required.append(pattern["id"])

    if patterns_with_required:
        raise AssertionError(
            f"Found {len(patterns_with_required)} patterns with configSchema.required:\n" +
            "\n".join(f"  - {pid}" for pid in patterns_with_required) +
            "\n\nAll should have been removed in Task 3."
        )


def test_patterns_with_config_schema_have_properties():
    """Patterns with configSchema must have properties defined."""
    patterns_dir = Path(__file__).parent.parent / "patterns"

    patterns_with_empty_properties = []

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        if "configSchema" in pattern:
            config_schema = pattern["configSchema"]

            # Check if properties field exists and is non-empty
            if "properties" not in config_schema:
                patterns_with_empty_properties.append(
                    f"{pattern['id']} (missing properties field)"
                )
            elif not config_schema["properties"]:
                patterns_with_empty_properties.append(
                    f"{pattern['id']} (empty properties object)"
                )

    if patterns_with_empty_properties:
        raise AssertionError(
            f"Found {len(patterns_with_empty_properties)} patterns with configSchema but no/empty properties:\n" +
            "\n".join(f"  - {p}" for p in patterns_with_empty_properties) +
            "\n\nPatterns with configSchema should define at least one property."
        )


def test_default_config_matches_config_schema():
    """Patterns with BOTH defaultConfig and configSchema must have matching keys."""
    patterns_dir = Path(__file__).parent.parent / "patterns"

    mismatches = []

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        # Only check patterns with BOTH fields
        if "defaultConfig" not in pattern or "configSchema" not in pattern:
            continue

        default_config = pattern["defaultConfig"]
        config_schema = pattern["configSchema"]

        # Skip if configSchema doesn't have properties
        if "properties" not in config_schema:
            continue

        schema_properties = config_schema["properties"]

        # Get keys from both
        default_keys = set(default_config.keys())
        schema_keys = set(schema_properties.keys())

        # Check for mismatches
        missing_in_default = schema_keys - default_keys
        extra_in_default = default_keys - schema_keys

        if missing_in_default or extra_in_default:
            mismatch_details = []
            if missing_in_default:
                mismatch_details.append(
                    f"Missing in defaultConfig: {sorted(missing_in_default)}"
                )
            if extra_in_default:
                mismatch_details.append(
                    f"Extra in defaultConfig: {sorted(extra_in_default)}"
                )

            mismatches.append(
                f"{pattern['id']}: {'; '.join(mismatch_details)}"
            )

    if mismatches:
        raise AssertionError(
            f"Found {len(mismatches)} patterns with defaultConfig/configSchema key mismatches:\n" +
            "\n".join(f"  - {m}" for m in mismatches) +
            "\n\nKeys in defaultConfig must exactly match configSchema.properties keys."
        )


def test_config_schema_has_valid_structure():
    """Patterns with configSchema must have valid JSON Schema structure."""
    patterns_dir = Path(__file__).parent.parent / "patterns"

    invalid_schemas = []

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        if "configSchema" not in pattern:
            continue

        config_schema = pattern["configSchema"]
        pattern_id = pattern["id"]

        # Check that configSchema has type: object
        if "type" not in config_schema:
            invalid_schemas.append(f"{pattern_id} (missing 'type' field)")
        elif config_schema["type"] != "object":
            invalid_schemas.append(
                f"{pattern_id} (type is '{config_schema['type']}', expected 'object')"
            )

        # Check that properties exist
        if "properties" not in config_schema:
            invalid_schemas.append(f"{pattern_id} (missing 'properties' field)")
            continue

        # Check that each property has a type
        properties = config_schema["properties"]
        for prop_name, prop_schema in properties.items():
            if "type" not in prop_schema:
                invalid_schemas.append(
                    f"{pattern_id}.{prop_name} (missing 'type' field)"
                )

    if invalid_schemas:
        raise AssertionError(
            f"Found {len(invalid_schemas)} configSchema structure issues:\n" +
            "\n".join(f"  - {s}" for s in invalid_schemas) +
            "\n\nconfigSchema must have type: 'object' and properties with type definitions."
        )


def test_default_config_values_match_schema_types():
    """Values in defaultConfig must match types defined in configSchema."""
    patterns_dir = Path(__file__).parent.parent / "patterns"

    type_mismatches = []

    # JSON type mapping
    json_types = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None)
    }

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        # Only check patterns with BOTH fields
        if "defaultConfig" not in pattern or "configSchema" not in pattern:
            continue

        default_config = pattern["defaultConfig"]
        config_schema = pattern["configSchema"]

        if "properties" not in config_schema:
            continue

        schema_properties = config_schema["properties"]
        pattern_id = pattern["id"]

        # Check each key that exists in both
        for key, value in default_config.items():
            if key not in schema_properties:
                continue

            prop_schema = schema_properties[key]
            if "type" not in prop_schema:
                continue

            expected_type = prop_schema["type"]

            # Handle type arrays (union types like ["string", "null"])
            if isinstance(expected_type, list):
                # Check if value matches ANY of the types
                matches_any = False
                for t in expected_type:
                    if t in json_types and isinstance(value, json_types[t]):
                        matches_any = True
                        break
                if not matches_any:
                    type_mismatches.append(
                        f"{pattern_id}.{key}: value is {type(value).__name__}, "
                        f"schema expects one of {expected_type}"
                    )
            else:
                # Single type
                if expected_type not in json_types:
                    continue

                python_type = json_types[expected_type]

                if not isinstance(value, python_type):
                    type_mismatches.append(
                        f"{pattern_id}.{key}: value is {type(value).__name__}, "
                        f"schema expects {expected_type}"
                    )

    if type_mismatches:
        raise AssertionError(
            f"Found {len(type_mismatches)} type mismatches between defaultConfig values and configSchema types:\n" +
            "\n".join(f"  - {m}" for m in type_mismatches) +
            "\n\ndefaultConfig values must match the types defined in configSchema."
        )


def test_default_config_values_satisfy_schema_constraints():
    """Values in defaultConfig must satisfy enum/min/max constraints in configSchema."""
    patterns_dir = Path(__file__).parent.parent / "patterns"

    constraint_violations = []

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        # Only check patterns with BOTH fields
        if "defaultConfig" not in pattern or "configSchema" not in pattern:
            continue

        default_config = pattern["defaultConfig"]
        config_schema = pattern["configSchema"]

        if "properties" not in config_schema:
            continue

        schema_properties = config_schema["properties"]
        pattern_id = pattern["id"]

        # Check each key that exists in both
        for key, value in default_config.items():
            if key not in schema_properties:
                continue

            prop_schema = schema_properties[key]

            # Check enum constraint
            if "enum" in prop_schema:
                if value not in prop_schema["enum"]:
                    constraint_violations.append(
                        f"{pattern_id}.{key}: value '{value}' not in enum {prop_schema['enum']}"
                    )

            # Check minimum constraint (for numbers)
            if "minimum" in prop_schema:
                if isinstance(value, (int, float)) and value < prop_schema["minimum"]:
                    constraint_violations.append(
                        f"{pattern_id}.{key}: value {value} < minimum {prop_schema['minimum']}"
                    )

            # Check maximum constraint (for numbers)
            if "maximum" in prop_schema:
                if isinstance(value, (int, float)) and value > prop_schema["maximum"]:
                    constraint_violations.append(
                        f"{pattern_id}.{key}: value {value} > maximum {prop_schema['maximum']}"
                    )

    if constraint_violations:
        raise AssertionError(
            f"Found {len(constraint_violations)} constraint violations in defaultConfig:\n" +
            "\n".join(f"  - {v}" for v in constraint_violations) +
            "\n\ndefaultConfig values must satisfy enum/min/max constraints in configSchema."
        )


def test_patterns_count():
    """Verify expected number of patterns exists (regression check)."""
    patterns_dir = Path(__file__).parent.parent / "patterns"

    pattern_files = list(patterns_dir.glob("*.json"))
    pattern_count = len(pattern_files)

    # After Task 3, we expect 147 patterns
    # This test will fail if patterns are accidentally deleted
    expected_min = 145  # Allow for slight variation
    expected_max = 150

    if pattern_count < expected_min:
        raise AssertionError(
            f"Found only {pattern_count} patterns, expected at least {expected_min}. "
            f"Patterns may have been accidentally deleted."
        )

    if pattern_count > expected_max:
        # This is not necessarily an error, just informational
        print(f"Note: Found {pattern_count} patterns, more than expected {expected_max}. "
              f"This may indicate new patterns were added.")


if __name__ == "__main__":
    # Allow running tests directly for quick validation
    import sys

    tests = [
        ("All patterns validate against schema", test_all_patterns_validate_against_schema),
        ("No patterns have configSchema.required", test_no_patterns_have_config_schema_required),
        ("Patterns with configSchema have properties", test_patterns_with_config_schema_have_properties),
        ("defaultConfig matches configSchema keys", test_default_config_matches_config_schema),
        ("configSchema has valid structure", test_config_schema_has_valid_structure),
        ("defaultConfig values match schema types", test_default_config_values_match_schema_types),
        ("defaultConfig values satisfy constraints", test_default_config_values_satisfy_schema_constraints),
        ("Pattern count is reasonable", test_patterns_count),
    ]

    failed = []
    passed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✓ {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_name}")
            print(f"  {str(e)}\n")
            failed.append(test_name)

    print(f"\n{passed}/{len(tests)} tests passed")

    if failed:
        print(f"\nFailed tests:")
        for test_name in failed:
            print(f"  - {test_name}")
        sys.exit(1)
    else:
        print("\nAll regression tests passed!")
        sys.exit(0)
