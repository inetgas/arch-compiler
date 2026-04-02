#!/usr/bin/env python3
"""
Test pattern data quality.

Validates costs, capabilities, and other quality metrics.
"""

import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_all_patterns_have_cost_provenance():
    """All patterns must have cost.provenance field (added in Part 0B)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        cost = pattern.get("cost", {})
        provenance = cost.get("provenance", {})

        if not provenance:
            errors.append(f"{pattern['id']}: Missing cost.provenance")

        # Check that provenance has key fields
        if "estimatedMonthlyRangeUsd" not in provenance:
            errors.append(f"{pattern['id']}: Missing provenance.estimatedMonthlyRangeUsd")

        if "adoptionCost" not in provenance:
            errors.append(f"{pattern['id']}: Missing provenance.adoptionCost")

        if "licenseCost" not in provenance:
            errors.append(f"{pattern['id']}: Missing provenance.licenseCost")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with cost provenance issues:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_no_runtime_cost_impact_field():
    """No patterns should have runtimeCostImpact field (removed in Part 0B)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        cost = pattern.get("cost", {})

        if "runtimeCostImpact" in cost:
            errors.append(f"{pattern['id']}: Has legacy runtimeCostImpact field")

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with legacy runtimeCostImpact:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_adoption_cost_reasonable_range():
    """Adoption costs should be in reasonable range ($0-$50,000)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        adoption_cost = pattern.get("cost", {}).get("adoptionCost")

        if adoption_cost is None:
            errors.append(f"{pattern['id']}: Missing adoptionCost")
            continue

        if not isinstance(adoption_cost, (int, float)):
            errors.append(f"{pattern['id']}: adoptionCost not a number: {adoption_cost}")
            continue

        if adoption_cost < 0 or adoption_cost > 50000:
            errors.append(
                f"{pattern['id']}: adoptionCost ${adoption_cost} outside range $0-$50K"
            )

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with unreasonable adoption costs:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_monthly_cost_range_valid():
    """Monthly cost ranges must have min <= max and reasonable values."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        cost_range = pattern.get("cost", {}).get("estimatedMonthlyRangeUsd", {})

        if not cost_range:
            errors.append(f"{pattern['id']}: Missing estimatedMonthlyRangeUsd")
            continue

        min_cost = cost_range.get("min")
        max_cost = cost_range.get("max")

        if min_cost is None or max_cost is None:
            errors.append(f"{pattern['id']}: Missing min or max in monthly range")
            continue

        if min_cost > max_cost:
            errors.append(
                f"{pattern['id']}: Monthly cost min ${min_cost} > max ${max_cost}"
            )

        if min_cost < 0:
            errors.append(f"{pattern['id']}: Negative monthly cost min ${min_cost}")

        if max_cost > 100000:
            errors.append(
                f"{pattern['id']}: Monthly cost max ${max_cost} seems very high (>$100K)"
            )

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with invalid monthly costs:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_capabilities_use_hyphens():
    """All capability names must use lowercase-with-hyphens convention (Part 0C fix)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        # Check provides
        for item in pattern.get("provides", []):
            cap = item.get("capability", "")
            if "_" in cap:
                errors.append(
                    f"{pattern['id']} provides: '{cap}' has underscores (should be hyphens)"
                )

        # Check requires
        for item in pattern.get("requires", []):
            cap = item.get("capability", "")
            if "_" in cap:
                errors.append(
                    f"{pattern['id']} requires: '{cap}' has underscores (should be hyphens)"
                )

    assert len(errors) == 0, (
        f"Found {len(errors)} capabilities with incorrect naming:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_no_duplicate_conflicts():
    """Patterns should not have duplicate conflict entries."""
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        conflicts = pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", [])

        # Check for duplicates
        seen = set()
        duplicates = []
        for conflict in conflicts:
            if conflict in seen:
                duplicates.append(conflict)
            seen.add(conflict)

        if duplicates:
            errors.append(
                f"{pattern['id']}: Duplicate conflicts: {', '.join(duplicates)}"
            )

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with duplicate conflicts:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_conflicts_are_sorted():
    """Conflict lists should be sorted alphabetically for consistency (non-critical)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    unsorted = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        conflicts = pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", [])

        if conflicts:
            sorted_conflicts = sorted(conflicts)
            if conflicts != sorted_conflicts:
                unsorted.append(pattern['id'])

    # This is a style preference, not a correctness requirement
    # Just warn if there are many unsorted
    if len(unsorted) > 20:
        print(f"WARNING: {len(unsorted)} patterns have unsorted conflicts (consider sorting)")
    # Don't fail the test for unsorted conflicts

def test_pattern_types_valid():
    """Pattern types must be from valid set."""
    patterns_dir = PROJECT_ROOT / "patterns"
    valid_types = {"design", "build", "deploy", "ops", "cost", "test", "sec", "security", "data", "platform", "coding"}

    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        types = pattern.get("types", [])

        if not types:
            errors.append(f"{pattern['id']}: No types specified")
            continue

        for ptype in types:
            if ptype not in valid_types:
                errors.append(
                    f"{pattern['id']}: Invalid type '{ptype}' "
                    f"(valid: {', '.join(sorted(valid_types))})"
                )

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with invalid types:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_cloud_compatibility_valid():
    """Cloud compatibility must use valid values."""
    patterns_dir = PROJECT_ROOT / "patterns"
    valid_clouds = {"aws", "azure", "gcp", "agnostic", "n/a", "on-prem"}

    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        clouds = pattern.get("compatibility", {}).get("cloud", [])

        for cloud in clouds:
            if cloud not in valid_clouds:
                errors.append(
                    f"{pattern['id']}: Invalid cloud '{cloud}' "
                    f"(valid: {', '.join(sorted(valid_clouds))})"
                )

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with invalid cloud values:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

def test_version_format():
    """Pattern versions should follow semantic versioning (X.Y.Z)."""
    patterns_dir = PROJECT_ROOT / "patterns"
    import re
    version_pattern = re.compile(r'^\d+\.\d+\.\d+$')

    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        version = pattern.get("version", "")

        if not version_pattern.match(version):
            errors.append(
                f"{pattern['id']}: Invalid version '{version}' (expected X.Y.Z format)"
            )

    assert len(errors) == 0, (
        f"Found {len(errors)} patterns with invalid version format:\n" +
        "\n".join(f"  - {err}" for err in errors[:10])
    )

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
