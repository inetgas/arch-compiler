#!/usr/bin/env python3
"""Unit tests for Phase 4: Cost feasibility check."""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from archcompiler import _check_cost_feasibility, _calculate_ops_team_cost


def test_no_warnings_under_budget():
    """No warnings when costs under ceilings."""
    patterns = {
        "pattern-a": {"cost": {"estimatedMonthlyRangeUsd": {"min": 100, "max": 200}, "adoptionCost": 1000, "licenseCost": 0}}
    }
    spec = {
        "cost": {
            "intent": {"priority": "optimize-tco"},
            "ceilings": {
                "monthly_operational_usd": 1000,
                "one_time_setup_usd": 5000
            }
        },
        "operating_model": {"ops_team_size": 0, "amortization_months": 24}
    }
    ops_team_cost = 0

    warnings, _ = _check_cost_feasibility(["pattern-a"], patterns, spec, ops_team_cost, {})

    assert len(warnings) == 0
    print("✅ test_no_warnings_under_budget passed")


def test_warning_opex_exceeds_ceiling_minimize_opex():
    """Warning when total opex exceeds ceiling (minimize-opex intent)."""
    patterns = {
        "expensive": {"cost": {"estimatedMonthlyRangeUsd": {"min": 1000, "max": 2000}}}
    }
    spec = {
        "cost": {
            "intent": {"priority": "minimize-opex"},
            "ceilings": {
                "monthly_operational_usd": 500
            }
        },
        "operating_model": {"ops_team_size": 0}
    }
    ops_team_cost = 0

    warnings, _ = _check_cost_feasibility(["expensive"], patterns, spec, ops_team_cost, {})

    assert len(warnings) == 1
    assert warnings[0]["code"] == "cost_opex_exceeds_ceiling"
    assert warnings[0]["severity"] == "high"
    assert warnings[0]["details"]["intent"] == "minimize-opex"
    assert "suggestions" in warnings[0]
    print("✅ test_warning_opex_exceeds_ceiling_minimize_opex passed")


def test_warning_capex_exceeds_ceiling_minimize_capex():
    """Warning when capex exceeds ceiling (minimize-capex intent)."""
    patterns = {
        "expensive": {"cost": {"adoptionCost": 10000, "licenseCost": 2000, "estimatedMonthlyRangeUsd": {"min": 100, "max": 200}}}
    }
    spec = {
        "cost": {
            "intent": {"priority": "minimize-capex"},
            "ceilings": {
                "one_time_setup_usd": 5000
            }
        },
        "operating_model": {"ops_team_size": 0}
    }
    ops_team_cost = 0

    warnings, _ = _check_cost_feasibility(["expensive"], patterns, spec, ops_team_cost, {})

    assert len(warnings) == 1
    assert warnings[0]["code"] == "cost_capex_exceeds_ceiling"
    assert warnings[0]["severity"] == "high"
    assert warnings[0]["details"]["intent"] == "minimize-capex"
    print("✅ test_warning_capex_exceeds_ceiling_minimize_capex passed")


def test_warning_tco_exceeds_ceiling_optimize_tco():
    """Warning when TCO exceeds combined ceiling (optimize-tco intent)."""
    patterns = {
        "pattern-a": {"cost": {"adoptionCost": 2000, "licenseCost": 0, "estimatedMonthlyRangeUsd": {"min": 200, "max": 300}}}
    }
    spec = {
        "cost": {
            "intent": {"priority": "optimize-tco"},
            "ceilings": {
                "monthly_operational_usd": 100,  # 100 * 24 = 2400
                "one_time_setup_usd": 1000
            }
        },
        "operating_model": {"ops_team_size": 0, "amortization_months": 24}
    }
    ops_team_cost = 0

    # TCO = 2000 + (200 * 24) = 2000 + 4800 = 6800
    # Ceiling TCO = 1000 + (100 * 24) = 1000 + 2400 = 3400
    # Overage = 6800 - 3400 = 3400

    warnings, _ = _check_cost_feasibility(["pattern-a"], patterns, spec, ops_team_cost, {})

    assert len(warnings) == 1
    assert warnings[0]["code"] == "cost_tco_exceeds_ceiling"
    assert warnings[0]["severity"] == "high"
    assert warnings[0]["details"]["intent"] == "optimize-tco"
    assert warnings[0]["details"]["tco"] == 6800
    assert warnings[0]["details"]["ceiling_tco"] == 3400
    print("✅ test_warning_tco_exceeds_ceiling_optimize_tco passed")


def test_ops_team_cost_calculation():
    """Ops team cost calculated correctly with new parameters."""
    operating_model = {
        "ops_team_size": 2,
        "single_resource_monthly_ops_usd": 12000,
        "on_call": False,
        "deploy_freq": "weekly"
    }

    cost = _calculate_ops_team_cost(operating_model)

    # Base: 2 × 12000 = 24000
    # On-call: 1.0 (no on-call)
    # Deploy: 0.8 (weekly)
    # Total: 24000 × 1.0 × 0.8 = 19200
    assert cost == 19200.0
    print("✅ test_ops_team_cost_calculation passed")


if __name__ == "__main__":
    test_no_warnings_under_budget()
    test_warning_opex_exceeds_ceiling_minimize_opex()
    test_warning_capex_exceeds_ceiling_minimize_capex()
    test_warning_tco_exceeds_ceiling_optimize_tco()
    test_ops_team_cost_calculation()
    print("\n✅ All Phase 4 tests passed!")
