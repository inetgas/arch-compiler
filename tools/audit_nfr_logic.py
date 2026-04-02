#!/usr/bin/env python3
"""
Audit NFR and constraint logic for correctness.

Issues to detect:
1. NFR: Invalid paths not in canonical-schema.yaml
2. Constraints: Multiple entries for same path (need consolidation)
3. Constraints: Invalid "supports" operator
4. Constraints: Missing "mobile" platform support

Note: Both lower (>=) and upper (<=) bounds on the same NFR/constraint path
are explicitly allowed — a range defines the operating envelope of a pattern
(e.g., peak_jobs_per_hour >= 60 AND <= 360M is a valid operating window).
"""
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict


def load_canonical_schema():
    """Load canonical schema to validate paths."""
    schema_path = Path("schemas/canonical-schema.yaml")
    schema = yaml.safe_load(schema_path.read_text())

    # Extract all valid paths
    valid_paths = set()

    # Add constraint paths
    constraints_props = schema["properties"]["constraints"]["properties"]
    for key in constraints_props.keys():
        valid_paths.add(f"/constraints/{key}")
        if key == "features":
            features = constraints_props["features"]["properties"]
            for feat in features.keys():
                valid_paths.add(f"/constraints/features/{feat}")

    # Add NFR paths
    nfr_props = schema["properties"]["nfr"]["properties"]
    for key in nfr_props.keys():
        if key in ["latency", "data", "consistency", "durability", "security"]:
            # Nested objects
            if "properties" in nfr_props[key]:
                for subkey in nfr_props[key]["properties"].keys():
                    valid_paths.add(f"/nfr/{key}/{subkey}")
                    # Handle data.compliance
                    if key == "data" and subkey == "compliance":
                        compliance_props = nfr_props[key]["properties"]["compliance"]["properties"]
                        for comp_key in compliance_props.keys():
                            valid_paths.add(f"/nfr/data/compliance/{comp_key}")
        elif key == "availability":
            valid_paths.add(f"/nfr/availability/target")
        elif key == "throughput":
            throughput_props = nfr_props[key].get("properties", {})
            for tp_key in throughput_props.keys():
                valid_paths.add(f"/nfr/throughput/{tp_key}")
        else:
            # Simple fields
            valid_paths.add(f"/nfr/{key}")

    # Add operating_model paths
    op_model_props = schema["properties"]["operating_model"]["properties"]
    for key in op_model_props.keys():
        valid_paths.add(f"/operating_model/{key}")

    return valid_paths


def analyze_nfr_rules(pattern: Dict[str, Any], valid_paths: set) -> Dict[str, List[str]]:
    """Analyze NFR rules for logic errors."""
    issues = defaultdict(list)
    pattern_id = pattern.get("id", "unknown")

    supports_nfr = pattern.get("supports_nfr", [])

    # Group rules by path
    rules_by_path = defaultdict(list)
    for rule in supports_nfr:
        path = rule.get("path", "")
        rules_by_path[path].append(rule)

    # Check each path
    for path, rules in rules_by_path.items():
        # Check if path is valid
        if path not in valid_paths:
            issues["invalid_path"].append({
                "pattern": pattern_id,
                "path": path,
                "reason": f"Path '{path}' not in canonical-schema.yaml"
            })

    return issues


def analyze_constraint_rules(pattern: Dict[str, Any]) -> Dict[str, List[str]]:
    """Analyze constraint rules for logic errors."""
    issues = defaultdict(list)
    pattern_id = pattern.get("id", "unknown")

    supports_constraints = pattern.get("supports_constraints", [])

    # Group rules by path
    rules_by_path = defaultdict(list)
    for rule in supports_constraints:
        path = rule.get("path", "")
        rules_by_path[path].append(rule)

    # Check each path
    for path, rules in rules_by_path.items():
        # Multiple entries for same path
        if len(rules) > 1:
            # Check if they can be consolidated
            ops = [r["op"] for r in rules]
            if "in" in ops and "!=" in ops:
                issues["multiple_platform_entries"].append({
                    "pattern": pattern_id,
                    "path": path,
                    "rules": rules,
                    "fix": "Consolidate into single 'in' rule"
                })
            elif len(set(ops)) > 1:
                issues["mixed_operators"].append({
                    "pattern": pattern_id,
                    "path": path,
                    "rules": rules,
                    "fix": "Multiple operators for same path - review logic"
                })

        # Invalid "supports" operator
        for rule in rules:
            if rule.get("op") == "supports":
                issues["invalid_supports_operator"].append({
                    "pattern": pattern_id,
                    "path": path,
                    "rule": rule,
                    "fix": "Replace 'supports' with 'in' [true, false] or '==' true"
                })

        # Check platform rules for missing "mobile"
        if path == "/constraints/platform":
            for rule in rules:
                if rule.get("op") == "in":
                    values = rule.get("value", [])
                    if isinstance(values, list) and "mobile" not in values and "agnostic" not in values:
                        # Check if this is a serverless/backend pattern
                        if "serverless" in pattern_id or "api" in pattern_id or "worker" in pattern_id:
                            issues["missing_mobile_platform"].append({
                                "pattern": pattern_id,
                                "path": path,
                                "current_values": values,
                                "fix": "Add 'mobile' to platform support (mobile apps with backend)"
                            })

    return issues


def audit_all_patterns():
    """Audit all patterns for NFR and constraint logic issues."""
    patterns_dir = Path("patterns")

    # Load valid paths
    print("Loading canonical schema...")
    valid_paths = load_canonical_schema()
    print(f"Found {len(valid_paths)} valid paths\n")

    all_issues = defaultdict(list)

    for pattern_file in sorted(patterns_dir.glob("*.json")):
        with open(pattern_file) as f:
            pattern = json.load(f)

        # Analyze NFR rules
        nfr_issues = analyze_nfr_rules(pattern, valid_paths)
        for issue_type, items in nfr_issues.items():
            all_issues[issue_type].extend(items)

        # Analyze constraint rules
        constraint_issues = analyze_constraint_rules(pattern)
        for issue_type, items in constraint_issues.items():
            all_issues[issue_type].extend(items)

    # Print summary
    print("=== NFR Logic Issues ===\n")

    if all_issues["invalid_path"]:
        print(f"❌ Invalid paths: {len(all_issues['invalid_path'])} rules")
        for issue in all_issues["invalid_path"][:5]:
            print(f"   {issue['pattern']}: {issue['path']}")
        if len(all_issues["invalid_path"]) > 5:
            print(f"   ... and {len(all_issues['invalid_path']) - 5} more")
        print()

    print("=== Constraint Logic Issues ===\n")

    if all_issues["multiple_platform_entries"]:
        print(f"❌ Multiple platform entries: {len(all_issues['multiple_platform_entries'])} patterns")
        for issue in all_issues["multiple_platform_entries"][:3]:
            print(f"   {issue['pattern']}: {len(issue['rules'])} rules")
        if len(all_issues["multiple_platform_entries"]) > 3:
            print(f"   ... and {len(all_issues['multiple_platform_entries']) - 3} more")
        print()

    if all_issues["invalid_supports_operator"]:
        print(f"❌ Invalid 'supports' operator: {len(all_issues['invalid_supports_operator'])} rules")
        for issue in all_issues["invalid_supports_operator"][:5]:
            print(f"   {issue['pattern']}: {issue['path']}")
        if len(all_issues["invalid_supports_operator"]) > 5:
            print(f"   ... and {len(all_issues['invalid_supports_operator']) - 5} more")
        print()

    if all_issues["missing_mobile_platform"]:
        print(f"⚠️  Missing mobile platform: {len(all_issues['missing_mobile_platform'])} patterns")
        for issue in all_issues["missing_mobile_platform"][:3]:
            print(f"   {issue['pattern']}")
        if len(all_issues["missing_mobile_platform"]) > 3:
            print(f"   ... and {len(all_issues['missing_mobile_platform']) - 3} more")
        print()

    # Summary
    total_issues = sum(len(items) for items in all_issues.values())
    print(f"=== Summary ===")
    print(f"Total issue types: {len(all_issues)}")
    print(f"Total issues found: {total_issues}")

    # Save detailed report
    report_path = Path("reports/nfr-constraint-logic-audit.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(dict(all_issues), f, indent=2)
        f.write("\n")

    print(f"\nDetailed report: {report_path}")

    return all_issues


if __name__ == "__main__":
    audit_all_patterns()
