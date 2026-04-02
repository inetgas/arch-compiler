#!/usr/bin/env python3
"""
Audit all patterns for quality, consistency, and completeness.
Generates detailed reports identifying issues.
"""
import json
import pathlib
from collections import defaultdict
from typing import Dict, List, Any

try:
    import yaml as _yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

def audit_pattern_metadata(pattern: Dict[str, Any], pattern_id: str) -> List[str]:
    """Check if all required metadata fields are present and valid."""
    issues = []

    # Required top-level fields (Part 2A architecture)
    # Note: compatibility removed (replaced by supports_constraints)
    # Note: conflicts optional (not all patterns have conflicts)
    required_fields = ['id', 'version', 'title', 'description', 'types',
                       'cost', 'provides', 'requires', 'tags',
                       'supports_nfr', 'supports_constraints']

    for field in required_fields:
        if field not in pattern:
            issues.append(f"Missing required field: {field}")

    # Validate types array
    if 'types' in pattern:
        valid_types = ['cost', 'design', 'build', 'test', 'ops', 'deploy', 'security', 'data', 'platform', 'coding']
        for t in pattern.get('types', []):
            if t not in valid_types:
                issues.append(f"Invalid type '{t}' - valid: {valid_types}")

    # NEW: Check generic/variant_of consistency
    is_generic = pattern.get("generic", False)
    variant_of = pattern.get("variant_of")

    if is_generic and variant_of:
        issues.append(f"Pattern {pattern_id} has both generic=true and variant_of (should be one or the other)")

    if variant_of:
        # Check if parent pattern exists
        parent_path = pathlib.Path(__file__).parent.parent / "patterns" / f"{variant_of}.json"
        if not parent_path.exists():
            issues.append(f"Pattern {pattern_id} declares variant_of='{variant_of}' but parent pattern not found")

    # Check supports_constraints array format
    supports_constraints = pattern.get("supports_constraints", [])
    if isinstance(supports_constraints, list):
        for idx, rule in enumerate(supports_constraints):
            if not isinstance(rule, dict):
                issues.append(f"Pattern {pattern_id} supports_constraints[{idx}] is not an object")
                continue
            if "path" not in rule:
                issues.append(f"Pattern {pattern_id} supports_constraints[{idx}] missing 'path'")
            if "op" not in rule:
                issues.append(f"Pattern {pattern_id} supports_constraints[{idx}] missing 'op'")
            if "value" not in rule:
                issues.append(f"Pattern {pattern_id} supports_constraints[{idx}] missing 'value'")
            if "reason" not in rule:
                issues.append(f"Pattern {pattern_id} supports_constraints[{idx}] missing 'reason'")

    # Check supports_nfr array format
    supports_nfr = pattern.get("supports_nfr", [])
    if isinstance(supports_nfr, list):
        for idx, rule in enumerate(supports_nfr):
            if not isinstance(rule, dict):
                issues.append(f"Pattern {pattern_id} supports_nfr[{idx}] is not an object")
                continue
            if "path" not in rule:
                issues.append(f"Pattern {pattern_id} supports_nfr[{idx}] missing 'path'")
            if "op" not in rule:
                issues.append(f"Pattern {pattern_id} supports_nfr[{idx}] missing 'op'")
            if "value" not in rule:
                issues.append(f"Pattern {pattern_id} supports_nfr[{idx}] missing 'value'")
            if "reason" not in rule:
                issues.append(f"Pattern {pattern_id} supports_nfr[{idx}] missing 'reason'")

    return issues

def audit_compatibility(pattern: Dict[str, Any]) -> List[str]:
    """Check compatibility fields for logical consistency. (OBSOLETE - compatibility removed)"""
    # compatibility field has been removed from all patterns and schema (Part 2A)
    # Replaced by supports_constraints field
    # This function kept for backwards compatibility but returns empty list
    return []

def audit_excluded_if_rules(pattern: Dict[str, Any]) -> List[str]:
    """Check excludedIf rules for logical soundness. (OBSOLETE - excludedIf removed)"""
    # excludedIf has been removed from all patterns and schema
    # This function kept for backwards compatibility but returns empty list
    return []

def _load_alias_map() -> Dict[str, str]:
    """Load alias → canonical mapping from schemas/capability-vocabulary.yaml.
    Returns empty dict if the file is missing or PyYAML is not installed."""
    if not _YAML_AVAILABLE:
        return {}
    vocab_path = pathlib.Path(__file__).parent.parent / "schemas" / "capability-vocabulary.yaml"
    if not vocab_path.exists():
        return {}
    with open(vocab_path) as f:
        vocab = _yaml.safe_load(f)
    alias_map: Dict[str, str] = {}
    for canonical, entry in (vocab.get("capabilities") or {}).items():
        for alias in (entry.get("aliases") or []):
            alias_map[alias] = canonical
    return alias_map


def audit_capability_vocabulary(pattern: Dict[str, Any], alias_map: Dict[str, str]) -> List[str]:
    """Check that no requires/provides capability uses a known alias instead of canonical name."""
    if not alias_map:
        return []
    issues = []
    for item in pattern.get("provides", []):
        cap = item.get("capability", "")
        if cap in alias_map:
            issues.append(
                f"provides '{cap}' is a known alias — use canonical name '{alias_map[cap]}'"
            )
    for item in pattern.get("requires", []):
        cap = item.get("capability", "")
        if cap in alias_map:
            issues.append(
                f"requires '{cap}' is a known alias — use canonical name '{alias_map[cap]}'"
            )
    return issues


def audit_incompatible_patterns(pattern: Dict[str, Any], all_pattern_ids: set) -> List[str]:
    """Check incompatibleWithDesignPatterns for symmetry and existence."""
    issues = []
    pattern_id = pattern.get('id')
    incompatible = pattern.get('conflicts', {}).get('incompatibleWithDesignPatterns', [])

    for other_id in incompatible:
        if other_id not in all_pattern_ids:
            issues.append(f"References non-existent pattern: {other_id}")

    return issues

def main():
    base = pathlib.Path(__file__).parent.parent / "patterns"
    patterns = {}

    # Load all patterns
    for f in base.glob("*.json"):
        try:
            with open(f) as fp:
                pattern = json.load(fp)
                patterns[pattern['id']] = pattern
        except Exception as e:
            print(f"ERROR loading {f.name}: {e}")

    all_pattern_ids = set(patterns.keys())
    alias_map = _load_alias_map()

    print(f"=== Pattern Quality Audit ===")
    print(f"Total patterns: {len(patterns)}")
    if alias_map:
        print(f"Vocabulary loaded: {len(alias_map)} known aliases\n")
    else:
        print("Vocabulary: not loaded (install PyYAML or check schemas/capability-vocabulary.yaml)\n")

    # Collect issues by category
    issues_by_category = defaultdict(list)
    issues_by_pattern = defaultdict(list)

    for pattern_id, pattern in patterns.items():
        # Run audits
        metadata_issues = audit_pattern_metadata(pattern, pattern_id)
        compat_issues = audit_compatibility(pattern)
        excluded_issues = audit_excluded_if_rules(pattern)
        incompatible_issues = audit_incompatible_patterns(pattern, all_pattern_ids)
        vocab_issues = audit_capability_vocabulary(pattern, alias_map)

        all_issues = (metadata_issues + compat_issues +
                     excluded_issues + incompatible_issues + vocab_issues)

        if all_issues:
            issues_by_pattern[pattern_id] = all_issues
            for issue in all_issues:
                issues_by_category[issue.split(':')[0]].append((pattern_id, issue))

    # Print summary by category
    print("=== Issues by Category ===\n")
    for category, issues in sorted(issues_by_category.items()):
        print(f"{category} ({len(issues)} issues):")
        for pid, issue in issues[:5]:  # Show first 5
            print(f"  {pid}: {issue}")
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more")
        print()

    # Print patterns with most issues
    print("=== Patterns with Most Issues ===\n")
    sorted_patterns = sorted(issues_by_pattern.items(),
                            key=lambda x: len(x[1]), reverse=True)
    for pattern_id, issues in sorted_patterns[:10]:
        print(f"{pattern_id} ({len(issues)} issues):")
        for issue in issues:
            print(f"  - {issue}")
        print()

    # Summary stats
    print(f"=== Summary ===")
    print(f"Patterns with issues: {len(issues_by_pattern)}")
    print(f"Clean patterns: {len(patterns) - len(issues_by_pattern)}")
    print(f"Total issues found: {sum(len(v) for v in issues_by_pattern.values())}")

if __name__ == "__main__":
    main()
