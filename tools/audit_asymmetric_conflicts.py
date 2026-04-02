#!/usr/bin/env python3
"""
Audit and report asymmetric conflict relationships in patterns.

Conflict relationships should be symmetric:
- If pattern A declares conflict with pattern B
- Then pattern B should declare conflict with pattern A

Common issue: Generic patterns missing conflicts with their variants
- Variants declare conflict with generic
- But generic doesn't declare conflict with variants
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Any

def load_all_patterns(patterns_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Load all patterns from directory."""
    patterns = {}
    for file in patterns_dir.glob("*.json"):
        with open(file, 'r', encoding='utf-8') as f:
            pattern = json.load(f)
            patterns[pattern["id"]] = pattern
    return patterns

def get_conflicts(pattern: Dict[str, Any]) -> Set[str]:
    """Extract conflict pattern IDs from a pattern."""
    conflicts_obj = pattern.get("conflicts", {})
    incompatible = conflicts_obj.get("incompatibleWithDesignPatterns", [])
    return set(incompatible)

def build_conflict_graph(patterns: Dict[str, Dict[str, Any]]) -> Dict[str, Set[str]]:
    """Build directed conflict graph (A -> [patterns A declares conflict with])."""
    graph = {}
    for pid, pattern in patterns.items():
        graph[pid] = get_conflicts(pattern)
    return graph

def find_asymmetric_conflicts(conflict_graph: Dict[str, Set[str]]) -> List[Dict[str, Any]]:
    """Find asymmetric conflict relationships."""
    asymmetric = []

    for pattern_a, conflicts_a in conflict_graph.items():
        for pattern_b in conflicts_a:
            # Check if pattern_b exists
            if pattern_b not in conflict_graph:
                asymmetric.append({
                    "type": "missing_pattern",
                    "pattern": pattern_a,
                    "declares_conflict_with": pattern_b,
                    "issue": f"Pattern {pattern_b} does not exist"
                })
                continue

            conflicts_b = conflict_graph[pattern_b]

            # Check if conflict is symmetric
            if pattern_a not in conflicts_b:
                asymmetric.append({
                    "type": "asymmetric_conflict",
                    "pattern_a": pattern_a,
                    "pattern_b": pattern_b,
                    "issue": f"{pattern_a} declares conflict with {pattern_b}, but {pattern_b} does NOT declare conflict with {pattern_a}"
                })

    return asymmetric

def categorize_asymmetric_conflicts(
    asymmetric: List[Dict[str, Any]],
    patterns: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize asymmetric conflicts by type."""
    categories = {
        "generic_missing_variant_conflicts": [],
        "variant_missing_generic_conflict": [],
        "variant_missing_sibling_conflict": [],
        "architecture_pattern_missing_conflict": [],
        "other_asymmetric": []
    }

    for asym in asymmetric:
        if asym["type"] == "missing_pattern":
            categories["other_asymmetric"].append(asym)
            continue

        pattern_a = asym["pattern_a"]
        pattern_b = asym["pattern_b"]

        # Detect generic vs variant patterns
        # Generic pattern format: "category-feature" (e.g., "db-timeseries--generic")
        # Variant pattern format: "category-feature--variant" (e.g., "db-timeseries--influxdb")

        # Check if pattern_b is generic and pattern_a is variant (or vice versa)
        if "--generic" in pattern_b and pattern_b.replace("--generic", "") in pattern_a:
            # pattern_a is a variant, pattern_b is its generic
            # This means generic is missing conflict with variant
            categories["generic_missing_variant_conflicts"].append({
                "generic_pattern": pattern_b,
                "variant_pattern": pattern_a,
                "issue": f"Generic pattern {pattern_b} missing conflict with variant {pattern_a}"
            })
        elif "--generic" in pattern_a and pattern_a.replace("--generic", "") in pattern_b:
            # pattern_b is a variant, pattern_a is its generic
            categories["variant_missing_generic_conflict"].append({
                "generic_pattern": pattern_a,
                "variant_pattern": pattern_b,
                "issue": f"Variant pattern {pattern_b} missing conflict with generic {pattern_a}"
            })
        elif pattern_a.startswith("arch-") or pattern_b.startswith("arch-"):
            categories["architecture_pattern_missing_conflict"].append(asym)
        else:
            # Check if they share a common prefix (sibling variants)
            prefix_a = pattern_a.rsplit("--", 1)[0] if "--" in pattern_a else pattern_a
            prefix_b = pattern_b.rsplit("--", 1)[0] if "--" in pattern_b else pattern_b

            if prefix_a == prefix_b and "--" in pattern_a and "--" in pattern_b:
                categories["variant_missing_sibling_conflict"].append({
                    "pattern_a": pattern_a,
                    "pattern_b": pattern_b,
                    "common_base": prefix_a,
                    "issue": f"Sibling variants missing symmetric conflict: {pattern_a} <-> {pattern_b}"
                })
            else:
                categories["other_asymmetric"].append(asym)

    return categories

def generate_fixes(categories: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[str]]:
    """Generate list of patterns needing conflict additions."""
    fixes = defaultdict(list)

    # Generic patterns missing variant conflicts
    for item in categories["generic_missing_variant_conflicts"]:
        generic = item["generic_pattern"]
        variant = item["variant_pattern"]
        fixes[generic].append(variant)

    # Variants missing generic conflict
    for item in categories["variant_missing_generic_conflict"]:
        generic = item["generic_pattern"]
        variant = item["variant_pattern"]
        fixes[variant].append(generic)

    # Sibling variants missing conflicts
    for item in categories["variant_missing_sibling_conflict"]:
        pattern_a = item["pattern_a"]
        pattern_b = item["pattern_b"]
        fixes[pattern_b].append(pattern_a)

    # Architecture patterns
    for item in categories["architecture_pattern_missing_conflict"]:
        if "pattern_a" in item and "pattern_b" in item:
            fixes[item["pattern_b"]].append(item["pattern_a"])

    return fixes

def main():
    patterns_dir = Path("patterns")
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    print("Loading patterns...")
    patterns = load_all_patterns(patterns_dir)
    print(f"Loaded {len(patterns)} patterns")

    print("\nBuilding conflict graph...")
    conflict_graph = build_conflict_graph(patterns)

    print("Finding asymmetric conflicts...")
    asymmetric = find_asymmetric_conflicts(conflict_graph)
    print(f"Found {len(asymmetric)} asymmetric conflict relationships")

    print("\nCategorizing asymmetric conflicts...")
    categories = categorize_asymmetric_conflicts(asymmetric, patterns)

    print("\n=== Asymmetric Conflict Summary ===")
    print(f"Generic patterns missing variant conflicts: {len(categories['generic_missing_variant_conflicts'])}")
    print(f"Variant patterns missing generic conflict: {len(categories['variant_missing_generic_conflict'])}")
    print(f"Sibling variants missing conflicts: {len(categories['variant_missing_sibling_conflict'])}")
    print(f"Architecture patterns missing conflicts: {len(categories['architecture_pattern_missing_conflict'])}")
    print(f"Other asymmetric conflicts: {len(categories['other_asymmetric'])}")

    # Generate fixes
    print("\nGenerating fixes...")
    fixes = generate_fixes(categories)
    print(f"Patterns needing fixes: {len(fixes)}")

    # Show specific examples
    print("\n=== Examples of Issues Found ===")

    if categories["generic_missing_variant_conflicts"]:
        print("\nGeneric patterns missing variant conflicts:")
        for item in categories["generic_missing_variant_conflicts"][:5]:
            print(f"  - {item['generic_pattern']} missing conflict with {item['variant_pattern']}")

    if categories["variant_missing_generic_conflict"]:
        print("\nVariant patterns missing generic conflict:")
        for item in categories["variant_missing_generic_conflict"][:5]:
            print(f"  - {item['variant_pattern']} missing conflict with {item['generic_pattern']}")

    if categories["variant_missing_sibling_conflict"]:
        print("\nSibling variants missing conflicts:")
        for item in categories["variant_missing_sibling_conflict"][:5]:
            print(f"  - {item['pattern_a']} <-> {item['pattern_b']}")

    # Save detailed report
    report = {
        "summary": {
            "total_patterns": len(patterns),
            "total_asymmetric_conflicts": len(asymmetric),
            "generic_missing_variant_conflicts": len(categories["generic_missing_variant_conflicts"]),
            "variant_missing_generic_conflict": len(categories["variant_missing_generic_conflict"]),
            "variant_missing_sibling_conflict": len(categories["variant_missing_sibling_conflict"]),
            "architecture_missing_conflict": len(categories["architecture_pattern_missing_conflict"]),
            "other_asymmetric": len(categories["other_asymmetric"]),
            "patterns_needing_fixes": len(fixes)
        },
        "categories": categories,
        "fixes": {pid: sorted(conflicts) for pid, conflicts in fixes.items()}
    }

    report_path = reports_dir / "asymmetric-conflicts-audit.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")

    # Save fixes in easy-to-apply format
    fixes_path = reports_dir / "asymmetric-conflicts-fixes.json"
    with open(fixes_path, 'w', encoding='utf-8') as f:
        json.dump(fixes, f, indent=2)

    print(f"Fixes saved to: {fixes_path}")

    return len(asymmetric) > 0

if __name__ == "__main__":
    import sys
    has_issues = main()
    sys.exit(1 if has_issues else 0)
