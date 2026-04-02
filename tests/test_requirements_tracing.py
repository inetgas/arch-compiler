#!/usr/bin/env python3
"""
Unit tests for requirements tracing helpers.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from archcompiler import _build_requirements_to_patterns_index, _format_pattern_list


def test_build_index_simple():
    """Test building inverse index with simple rules."""
    honored_rules = {
        "pattern-a": {
            "constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws"},
                {"path": "/constraints/language", "op": "in", "value": ["python"]}
            ],
            "nfr": [
                {"path": "/nfr/availability/target", "op": "<=", "value": 0.999}
            ]
        },
        "pattern-b": {
            "constraints": [
                {"path": "/constraints/cloud", "op": "==", "value": "aws"}
            ],
            "nfr": []
        }
    }

    match_scores = {"pattern-a": 10.0, "pattern-b": 5.0}

    index = _build_requirements_to_patterns_index(honored_rules, match_scores)

    # Check paths exist
    assert "/constraints/cloud" in index
    assert "/constraints/language" in index
    assert "/nfr/availability/target" in index

    # Check sorted by match_score (pattern-a has higher score)
    assert index["/constraints/cloud"] == ["pattern-a", "pattern-b"]
    assert index["/constraints/language"] == ["pattern-a"]
    assert index["/nfr/availability/target"] == ["pattern-a"]

    print("✅ test_build_index_simple passed")


def test_build_index_empty():
    """Test building index with no rules."""
    honored_rules = {}
    match_scores = {}

    index = _build_requirements_to_patterns_index(honored_rules, match_scores)

    assert index == {}
    print("✅ test_build_index_empty passed")


def test_format_pattern_list_short():
    """Test formatting when <= 3 patterns."""
    assert _format_pattern_list([]) == ""
    assert _format_pattern_list(["p1"]) == "p1"
    assert _format_pattern_list(["p1", "p2"]) == "p1, p2"
    assert _format_pattern_list(["p1", "p2", "p3"]) == "p1, p2, p3"
    print("✅ test_format_pattern_list_short passed")


def test_format_pattern_list_long():
    """Test formatting when > 3 patterns."""
    result = _format_pattern_list(["p1", "p2", "p3", "p4"])
    assert result == "p1, p2, p3, ... (1 more)"

    result = _format_pattern_list(["p1", "p2", "p3", "p4", "p5", "p6"])
    assert result == "p1, p2, p3, ... (3 more)"
    print("✅ test_format_pattern_list_long passed")


def test_metadata_comments_free_tier():
    """Test metadata-based comments for free tier patterns."""
    from archcompiler import _build_metadata_comments_index

    selected_pattern_ids = ["pattern-a", "pattern-b", "pattern-c"]
    patterns = {
        "pattern-a": {
            "cost": {"freeTierEligible": True}
        },
        "pattern-b": {
            "cost": {"freeTierEligible": False}
        },
        "pattern-c": {
            "cost": {"freeTierEligible": True}
        }
    }
    match_scores = {"pattern-a": 10.0, "pattern-b": 5.0, "pattern-c": 8.0}
    spec = {
        "cost": {
            "preferences": {
                "prefer_free_tier_if_possible": True
            }
        }
    }

    index = _build_metadata_comments_index(selected_pattern_ids, patterns, match_scores, spec)

    # Check path exists
    assert "/cost/preferences/prefer_free_tier_if_possible" in index

    # Check only free tier patterns included, sorted by match_score
    assert index["/cost/preferences/prefer_free_tier_if_possible"] == ["pattern-a", "pattern-c"]

    print("✅ test_metadata_comments_free_tier passed")


def test_metadata_comments_free_tier_false():
    """Test no comment when prefer_free_tier_if_possible is false."""
    from archcompiler import _build_metadata_comments_index

    selected_pattern_ids = ["pattern-a"]
    patterns = {
        "pattern-a": {
            "cost": {"freeTierEligible": True}
        }
    }
    match_scores = {"pattern-a": 10.0}
    spec = {
        "cost": {
            "preferences": {
                "prefer_free_tier_if_possible": False
            }
        }
    }

    index = _build_metadata_comments_index(selected_pattern_ids, patterns, match_scores, spec)

    # Check NO comment when prefer_free_tier_if_possible is false
    assert "/cost/preferences/prefer_free_tier_if_possible" not in index

    print("✅ test_metadata_comments_free_tier_false passed")


if __name__ == "__main__":
    test_build_index_simple()
    test_build_index_empty()
    test_format_pattern_list_short()
    test_format_pattern_list_long()
    test_metadata_comments_free_tier()
    test_metadata_comments_free_tier_false()
    print("\n✅ All tests passed!")
