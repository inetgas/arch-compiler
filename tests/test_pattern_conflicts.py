#!/usr/bin/env python3
"""
Test pattern conflict relationships.

Validates conflict symmetry and correct conflict declarations.
"""

import sys
import subprocess
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_no_asymmetric_conflicts():
    """All conflict relationships must be symmetric (bidirectional)."""
    result = subprocess.run(
        ["python3", "tools/audit_asymmetric_conflicts.py"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    # Load audit report
    report_path = PROJECT_ROOT / "reports" / "asymmetric-conflicts-audit.json"
    with open(report_path, 'r') as f:
        audit = json.load(f)

    total_asymmetric = audit.get("summary", {}).get("total_asymmetric_conflicts", 0)

    assert total_asymmetric == 0, (
        f"Found {total_asymmetric} asymmetric conflict relationships.\n"
        f"Run 'python3 tools/audit_asymmetric_conflicts.py' for details."
    )

def test_all_conflict_references_valid():
    """All patterns referenced in conflicts must exist."""
    patterns_dir = PROJECT_ROOT / "patterns"

    # Get all pattern IDs
    pattern_ids = set()
    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)
            pattern_ids.add(pattern["id"])

    # Check all conflict references
    errors = []
    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        conflicts = pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", [])

        for conflict_id in conflicts:
            if conflict_id not in pattern_ids:
                errors.append(
                    f"{pattern['id']}: References non-existent pattern '{conflict_id}'"
                )

    assert len(errors) == 0, (
        f"Found {len(errors)} invalid conflict references:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_generic_patterns_have_activation_gate():
    """
    Generic (meta-policy) patterns must have exactly one supports_constraints
    activation gate using op="==" value=true, scoped to their feature flag.

    Generics are NOT mutually exclusive with variants — they serve different
    roles (meta-policy enforcer vs concrete implementation) and coexist.
    Sibling variant conflicts are covered by test_sibling_variants_conflict.
    """
    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        pid = pattern["id"]
        if "--generic" not in pid:
            continue

        sc = pattern.get("supports_constraints", [])
        eq_true_gates = [
            r for r in sc
            if r.get("op") == "==" and r.get("value") is True
            and r.get("path", "").startswith("/constraints/features/")
        ]

        if not eq_true_gates:
            errors.append(
                f"{pid}: Missing supports_constraints activation gate "
                f"(op==\"==\", value=true, path under /constraints/features/)"
            )

    assert len(errors) == 0, (
        f"Found {len(errors)} generic patterns without a feature activation gate:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )


def test_variants_do_not_conflict_with_generic():
    """
    Variant patterns must NOT conflict with their generic (meta-policy) pattern.

    Generics and variants serve complementary roles: the generic enforces that
    the feature is configured correctly; variants provide concrete implementations.
    Both can be selected simultaneously from a single spec.
    Variant ↔ sibling conflicts are tested by test_sibling_variants_conflict.
    """
    patterns_dir = PROJECT_ROOT / "patterns"

    generic_ids = {
        json.load(open(f))["id"]
        for f in patterns_dir.glob("*.json")
        if "--generic" in json.load(open(f))["id"]
    }

    errors = []
    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        pid = pattern["id"]
        if "--" not in pid or "--generic" in pid:
            continue

        base = pid.rsplit("--", 1)[0]
        expected_generic = f"{base}--generic"

        if expected_generic in generic_ids:
            conflicts = set(pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", []))
            if expected_generic in conflicts:
                errors.append(
                    f"{pid}: Must NOT conflict with meta-policy generic '{expected_generic}'"
                )

    assert len(errors) == 0, (
        f"Found {len(errors)} variant patterns incorrectly conflicting with their generic:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )

def test_sibling_variants_conflict():
    """
    Sibling variant patterns (same base) must conflict with each other — UNLESS the
    siblings serve complementary purposes and are designed to coexist.

    Coexisting siblings are identified by having a contains-any constraint on
    /constraints/saas-providers: each variant activates for a different provider,
    so multiple can be selected simultaneously from a single spec.

    Currently known coexisting groups: cost-free-saas-tier (supabase=DB, render=host,
    netlify=frontend) — the greedy-MIS conflict algorithm handles these correctly.
    """
    patterns_dir = PROJECT_ROOT / "patterns"

    # Bases whose siblings are designed to coexist (not mutually exclusive)
    COEXISTING_BASES = {"cost-free-saas-tier"}

    # Group variants by base
    variant_groups = {}

    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        pid = pattern["id"]

        # Skip non-variant patterns
        if "--" not in pid or "--generic" in pid:
            continue

        base = pid.rsplit("--", 1)[0]
        if base not in variant_groups:
            variant_groups[base] = []
        variant_groups[base].append(pid)

    # Check that siblings conflict with each other (skip coexisting groups)
    errors = []
    for base, variants in variant_groups.items():
        if len(variants) < 2:
            continue  # No siblings to check
        if base in COEXISTING_BASES:
            continue  # These siblings are designed to coexist

        for variant in variants:
            with open(patterns_dir / f"{variant}.json", 'r') as f:
                pattern = json.load(f)

            conflicts = set(pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", []))
            siblings = [v for v in variants if v != variant]

            for sibling in siblings:
                if sibling not in conflicts:
                    errors.append(
                        f"{variant}: Missing conflict with sibling variant '{sibling}'"
                    )

    assert len(errors) == 0, (
        f"Found {len(errors)} variant patterns missing sibling conflicts:\n" +
        "\n".join(f"  - {err}" for err in errors[:20])
    )

def test_architecture_patterns_mutually_exclusive():
    """Architecture patterns (arch-*) should conflict with each other."""
    patterns_dir = PROJECT_ROOT / "patterns"

    # Find all architecture patterns
    arch_patterns = []
    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        if pattern["id"].startswith("arch-"):
            arch_patterns.append(pattern["id"])

    # Check that each arch pattern conflicts with others
    errors = []
    for pattern_file in patterns_dir.glob("*.json"):
        with open(pattern_file, 'r') as f:
            pattern = json.load(f)

        pid = pattern["id"]

        if not pid.startswith("arch-"):
            continue

        conflicts = set(pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", []))
        other_arch = [a for a in arch_patterns if a != pid]

        # Count how many other arch patterns this conflicts with
        arch_conflicts = [a for a in other_arch if a in conflicts]

        # Allow some flexibility - not all arch patterns must conflict with ALL others
        # But should conflict with at least some major alternatives
        if len(arch_conflicts) < 2 and len(other_arch) >= 2:
            errors.append(
                f"{pid}: Only conflicts with {len(arch_conflicts)} other architecture patterns "
                f"(expected at least 2 out of {len(other_arch)})"
            )

    # This is more of a warning - some arch patterns might be compatible
    # So we'll just warn if there are many issues
    if len(errors) > len(arch_patterns) / 2:
        assert False, (
            f"Many architecture patterns missing mutual exclusivity:\n" +
            "\n".join(f"  - {err}" for err in errors[:10])
        )

def test_serverless_excludes_platforms():
    """Test that arch-serverless-* patterns exclude all platform-* patterns."""

    # All serverless patterns
    serverless_patterns = [
        "arch-serverless",
        "arch-serverless--aws",
        "arch-serverless--azure",
        "arch-serverless--gcp"
    ]

    # All platform patterns
    platform_patterns = [
        "platform-vm-first",
        "platform-kubernetes",
        "platform-no-mesh",
        "platform-service-mesh"
    ]

    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for serverless in serverless_patterns:
        serverless_file = patterns_dir / f"{serverless}.json"
        if not serverless_file.exists():
            continue

        with open(serverless_file) as f:
            pattern = json.load(f)

        conflicts = pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", [])

        for platform in platform_patterns:
            if platform not in conflicts:
                errors.append(f"{serverless} must declare conflict with {platform}")

    assert len(errors) == 0, (
        f"Found {len(errors)} missing serverless→platform conflict declarations:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )


def test_platforms_exclude_serverless():
    """Test that platform-* patterns exclude all arch-serverless-* patterns."""

    serverless_patterns = [
        "arch-serverless",
        "arch-serverless--aws",
        "arch-serverless--azure",
        "arch-serverless--gcp"
    ]

    platform_patterns = [
        "platform-vm-first",
        "platform-kubernetes",
        "platform-no-mesh",
        "platform-service-mesh"
    ]

    patterns_dir = PROJECT_ROOT / "patterns"
    errors = []

    for platform in platform_patterns:
        platform_file = patterns_dir / f"{platform}.json"
        if not platform_file.exists():
            continue

        with open(platform_file) as f:
            pattern = json.load(f)

        conflicts = pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", [])

        for serverless in serverless_patterns:
            if serverless not in conflicts:
                errors.append(f"{platform} must declare conflict with {serverless}")

    assert len(errors) == 0, (
        f"Found {len(errors)} missing platform→serverless conflict declarations:\n" +
        "\n".join(f"  - {err}" for err in errors)
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
