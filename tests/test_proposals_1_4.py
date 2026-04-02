#!/usr/bin/env python3
"""Unit tests for Proposals 1-4.

Proposal 1: Sort selected patterns by match_score (descending)
Proposal 2: Minimize selected-patterns.yaml fields (non-verbose: only id/title)
Proposal 3: Sort rejected patterns by partial_match_score (descending)
Proposal 4: Add honored_rules to selected patterns

These tests verify the implementation of all 4 proposals.
"""
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import (
    _calculate_pattern_match_score,
    _calculate_partial_match_score,
    _sort_rejected_patterns_by_relevance,
    _filter_by_supports_constraints,
    _filter_by_supports_nfr,
    _resolve_conflicts_with_match_scoring,
    _generate_output_files,
    _print_cost_details,
    _check_cost_feasibility,
    _calculate_ops_team_cost
)


def test_selected_patterns_sorted_by_match_score():
    """
    Proposal 1: Verify patterns are sorted descending by match score.
    Highest relevance patterns appear first.
    """
    # Create patterns with different numbers of rules
    patterns = {
        "low-match": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS only"}
            ],
            "supports_nfr": []
        },
        "high-match": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS only"},
                {"path": "/constraints/language", "op": "==", "value": "python", "reason": "Python only"}
            ],
            "supports_nfr": [
                {"path": "/nfr/availability/target", "op": "<=", "value": 0.99, "reason": "Standard availability"}
            ]
        },
        "medium-match": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS only"}
            ],
            "supports_nfr": [
                {"path": "/nfr/availability/target", "op": "<=", "value": 0.99, "reason": "Standard availability"}
            ]
        }
    }

    spec = {
        "constraints": {"cloud": "aws", "language": "python"},
        "nfr": {"availability": {"target": 0.99}}
    }

    # Calculate match scores
    match_scores = {
        pid: _calculate_pattern_match_score(patterns[pid], spec)
        for pid in patterns.keys()
    }

    # Verify scores are as expected
    assert match_scores["low-match"] == 1  # 1 constraint rule matched
    assert match_scores["medium-match"] == 2  # 1 constraint + 1 NFR
    assert match_scores["high-match"] == 3  # 2 constraints + 1 NFR

    # Sort patterns by match score (descending)
    sorted_patterns = sorted(patterns.keys(), key=lambda pid: match_scores[pid], reverse=True)

    # Verify order: high > medium > low
    assert sorted_patterns == ["high-match", "medium-match", "low-match"]

    print("✅ test_selected_patterns_sorted_by_match_score passed")


def test_selected_patterns_minimal_fields():
    """
    Proposal 2: Non-verbose mode shows only id and title.
    Verify tier and monthly_cost_min are removed.
    Verify match_score is NOT shown.
    """
    patterns = {
        "test-pattern": {
            "title": "Test Pattern",
            "description": "A test pattern",
            "availability": {"tier": "open"},
            "cost": {
                "estimatedMonthlyRangeUsd": {"min": 100, "max": 200}
            },
            "provides": [{"capability": "test-cap"}],
            "conflicts": {"incompatibleWithDesignPatterns": []},
            "supports_constraints": [],
            "supports_nfr": []
        }
    }

    spec = {"constraints": {}, "nfr": {}}
    match_scores = {"test-pattern": 0}
    honored_rules = {"test-pattern": {"constraints": [], "nfr": []}}

    # Generate output files in non-verbose mode
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        written_files = _generate_output_files(
            spec=spec,
            selected_patterns=["test-pattern"],
            rejected_patterns=[],
            warnings=[],
            patterns=patterns,
            output_dir=tmpdir,
            verbose=False,  # Non-verbose mode
            timestamp=False,
            match_scores=match_scores,
            honored_rules=honored_rules
        )

        # Read selected-patterns.yaml
        selected_file = Path(tmpdir) / "selected-patterns.yaml"
        with open(selected_file, "r") as f:
            selected_data = yaml.safe_load(f)

        # Verify structure
        assert len(selected_data) == 1
        entry = selected_data[0]

        # Non-verbose: only id, title, and honored_rules
        assert "id" in entry
        assert "title" in entry
        assert "honored_rules" in entry

        # These should NOT be present in non-verbose mode
        assert "description" not in entry
        assert "capabilities" not in entry
        assert "cost (for reference only)" not in entry
        assert "conflicts" not in entry
        assert "tier" not in entry
        assert "match_score" not in entry

        # Verify values
        assert entry["id"] == "test-pattern"
        assert entry["title"] == "Test Pattern"

    print("✅ test_selected_patterns_minimal_fields passed")


def test_rejected_patterns_sorted_by_partial_match():
    """
    Proposal 3: Verify rejected patterns sorted by relevance.
    Patterns that "almost made it" appear first.
    """
    patterns = {
        "almost-made-it": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS only"},
                {"path": "/constraints/language", "op": "==", "value": "python", "reason": "Python only"},
                {"path": "/constraints/platform", "op": "==", "value": "mobile", "reason": "Mobile only"}  # This fails
            ],
            "supports_nfr": []
        },
        "not-close": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "gcp", "reason": "GCP only"},  # Fails
                {"path": "/constraints/language", "op": "==", "value": "java", "reason": "Java only"}  # Fails
            ],
            "supports_nfr": []
        },
        "somewhat-close": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS only"},
                {"path": "/constraints/language", "op": "==", "value": "java", "reason": "Java only"}  # Fails
            ],
            "supports_nfr": []
        }
    }

    spec = {
        "constraints": {"cloud": "aws", "language": "python", "platform": "api"}
    }

    # Create rejected pattern entries
    rejected_patterns = [
        {
            "id": "almost-made-it",
            "reason": "Failed 1 constraint rule(s)",
            "failed_rules": [
                {"path": "/constraints/platform", "op": "==", "value": "mobile", "reason": "Mobile only"}
            ]
        },
        {
            "id": "not-close",
            "reason": "Failed 2 constraint rule(s)",
            "failed_rules": [
                {"path": "/constraints/cloud", "op": "==", "value": "gcp", "reason": "GCP only"},
                {"path": "/constraints/language", "op": "==", "value": "java", "reason": "Java only"}
            ]
        },
        {
            "id": "somewhat-close",
            "reason": "Failed 1 constraint rule(s)",
            "failed_rules": [
                {"path": "/constraints/language", "op": "==", "value": "java", "reason": "Java only"}
            ]
        }
    ]

    # Sort by partial match score
    sorted_rejected = _sort_rejected_patterns_by_relevance(rejected_patterns, patterns, spec)

    # Verify partial match scores
    # almost-made-it: 3 total rules - 1 failed = 2 matched
    # somewhat-close: 2 total rules - 1 failed = 1 matched
    # not-close: 2 total rules - 2 failed = 0 matched
    assert sorted_rejected[0]["id"] == "almost-made-it"
    assert sorted_rejected[0]["partial_match_score"] == 2
    assert sorted_rejected[1]["id"] == "somewhat-close"
    assert sorted_rejected[1]["partial_match_score"] == 1
    assert sorted_rejected[2]["id"] == "not-close"
    assert sorted_rejected[2]["partial_match_score"] == 0

    print("✅ test_rejected_patterns_sorted_by_partial_match passed")


def test_honored_rules_format():
    """
    Proposal 4: Verify honored_rules structure matches failed_rules format.
    Check constraints and nfr sections.
    Each rule has path, op, value, reason.
    """
    patterns = {
        "test-pattern": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS compatible"}
            ],
            "supports_nfr": [
                {"path": "/nfr/availability/target", "op": "<=", "value": 0.99, "reason": "Standard availability"}
            ]
        }
    }

    spec = {
        "constraints": {"cloud": "aws"},
        "nfr": {"availability": {"target": 0.99}}
    }

    # Phase 3.1: Filter by constraints
    selected, rejected, honored_rules = _filter_by_supports_constraints(patterns, spec)

    # Phase 3.2: Filter by NFR
    selected, rejected_nfr, honored_rules = _filter_by_supports_nfr(selected, patterns, spec, honored_rules)

    # Verify honored_rules structure
    assert "test-pattern" in honored_rules
    rules = honored_rules["test-pattern"]

    # Check top-level structure
    assert "constraints" in rules
    assert "nfr" in rules
    assert isinstance(rules["constraints"], list)
    assert isinstance(rules["nfr"], list)

    # Check constraint rules
    assert len(rules["constraints"]) == 1
    constraint_rule = rules["constraints"][0]
    assert "path" in constraint_rule
    assert "op" in constraint_rule
    assert "value" in constraint_rule
    assert "reason" in constraint_rule
    assert constraint_rule["path"] == "/constraints/cloud"
    assert constraint_rule["op"] == "=="
    assert constraint_rule["value"] == "aws"

    # Check NFR rules
    assert len(rules["nfr"]) == 1
    nfr_rule = rules["nfr"][0]
    assert "path" in nfr_rule
    assert "op" in nfr_rule
    assert "value" in nfr_rule
    assert "reason" in nfr_rule
    assert nfr_rule["path"] == "/nfr/availability/target"
    assert nfr_rule["op"] == "<="
    assert nfr_rule["value"] == 0.99

    print("✅ test_honored_rules_format passed")


def test_honored_rules_accuracy():
    """
    Proposal 4: Verify honored_rules actually match spec values.
    Rules make sense for selected patterns.
    """
    patterns = {
        "aws-pattern": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "in", "value": ["aws", "gcp"], "reason": "Multi-cloud"},
                {"path": "/constraints/language", "op": "==", "value": "python", "reason": "Python only"}
            ],
            "supports_nfr": []
        },
        "gcp-pattern": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "gcp", "reason": "GCP only"}
            ],
            "supports_nfr": []
        }
    }

    spec = {
        "constraints": {"cloud": "aws", "language": "python"}
    }

    # Filter patterns
    selected, rejected, honored_rules = _filter_by_supports_constraints(patterns, spec)

    # aws-pattern should be selected (matches cloud and language)
    assert "aws-pattern" in selected
    assert "aws-pattern" in honored_rules
    aws_rules = honored_rules["aws-pattern"]["constraints"]
    assert len(aws_rules) == 2  # Both rules matched

    # Verify the rules actually match the spec
    cloud_rule = [r for r in aws_rules if r["path"] == "/constraints/cloud"][0]
    assert spec["constraints"]["cloud"] in cloud_rule["value"]

    language_rule = [r for r in aws_rules if r["path"] == "/constraints/language"][0]
    assert spec["constraints"]["language"] == language_rule["value"]

    # gcp-pattern should be rejected (cloud doesn't match)
    assert "gcp-pattern" not in selected
    assert "gcp-pattern" not in honored_rules

    print("✅ test_honored_rules_accuracy passed")


def test_cli_outputs_compiled_spec_content():
    """
    Verify compiled-spec.yaml content is shown in CLI output.
    Not just "Wrote..." message.

    Note: This test verifies the file generation, actual CLI output
    is tested via integration tests.
    """
    spec = {
        "constraints": {"cloud": "aws"},
        "assumptions": {}
    }
    patterns = {}

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        written_files = _generate_output_files(
            spec=spec,
            selected_patterns=[],
            rejected_patterns=[],
            warnings=[],
            patterns=patterns,
            output_dir=tmpdir,
            verbose=False,
            timestamp=False,
            match_scores={},
            honored_rules={}
        )

        # Verify compiled-spec.yaml exists
        compiled_file = Path(tmpdir) / "compiled-spec.yaml"
        assert compiled_file.exists()

        # Read and verify content
        with open(compiled_file, "r") as f:
            content = f.read()

        # Should contain the spec data
        assert "cloud: aws" in content

        # Verify annotation
        assert any("(above output)" in annotation for _, annotation in written_files if "compiled-spec" in _)

    print("✅ test_cli_outputs_compiled_spec_content passed")


def test_cli_files_at_end_with_utc():
    """
    Verify file list at end has UTC timestamp in ISO 8601 format.
    File annotations present.

    Note: This test verifies the function behavior, actual CLI output
    tested via integration tests.
    """
    spec = {"constraints": {}, "assumptions": {}}
    patterns = {}

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        written_files = _generate_output_files(
            spec=spec,
            selected_patterns=[],
            rejected_patterns=[],
            warnings=[],
            patterns=patterns,
            output_dir=tmpdir,
            verbose=False,
            timestamp=True,  # Enable timestamp
            match_scores={},
            honored_rules={}
        )

        # Verify files have timestamps in names
        for file_path, annotation in written_files:
            assert Path(file_path).exists()
            # Files with timestamp should match pattern: *-YYYY-MM-DDTHH:MM:SSZ.yaml
            if "compiled-spec" in file_path:
                # Should have timestamp in filename
                import re
                assert re.search(r'-\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', file_path)

        # Verify annotations exist
        annotations = [ann for _, ann in written_files]
        assert "(above output)" in annotations
        assert "(further details of selected patterns)" in annotations

    print("✅ test_cli_files_at_end_with_utc passed")


def test_verbose_comprehensive_info():
    """
    Verify all 7 fields in verbose mode.
    Correct field order.
    Cost label "cost (for reference only):".

    Expected order in verbose mode:
    1. id
    2. title
    3. description
    4. honored_rules
    5. capabilities
    6. cost (for reference only)
    7. conflicts
    """
    patterns = {
        "test-pattern": {
            "title": "Test Pattern",
            "description": "A comprehensive test pattern",
            "availability": {"tier": "open"},
            "cost": {
                "adoptionCost": 500,
                "licenseCost": 0,
                "estimatedMonthlyRangeUsd": {"min": 50, "max": 100}
            },
            "provides": [
                {"capability": "test-cap-1", "reasoning": "Provides test capability 1"},
                {"capability": "test-cap-2", "reasoning": "Provides test capability 2"}
            ],
            "conflicts": {
                "incompatibleWithDesignPatterns": ["other-pattern"]
            },
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS only"}
            ],
            "supports_nfr": []
        }
    }

    spec = {"constraints": {"cloud": "aws"}, "nfr": {}, "assumptions": {}}
    match_scores = {"test-pattern": 1}
    honored_rules = {
        "test-pattern": {
            "constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS only"}
            ],
            "nfr": []
        }
    }

    # Generate output files in verbose mode
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        written_files = _generate_output_files(
            spec=spec,
            selected_patterns=["test-pattern"],
            rejected_patterns=[],
            warnings=[],
            patterns=patterns,
            output_dir=tmpdir,
            verbose=True,  # Verbose mode
            timestamp=False,
            match_scores=match_scores,
            honored_rules=honored_rules
        )

        # Read selected-patterns.yaml
        selected_file = Path(tmpdir) / "selected-patterns.yaml"
        with open(selected_file, "r") as f:
            content = f.read()
            f.seek(0)
            selected_data = yaml.safe_load(f)

        # Verify structure
        assert len(selected_data) == 1
        entry = selected_data[0]

        # Verbose mode: all 7 fields
        assert "id" in entry
        assert "title" in entry
        assert "description" in entry
        assert "honored_rules" in entry
        assert "provides" in entry
        assert "cost (for reference only)" in entry  # Exact label
        assert "conflicts" in entry

        # Verify field order by checking YAML content
        lines = content.split('\n')
        field_positions = {}
        for i, line in enumerate(lines):
            if line.startswith('- id:'):
                field_positions['id'] = i
            elif line.startswith('  title:'):
                field_positions['title'] = i
            elif line.startswith('  description:'):
                field_positions['description'] = i
            elif line.startswith('  honored_rules:'):
                field_positions['honored_rules'] = i
            elif line.startswith('  provides:'):
                field_positions['provides'] = i
            elif line.startswith('  cost (for reference only):'):
                field_positions['cost'] = i
            elif line.startswith('  conflicts:'):
                field_positions['conflicts'] = i

        # Verify order: id < title < description < honored_rules < provides < cost < conflicts
        assert field_positions['id'] < field_positions['title']
        assert field_positions['title'] < field_positions['description']
        assert field_positions['description'] < field_positions['honored_rules']
        assert field_positions['honored_rules'] < field_positions['provides']
        assert field_positions['provides'] < field_positions['cost']
        assert field_positions['cost'] < field_positions['conflicts']

        # Verify cost structure
        cost_data = entry["cost (for reference only)"]
        assert "adoption_usd" in cost_data
        assert "monthly_min_usd" in cost_data
        assert "monthly_max_usd" in cost_data
        assert "monthly_expected_usd" in cost_data
        assert "license_cost" in cost_data

    print("✅ test_verbose_comprehensive_info passed")


def test_verbose_cost_logging_always():
    """
    Verify cost calculations shown in verbose mode.
    Shown regardless of warnings.
    Shown BEFORE warnings section.
    """
    patterns = {
        "test-pattern": {
            "cost": {
                "adoptionCost": 1000,
                "licenseCost": 0,
                "estimatedMonthlyRangeUsd": {"min": 100, "max": 200}
            },
            "hosting": {
                "self_hosted": False,
                "managed_service": True
            }
        }
    }

    spec = {
        "cost": {
            "intent": {"priority": "optimize-tco"},
            "ceilings": {
                "monthly_operational_usd": 50,  # Will trigger warning
                "one_time_setup_usd": 500  # Will trigger warning
            }
        },
        "operating_model": {
            "amortization_months": 24,
            "ops_team_size": 0,
            "single_resource_monthly_ops_usd": 10000,
            "on_call": False,
            "deploy_freq": "weekly"
        },
        "nfr": {}
    }

    # Calculate ops team cost
    ops_team_cost = _calculate_ops_team_cost(spec["operating_model"])

    # Check cost feasibility (should return warnings and cost_details)
    warnings, cost_details = _check_cost_feasibility(
        selected_pattern_ids=["test-pattern"],
        patterns=patterns,
        spec=spec,
        ops_team_cost=ops_team_cost,
        match_scores={"test-pattern": 10.0},
        verbose=True  # Verbose mode
    )

    # Verify cost_details is returned in verbose mode
    assert cost_details is not None
    assert "intent" in cost_details
    assert "amortization_months" in cost_details
    assert "ops_team_size" in cost_details
    assert "pattern_costs" in cost_details
    assert "total_tco" in cost_details

    # Verify pattern costs
    assert len(cost_details["pattern_costs"]) == 1
    pattern_cost = cost_details["pattern_costs"][0]
    assert pattern_cost["id"] == "test-pattern"
    assert pattern_cost["adoption_cost"] == 1000
    assert pattern_cost["monthly_min"] == 100
    # monthly_expected defaults to monthly_min when 'expected' field not present
    assert pattern_cost["monthly_expected"] == 100

    # Verify warnings exist (cost exceeds ceiling)
    assert len(warnings) > 0
    assert any("tco_exceeds_ceiling" in w.get("code", "") for w in warnings)

    # Note: The actual printing order (cost details BEFORE warnings)
    # is enforced in main() function, which is tested via integration tests

    print("✅ test_verbose_cost_logging_always passed")


def test_match_score_calculation_edge_cases():
    """
    Additional test: Verify match score calculation handles edge cases.
    - Empty rules
    - Partial matches
    - All rules matched
    """
    # Pattern with no rules
    pattern_empty = {
        "supports_constraints": [],
        "supports_nfr": []
    }
    spec = {"constraints": {"cloud": "aws"}}
    assert _calculate_pattern_match_score(pattern_empty, spec) == 0

    # Pattern with rules that don't match spec
    pattern_no_match = {
        "supports_constraints": [
            {"path": "/constraints/cloud", "op": "==", "value": "gcp", "reason": "GCP only"}
        ],
        "supports_nfr": []
    }
    assert _calculate_pattern_match_score(pattern_no_match, spec) == 0

    # Pattern with mixed matches
    # Note: When a spec field is unspecified (None), rule evaluation returns True
    # This is by design - unspecified constraints don't reject patterns
    spec_detailed = {"constraints": {"cloud": "aws", "language": "java"}}
    pattern_mixed = {
        "supports_constraints": [
            {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS match"},  # Matches
            {"path": "/constraints/language", "op": "==", "value": "python", "reason": "Python only"}  # No match
        ],
        "supports_nfr": []
    }
    assert _calculate_pattern_match_score(pattern_mixed, spec_detailed) == 1

    print("✅ test_match_score_calculation_edge_cases passed")


def test_partial_match_score_edge_cases():
    """
    Additional test: Verify partial match score calculation handles edge cases.
    - All rules failed
    - No rules failed
    - Missing pattern in registry
    """
    patterns = {
        "all-failed": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "gcp", "reason": "GCP"},
                {"path": "/constraints/language", "op": "==", "value": "java", "reason": "Java"}
            ],
            "supports_nfr": []
        },
        "none-failed": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS"}
            ],
            "supports_nfr": []
        }
    }

    spec = {"constraints": {"cloud": "aws", "language": "python"}}

    # All rules failed: partial_match_score = 0
    rejected_all_failed = {
        "id": "all-failed",
        "failed_rules": [
            {"path": "/constraints/cloud", "op": "==", "value": "gcp", "reason": "GCP"},
            {"path": "/constraints/language", "op": "==", "value": "java", "reason": "Java"}
        ]
    }
    assert _calculate_partial_match_score(rejected_all_failed, patterns, spec) == 0

    # This scenario wouldn't normally occur (no failed rules means pattern selected),
    # but test the logic anyway
    rejected_none_failed = {
        "id": "none-failed",
        "failed_rules": []
    }
    assert _calculate_partial_match_score(rejected_none_failed, patterns, spec) == 1

    print("✅ test_partial_match_score_edge_cases passed")


def test_honored_rules_persists_through_phases():
    """
    Additional test: Verify honored_rules persists correctly through Phase 3.1-3.3.
    Phase 3.1 adds constraints, Phase 3.2 adds NFR, Phase 3.3 preserves both.
    """
    patterns = {
        "multi-rule-pattern": {
            "supports_constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws", "reason": "AWS compatible"}
            ],
            "supports_nfr": [
                {"path": "/nfr/availability/target", "op": "<=", "value": 0.99, "reason": "Standard availability"}
            ],
            "conflicts": {"incompatibleWithDesignPatterns": []}
        }
    }

    spec = {
        "constraints": {"cloud": "aws"},
        "nfr": {"availability": {"target": 0.99}},
        "cost": {"intent": {"priority": "optimize-tco"}},
        "operating_model": {"amortization_months": 24}
    }

    # Phase 3.1: Filter by constraints
    selected_ids, rejected_constraints, honored_rules = _filter_by_supports_constraints(patterns, spec)
    assert "multi-rule-pattern" in honored_rules
    assert len(honored_rules["multi-rule-pattern"]["constraints"]) == 1
    assert len(honored_rules["multi-rule-pattern"]["nfr"]) == 0

    # Phase 3.2: Filter by NFR
    selected_ids, rejected_nfr, honored_rules = _filter_by_supports_nfr(
        selected_ids, patterns, spec, honored_rules
    )
    assert "multi-rule-pattern" in honored_rules
    assert len(honored_rules["multi-rule-pattern"]["constraints"]) == 1
    assert len(honored_rules["multi-rule-pattern"]["nfr"]) == 1

    # Phase 3.3: Conflict resolution
    selected_ids, rejected_conflicts, match_scores = _resolve_conflicts_with_match_scoring(
        selected_ids, patterns, spec
    )
    assert "multi-rule-pattern" in selected_ids
    # honored_rules should still be intact (not modified by Phase 3.3)
    assert "multi-rule-pattern" in honored_rules
    assert len(honored_rules["multi-rule-pattern"]["constraints"]) == 1
    assert len(honored_rules["multi-rule-pattern"]["nfr"]) == 1

    print("✅ test_honored_rules_persists_through_phases passed")


if __name__ == "__main__":
    # Run all tests
    test_selected_patterns_sorted_by_match_score()
    test_selected_patterns_minimal_fields()
    test_rejected_patterns_sorted_by_partial_match()
    test_honored_rules_format()
    test_honored_rules_accuracy()
    test_cli_outputs_compiled_spec_content()
    test_cli_files_at_end_with_utc()
    test_verbose_comprehensive_info()
    test_verbose_cost_logging_always()
    test_match_score_calculation_edge_cases()
    test_partial_match_score_edge_cases()
    test_honored_rules_persists_through_phases()

    print("\n" + "=" * 60)
    print("✅ All 12 tests for Proposals 1-4 passed!")
    print("=" * 60)
