#!/usr/bin/env python3
"""Unit tests for Phase 3.3: Conflict resolution with cost tie-breaking."""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _resolve_conflicts_with_match_scoring


def test_no_conflicts_all_selected():
    """Patterns without conflicts are all selected."""
    patterns = {
        "pattern-a": {"conflicts": {}},
        "pattern-b": {"conflicts": {}},
        "pattern-c": {"conflicts": {}}
    }
    spec = {}

    selected, rejected, _ = _resolve_conflicts_with_match_scoring(
        ["pattern-a", "pattern-b", "pattern-c"], patterns, spec
    )

    assert len(selected) == 3
    assert len(rejected) == 0
    print("✅ test_no_conflicts_all_selected passed")


def test_conflict_higher_score_wins():
    """Pattern with higher match score wins conflict."""
    patterns = {
        "cache-aside": {
            "conflicts": {"incompatibleWithDesignPatterns": ["cache-aside--redis"]},
            "supports_constraints": [
                {"path": "/constraints/features/caching", "op": "==", "value": True, "reason": "..."}
            ],
            "cost": {"estimatedMonthlyRangeUsd": {"min": 10, "max": 50}}
        },
        "cache-aside--redis": {
            "conflicts": {"incompatibleWithDesignPatterns": ["cache-aside"]},
            "supports_constraints": [
                {"path": "/constraints/features/caching", "op": "==", "value": True, "reason": "..."},
                {"path": "/constraints/saas-providers", "op": "contains-any", "value": ["redis-cloud"], "reason": "..."}
            ],
            "cost": {"estimatedMonthlyRangeUsd": {"min": 20, "max": 100}}
        }
    }
    spec = {
        "constraints": {
            "features": {"caching": True},
            "saas-providers": ["redis-cloud"]
        }
    }

    selected, rejected, _ = _resolve_conflicts_with_match_scoring(
        ["cache-aside", "cache-aside--redis"], patterns, spec
    )

    assert "cache-aside--redis" in selected
    assert "cache-aside" not in selected
    assert len(rejected) == 1
    assert rejected[0]["id"] == "cache-aside"
    assert rejected[0]["winner"] == "cache-aside--redis"
    # cache-aside: 1 match (caching), cache-aside--redis: 2 matches (caching + saas-providers)
    assert rejected[0]["loser_score"] == 1
    assert rejected[0]["winner_score"] == 2
    print("✅ test_conflict_higher_score_wins passed")


def test_conflict_tie_score_lower_cost_wins():
    """When match scores tied, lower-cost pattern wins (cost.intent tie-breaker)."""
    patterns = {
        "expensive": {
            "conflicts": {"incompatibleWithDesignPatterns": ["cheap"]},
            "supports_constraints": [
                {"path": "/constraints/platform", "op": "==", "value": "api", "reason": "..."}
            ],
            "cost": {
                "estimatedMonthlyRangeUsd": {"min": 100, "max": 200},
                "adoptionCost": 5000,
                "licenseCost": 0
            }
        },
        "cheap": {
            "conflicts": {"incompatibleWithDesignPatterns": ["expensive"]},
            "supports_constraints": [
                {"path": "/constraints/platform", "op": "==", "value": "api", "reason": "..."}
            ],
            "cost": {
                "estimatedMonthlyRangeUsd": {"min": 10, "max": 50},
                "adoptionCost": 1000,
                "licenseCost": 0
            }
        }
    }
    spec = {
        "constraints": {"platform": "api"},
        "cost": {"intent": {"priority": "minimize-opex"}},
        "operating_model": {"amortization_months": 24}
    }

    selected, rejected, _ = _resolve_conflicts_with_match_scoring(
        ["expensive", "cheap"], patterns, spec
    )

    assert "cheap" in selected
    assert "expensive" not in selected
    assert len(rejected) == 1
    assert rejected[0]["id"] == "expensive"
    assert rejected[0]["winner"] == "cheap"
    # Both have score 1 (platform match), but cheap has lower opex (10 vs 100)
    assert rejected[0]["winner_score"] == rejected[0]["loser_score"]  # Tied score
    assert rejected[0]["winner_cost"] < rejected[0]["loser_cost"]  # Lower cost wins
    assert rejected[0]["cost_intent"] == "minimize-opex"
    print("✅ test_conflict_tie_score_lower_cost_wins passed")


def test_hub_pattern_both_specific_variants_selected():
    """
    Regression: two specific variants that don't conflict with each other should
    both be selected even when they share a common hub (generic fallback) in the
    conflict graph.

    Before the greedy-MIS fix the BFS grouped generic+supabase+render into one
    conflict component and selected only ONE winner, discarding the other two.
    """
    patterns = {
        "cost-free-saas-tier": {
            "conflicts": {
                "incompatibleWithDesignPatterns": [
                    "cost-free-saas-tier--supabase",
                    "cost-free-saas-tier--render",
                ]
            },
            "supports_constraints": [],
            "cost": {"estimatedMonthlyRangeUsd": {"min": 0, "max": 50}}
        },
        "cost-free-saas-tier--supabase": {
            "conflicts": {
                "incompatibleWithDesignPatterns": ["cost-free-saas-tier"]
            },
            "supports_constraints": [
                {
                    "path": "/constraints/saas-providers",
                    "op": "contains-any",
                    "value": ["supabase"],
                    "reason": "Requires supabase in saas-providers"
                }
            ],
            "cost": {"estimatedMonthlyRangeUsd": {"min": 0, "max": 0}}
        },
        "cost-free-saas-tier--render": {
            "conflicts": {
                "incompatibleWithDesignPatterns": ["cost-free-saas-tier"]
            },
            "supports_constraints": [
                {
                    "path": "/constraints/saas-providers",
                    "op": "contains-any",
                    "value": ["render"],
                    "reason": "Requires render in saas-providers"
                }
            ],
            "cost": {"estimatedMonthlyRangeUsd": {"min": 0, "max": 0}}
        }
    }
    spec = {
        "constraints": {
            "saas-providers": ["supabase", "render"]
        }
    }

    selected, rejected, _ = _resolve_conflicts_with_match_scoring(
        ["cost-free-saas-tier", "cost-free-saas-tier--supabase", "cost-free-saas-tier--render"],
        patterns, spec
    )

    assert "cost-free-saas-tier--supabase" in selected, "supabase variant must be selected"
    assert "cost-free-saas-tier--render" in selected, "render variant must be selected"
    assert "cost-free-saas-tier" not in selected, "generic must be excluded (lower score)"
    assert len(rejected) == 1
    assert rejected[0]["id"] == "cost-free-saas-tier"
    print("✅ test_hub_pattern_both_specific_variants_selected passed")


def test_pairwise_conflict_still_picks_one_winner():
    """
    Greedy MIS must NOT change normal pairwise-conflict behaviour:
    when A and B are mutually exclusive, only the higher-score one is selected.
    """
    patterns = {
        "arch-monolith": {
            "conflicts": {"incompatibleWithDesignPatterns": ["arch-microservices"]},
            "supports_constraints": [
                {"path": "/constraints/platform", "op": "==", "value": "api", "reason": "..."}
            ],
            "cost": {"estimatedMonthlyRangeUsd": {"min": 10, "max": 50}}
        },
        "arch-microservices": {
            "conflicts": {"incompatibleWithDesignPatterns": ["arch-monolith"]},
            "supports_constraints": [
                {"path": "/constraints/platform", "op": "==", "value": "api", "reason": "..."},
                {"path": "/constraints/features/multi_tenancy", "op": "==", "value": True, "reason": "..."}
            ],
            "cost": {"estimatedMonthlyRangeUsd": {"min": 100, "max": 500}}
        }
    }
    spec = {
        "constraints": {
            "platform": "api",
            "features": {"multi_tenancy": True}
        }
    }

    selected, rejected, _ = _resolve_conflicts_with_match_scoring(
        ["arch-monolith", "arch-microservices"], patterns, spec
    )

    assert "arch-microservices" in selected
    assert "arch-monolith" not in selected
    assert len(selected) == 1
    assert len(rejected) == 1
    print("✅ test_pairwise_conflict_still_picks_one_winner passed")


if __name__ == "__main__":
    test_no_conflicts_all_selected()
    test_conflict_higher_score_wins()
    test_conflict_tie_score_lower_cost_wins()
    test_hub_pattern_both_specific_variants_selected()
    test_pairwise_conflict_still_picks_one_winner()
    print("\n✅ All Phase 3.3 tests passed!")
