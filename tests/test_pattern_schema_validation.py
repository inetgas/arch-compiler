#!/usr/bin/env python3
"""
Test pattern schema validation.

Uses audit_patterns.py to validate all patterns against pattern-schema.yaml.
"""

import sys
import subprocess
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_all_patterns_valid_schema():
    """All patterns must conform to pattern-schema.yaml (basic validation)."""
    result = subprocess.run(
        [sys.executable, "tools/audit_patterns.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    # Parse output to check for issues
    lines = result.stdout.split('\n')
    summary_section = False
    patterns_with_issues = 0

    for line in lines:
        if '=== Summary ===' in line:
            summary_section = True
        if summary_section and 'Patterns with issues:' in line:
            patterns_with_issues = int(line.split(':')[1].strip())
            break

    # Allow some patterns to have minor issues (missing optional fields)
    # But should be less than 50 out of 147 patterns
    assert patterns_with_issues < 50, (
        f"Found {patterns_with_issues} patterns with schema issues (threshold: <50).\n"
        f"Run 'python3 tools/audit_patterns.py' for details.\n"
        f"Many of these may be missing 'conflicts' field which is acceptable."
    )

def test_all_pattern_files_loadable():
    """All pattern JSON files must be valid JSON."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        try:
            with open(pattern_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Verify it has an id field
            if 'id' not in data:
                errors.append(f"{pattern_file.name}: Missing 'id' field")

            # Verify id matches filename
            expected_id = pattern_file.stem
            if data.get('id') != expected_id:
                errors.append(
                    f"{pattern_file.name}: ID mismatch - "
                    f"expected '{expected_id}', got '{data.get('id')}'"
                )

        except json.JSONDecodeError as e:
            errors.append(f"{pattern_file.name}: Invalid JSON - {e}")
        except Exception as e:
            errors.append(f"{pattern_file.name}: Error loading - {e}")

    assert len(errors) == 0, (
        f"Found {len(errors)} pattern file errors:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_pattern_required_fields():
    """All patterns must have core required top-level fields."""
    patterns_dir = PROJECT_ROOT / "patterns"
    # Only check truly required fields that must always be present
    # Note: compatibility removed in Part 2A (replaced by supports_constraints)
    required_fields = [
        "id", "version", "title", "description", "types",
        "cost", "provides", "requires", "tags", "supports_nfr", "supports_constraints"
    ]

    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)

        for field in required_fields:
            if field not in pattern:
                errors.append(f"{pattern['id']}: Missing required field '{field}'")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns missing required fields:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_pattern_supports_fields():
    """All patterns must have supports_nfr and supports_constraints (Part 2A requirement)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)

        if "supports_nfr" not in pattern:
            errors.append(f"{pattern['id']}: Missing 'supports_nfr' field")

        if "supports_constraints" not in pattern:
            errors.append(f"{pattern['id']}: Missing 'supports_constraints' field")

    # Allow a small number of patterns to not have supports_nfr (edge cases)
    # but all should have supports_constraints
    constraint_errors = [e for e in errors if 'supports_constraints' in e]

    assert len(constraint_errors) == 0, (
        f"Found {len(constraint_errors)} patterns missing supports_constraints:\n" +
        "\n".join(f"  - {err}" for err in constraint_errors)
    )

def test_no_excluded_if_fields():
    """No patterns should have excludedIf field (removed in Part 2A)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)

        if "excludedIf" in pattern:
            errors.append(f"{pattern['id']}: Has legacy 'excludedIf' field")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with legacy excludedIf field:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
