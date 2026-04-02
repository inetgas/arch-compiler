#!/usr/bin/env python3
"""
Test NFR and constraint logic correctness.

Uses audit_nfr_logic.py to validate directional metric bounds and constraint rules.
"""

import sys
import subprocess
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_no_nfr_logic_errors():
    """NFR rules must use valid paths. Both lower and upper bounds on the same path are allowed."""
    subprocess.run(
        ["python3", "tools/audit_nfr_logic.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    # Load audit report
    report_path = PROJECT_ROOT / "reports" / "nfr-constraint-logic-audit.json"
    with open(report_path, 'r') as f:
        audit = json.load(f)

    nfr_issues = len(audit.get("invalid_path", []))

    assert nfr_issues == 0, (
        f"Found {nfr_issues} NFR logic errors:\n"
        f"  - Invalid paths: {nfr_issues}\n"
        f"Run 'python3 tools/audit_nfr_logic.py' for details."
    )

def test_no_constraint_logic_errors():
    """Constraint rules must be valid (no multiple platform entries, no invalid operators, mobile platform present)."""
    report_path = PROJECT_ROOT / "reports" / "nfr-constraint-logic-audit.json"
    with open(report_path, 'r') as f:
        audit = json.load(f)

    # Check for constraint issues (excluding mixed_operators which are valid for tenantCount)
    constraint_issues = (
        len(audit.get("multiple_platform_entries", [])) +
        len(audit.get("invalid_supports_operator", [])) +
        len(audit.get("missing_mobile_platform", []))
    )

    assert constraint_issues == 0, (
        f"Found {constraint_issues} constraint logic errors:\n"
        f"  - Multiple platform entries: {len(audit.get('multiple_platform_entries', []))}\n"
        f"  - Invalid operators: {len(audit.get('invalid_supports_operator', []))}\n"
        f"  - Missing mobile platform: {len(audit.get('missing_mobile_platform', []))}\n"
        f"Run 'python3 tools/audit_nfr_logic.py' for details."
    )

def test_nfr_paths_in_canonical_schema():
    """All NFR paths must exist in canonical-schema.yaml."""
    patterns_dir = PROJECT_ROOT / "patterns"
    canonical_schema_path = PROJECT_ROOT / "schemas" / "canonical-schema.yaml"

    # Load canonical schema to get valid paths
    try:
        import yaml
    except ImportError:
        import pytest
        pytest.skip("PyYAML not installed")

    with open(canonical_schema_path, 'r') as f:
        canonical = yaml.safe_load(f)

    # Extract valid NFR paths from JSON Schema
    valid_nfr_paths = set()

    def extract_paths_from_schema(schema_obj, prefix=""):
        """Extract JSON Pointer paths from JSON Schema properties."""
        if not isinstance(schema_obj, dict):
            return

        # If this has a 'properties' key, it's a schema object with properties
        if 'properties' in schema_obj:
            for prop_name, prop_schema in schema_obj['properties'].items():
                prop_path = f"{prefix}/{prop_name}"
                valid_nfr_paths.add(prop_path)
                # Recursively extract nested properties
                extract_paths_from_schema(prop_schema, prop_path)

    # Start from properties.nfr in the JSON Schema
    if "properties" in canonical and "nfr" in canonical["properties"]:
        extract_paths_from_schema(canonical["properties"]["nfr"], "/nfr")

    # Check all patterns
    errors = []
    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        supports_nfr = pattern.get("supports_nfr", [])
        for rule in supports_nfr:
            path = rule.get("path", "")
            if path and path not in valid_nfr_paths:
                errors.append(f"{pattern['id']}: Invalid NFR path '{path}'")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with invalid NFR paths:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_constraint_paths_in_canonical_schema():
    """All supports_constraints paths must exist in canonical-schema.yaml (any top-level section)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    canonical_schema_path = PROJECT_ROOT / "schemas" / "canonical-schema.yaml"

    # Load canonical schema
    try:
        import yaml
    except ImportError:
        import pytest
        pytest.skip("PyYAML not installed")

    with open(canonical_schema_path, 'r') as f:
        canonical = yaml.safe_load(f)

    # Extract ALL valid paths from JSON Schema (not just /constraints)
    valid_paths = set()

    def extract_paths_from_schema(schema_obj, prefix=""):
        """Extract JSON Pointer paths from JSON Schema properties."""
        if not isinstance(schema_obj, dict):
            return

        # If this has a 'properties' key, it's a schema object with properties
        if 'properties' in schema_obj:
            for prop_name, prop_schema in schema_obj['properties'].items():
                prop_path = f"{prefix}/{prop_name}"
                valid_paths.add(prop_path)
                # Recursively extract nested properties
                extract_paths_from_schema(prop_schema, prop_path)

    # Extract from all top-level sections
    if "properties" in canonical:
        for section_name, section_schema in canonical["properties"].items():
            extract_paths_from_schema(section_schema, f"/{section_name}")

    # Check all patterns
    errors = []
    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        supports_constraints = pattern.get("supports_constraints", [])
        for rule in supports_constraints:
            path = rule.get("path", "")
            if path and path not in valid_paths:
                errors.append(f"{pattern['id']}: Invalid supports_constraints path '{path}'")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with invalid supports_constraints paths:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_valid_operators():
    """All supports_nfr and supports_constraints rules must use valid operators."""
    patterns_dir = PROJECT_ROOT / "patterns"
    valid_operators = {
        "==", "!=", "in", ">", ">=", "<", "<=", "=",
        "contains", "contains-any", "includes-any", "intersects", "exists", "optional"
    }

    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        # Check supports_nfr
        for rule in pattern.get("supports_nfr", []):
            op = rule.get("op")
            if op not in valid_operators:
                errors.append(f"{pattern['id']} supports_nfr: Invalid operator '{op}'")

        # Check supports_constraints
        for rule in pattern.get("supports_constraints", []):
            op = rule.get("op")
            if op not in valid_operators:
                errors.append(f"{pattern['id']} supports_constraints: Invalid operator '{op}'")

    assert len(errors) == 0, (
        f"Found {len(errors)} rules with invalid operators:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
